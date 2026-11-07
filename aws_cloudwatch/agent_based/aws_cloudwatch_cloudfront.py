#!/usr/bin/env python3
"""Checkmk check plugin for AWS CloudFront CloudWatch metrics.

This module provides the check plugin for CloudFront distribution metrics
with configurable thresholds for Error Rates and Requests.
"""

from typing import Any

from cmk.agent_based.v2 import Result, State

from .aws_cloudwatch_helpers import (
    SERVICE_CLOUDFRONT,
    SERVICE_CLOUDFRONT_FUNCTIONS,
    CheckConfig,
    InfoMetricSpec,
    LevelsType,
    MetricSpec,
    RenderType,
    create_cloudwatch_check,
)

# CloudFront-specific metric specifications
CLOUDFRONT_METRIC_SPECS = [
    # Error Rates
    MetricSpec(
        metric_key="TotalErrorRate_Average",
        label="Total Error Rate",
        metric_name="total_error_rate",
        param_key="total_error_rate_levels",
        render_type=RenderType.PERCENT,
        levels_type=LevelsType.UPPER,
    ),
    MetricSpec(
        metric_key="4xxErrorRate_Average",
        label="4xx Error Rate",
        metric_name="4xx_error_rate",
        param_key="error_4xx_rate_levels",
        render_type=RenderType.PERCENT,
        levels_type=LevelsType.UPPER,
    ),
    MetricSpec(
        metric_key="5xxErrorRate_Average",
        label="5xx Error Rate",
        metric_name="5xx_error_rate",
        param_key="error_5xx_rate_levels",
        render_type=RenderType.PERCENT,
        levels_type=LevelsType.UPPER,
    ),
    # Cache Hit Rate (lower is bad)
    MetricSpec(
        metric_key="CacheHitRate_Average",
        label="Cache Hit Rate",
        metric_name="cache_hit_rate",
        param_key="cache_hit_rate_levels",
        render_type=RenderType.PERCENT,
        levels_type=LevelsType.LOWER,
    ),
    # Origin Latency (stored in seconds, displayed as ms)
    MetricSpec(
        metric_key="OriginLatency_Average",
        label="Origin Latency",
        metric_name="origin_latency",
        param_key="origin_latency_levels",
        render_type=RenderType.MILLISECONDS,
        levels_type=LevelsType.UPPER,
    ),
    MetricSpec(
        metric_key="BytesDownloaded_Sum",
        label="Downloaded",
        metric_name="bytes_downloaded",
        param_key="bytes_downloaded_levels",
        render_type=RenderType.BYTES,
        levels_type=LevelsType.UPPER,
    ),
    MetricSpec(
        metric_key="BytesUploaded_Sum",
        label="Uploaded",
        metric_name="bytes_uploaded",
        param_key="bytes_uploaded_levels",
        render_type=RenderType.BYTES,
        levels_type=LevelsType.UPPER,
    ),
]

# Informational metrics
CLOUDFRONT_INFO_METRICS = [
    InfoMetricSpec(
        metric_key="Requests_Sum",
        label="Requests",
        metric_name="requests",
        render_type=RenderType.COUNT,
    ),
]


def _metadata_fetch_enabled(section: dict[str, Any]) -> bool:
    """Whether the agent fetched CloudFront metadata (ListDistributions).

    Older agents did not report the option and always fetched; treat a
    missing value as enabled.
    """
    api_config = section.get("CloudWatchAPIConfig", {})
    if not isinstance(api_config, dict):
        return True
    options = api_config.get("section_options", {})
    if not isinstance(options, dict):
        return True
    cloudfront_options = options.get("cloudfront", {})
    if not isinstance(cloudfront_options, dict):
        return True
    return bool(cloudfront_options.get("fetch_metadata", True))


def _cloudfront_pre_hook(
    _metrics_found: dict[str, dict[str, Any]],
    params: dict[str, Any],
    _metric_prefix: str,
    item: str,
    section: dict[str, Any],
) -> Any:
    """Prepend CloudFront description and/or URL before metric output."""
    show_desc = params.get("show_description", False)
    show_url = params.get("show_url", False)
    if not show_desc and not show_url:
        return

    if not _metadata_fetch_enabled(section):
        yield Result(
            state=State.OK,
            notice=(
                "Description/URL not available: enable 'CloudFront: Fetch description "
                "and URL' in the special agent rule (needs cloudfront:ListDistributions)"
            ),
        )
        return

    parts = item.split(" ", 1)
    if len(parts) != 2:
        return
    region, resource_id = parts[0], parts[1]

    metadata_section = section.get("CloudWatchResourceMetadata", {})
    service_key = f"{region}:cloudfront"
    metadata = metadata_section.get(service_key, {}).get(resource_id, {})

    comment = metadata.get("comment", "") if show_desc else ""
    url = ""
    if show_url:
        aliases = metadata.get("aliases", [])
        url = aliases[0] if aliases else metadata.get("domain_name", "")
        if url and not url.startswith("http"):
            url = f"https://{url}"

    if comment and url:
        summary = f"{comment}: {url}"
    elif url:
        summary = f"URL: {url}"
    elif comment:
        summary = f"({comment})"
    else:
        return

    yield Result(state=State.OK, summary=summary)


# Create the check plugin using the factory
# CloudFront uses exclude filter to skip CloudFront Functions
check_plugin_aws_cloudwatch_cloudfront = create_cloudwatch_check(
    CheckConfig(
        service_key=SERVICE_CLOUDFRONT,
        service_name="CloudFront",
        resource_type="distribution",
        metric_prefix="cloudfront",
        metric_specs=CLOUDFRONT_METRIC_SPECS,
        info_metrics=CLOUDFRONT_INFO_METRICS,
        exclude_filter=SERVICE_CLOUDFRONT_FUNCTIONS,
        pre_check_hook=_cloudfront_pre_hook,
    )
)
