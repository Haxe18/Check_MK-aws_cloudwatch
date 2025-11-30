#!/usr/bin/env python3
"""Checkmk check plugin for AWS S3 CloudWatch metrics.

This module provides the check plugin for S3 bucket metrics
with configurable thresholds for Bucket Size and Object Count.
"""

from typing import Any

from .aws_cloudwatch_helpers import (
    SERVICE_S3,
    CheckConfig,
    LevelsType,
    MetricSpec,
    RenderType,
    create_cloudwatch_check,
)

# S3-specific metric specifications
S3_METRIC_SPECS = [
    # Bucket Size
    MetricSpec(
        metric_key="BucketSizeBytes_Average",
        label="Bucket Size",
        metric_name="bucket_size",
        param_key="bucket_size_levels",
        render_type=RenderType.BYTES,
        levels_type=LevelsType.UPPER,
    ),
    # Object Count
    MetricSpec(
        metric_key="NumberOfObjects_Average",
        label="Objects",
        metric_name="object_count",
        param_key="object_count_levels",
        render_type=RenderType.COUNT,
        levels_type=LevelsType.UPPER,
    ),
]


def _s3_ttl_details(
    metrics_found: dict[str, dict[str, Any]],
    params: dict[str, Any],
    metric_prefix: str,
    item: str,
    section: dict[str, Any],
) -> str:
    """Return details text about AWS-driven daily S3 metric cadence."""
    _ = (metrics_found, params, metric_prefix, item)
    api_config = section.get("CloudWatchAPIConfig", {})
    overrides = (
        api_config.get("service_metrics_ttl_overrides", {})
        if isinstance(api_config, dict)
        else {}
    )
    s3_ttl = overrides.get("s3", 24 * 3600) if isinstance(overrides, dict) else 24 * 3600
    ttl_hours = max(1, int(s3_ttl) // 3600)
    return (
        f"S3 metrics are published daily by AWS; TTL is set to {ttl_hours}h accordingly "
        "(also reducing unnecessary API calls)."
    )


# Create the check plugin using the factory
check_plugin_aws_cloudwatch_s3 = create_cloudwatch_check(
    CheckConfig(
        service_key=SERVICE_S3,
        service_name="S3",
        resource_type="bucket",
        metric_prefix="s3",
        metric_specs=S3_METRIC_SPECS,
        details_hook=_s3_ttl_details,
    )
)
