#!/usr/bin/env python3
"""Checkmk check plugin for AWS ELB Classic CloudWatch metrics.

This module provides the check plugin for Classic Elastic Load Balancer metrics
with configurable thresholds for Latency, Healthy Hosts, and Error Rates.
"""

from typing import Any

from cmk.agent_based.v2 import CheckResult

from .aws_cloudwatch_helpers import (
    SERVICE_ELB,
    SERVICE_ELB_V2,
    CheckConfig,
    InfoMetricSpec,
    LevelsType,
    MetricSpec,
    RenderType,
    check_healthy_unhealthy_targets,
    check_http_error_codes,
    create_cloudwatch_check,
    emit_sum_metrics,
)

# ELB Classic error codes for shared helper
ELB_ERROR_CODES = [
    ("HTTPCode_ELB_4XX", "ELB 4XX"),
    ("HTTPCode_ELB_5XX", "ELB 5XX"),
    ("HTTPCode_Backend_4XX", "Backend 4XX"),
    ("HTTPCode_Backend_5XX", "Backend 5XX"),
]

# ELB-specific metric specifications
ELB_METRIC_SPECS = [
    # Latency (stored in seconds, displayed as ms)
    MetricSpec(
        metric_key="Latency_Average",
        label="Latency",
        metric_name="latency",
        param_key="latency_levels",
        render_type=RenderType.MILLISECONDS,
        levels_type=LevelsType.UPPER,
        value_transform=lambda v: v * 1000,  # CloudWatch seconds -> ms for thresholds
    ),
]

# Informational metrics
ELB_INFO_METRICS = [
    InfoMetricSpec(
        metric_key="RequestCount_Sum",
        label="Requests",
        metric_name="request_count",
        render_type=RenderType.INTEGER,
    ),
    # Shown in the service details only
    InfoMetricSpec(
        metric_key="SpilloverCount_Sum",
        label="Spillover",
        metric_name="spillover_count",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="SurgeQueueLength_Maximum",
        label="Surge Queue Length",
        metric_name="surge_queue_length",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
]


def _check_elb_special(
    metrics_found: dict[str, dict[str, Any]],
    params: dict[str, Any],
    metric_prefix: str,
    **_kwargs: Any,
) -> CheckResult:
    """Check ELB-specific metrics using shared helpers."""
    # Healthy/Unhealthy hosts (ELB Classic uses "Hosts" label)
    yield from check_healthy_unhealthy_targets(
        metrics_found,
        params,
        metric_prefix,
        levels_param="unhealthy_hosts_levels",
        label_type="Hosts",
    )

    # HTTP error codes
    yield from check_http_error_codes(metrics_found, ELB_ERROR_CODES, metric_prefix)

    # Process successful backend codes (informational, metrics only)
    yield from emit_sum_metrics(
        metrics_found,
        ["HTTPCode_Backend_2XX", "HTTPCode_Backend_3XX"],
        metric_prefix,
    )


# Create the check plugin using the factory
# ELB Classic uses exclude filter to skip ELB v2
check_plugin_aws_cloudwatch_elb = create_cloudwatch_check(
    CheckConfig(
        service_key=SERVICE_ELB,
        service_name="ELB",
        resource_type="load balancer",
        metric_prefix="elb",
        metric_specs=ELB_METRIC_SPECS,
        info_metrics=ELB_INFO_METRICS,
        exclude_filter=SERVICE_ELB_V2,
        post_check_hook=_check_elb_special,
    )
)
