#!/usr/bin/env python3
"""Checkmk check plugin for AWS Application Load Balancer (ALB) CloudWatch metrics.

This module provides the check plugin for ALB metrics
with configurable thresholds for Response Time, Healthy Targets, and Error Rates.
"""

from typing import Any

from cmk.agent_based.v2 import CheckResult

from .aws_cloudwatch_helpers import (
    SERVICE_ALB,
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

# ALB-specific error codes for shared helper
ALB_ERROR_CODES = [
    ("HTTPCode_ELB_4XX_Count", "ALB 4XX"),
    ("HTTPCode_ELB_5XX_Count", "ALB 5XX"),
    ("HTTPCode_Target_4XX_Count", "Target 4XX"),
    ("HTTPCode_Target_5XX_Count", "Target 5XX"),
]

# ALB-specific metric specifications
ALB_METRIC_SPECS = [
    # Response Time (stored in seconds, displayed as ms)
    MetricSpec(
        metric_key="TargetResponseTime_Average",
        label="Response Time",
        metric_name="response_time",
        param_key="response_time_levels",
        render_type=RenderType.MILLISECONDS,
        levels_type=LevelsType.UPPER,
        value_transform=lambda v: v * 1000,  # CloudWatch seconds -> ms for thresholds
    ),
    # Active Connections
    MetricSpec(
        metric_key="ActiveConnectionCount_Sum",
        label="Active Connections",
        metric_name="active_connections",
        param_key="active_connections_levels",
        render_type=RenderType.INTEGER,
        levels_type=LevelsType.UPPER,
    ),
]

# Informational metrics
ALB_INFO_METRICS = [
    InfoMetricSpec(
        metric_key="RequestCount_Sum",
        label="Requests",
        metric_name="request_count",
        render_type=RenderType.INTEGER,
    ),
    # Shown in the service details only
    InfoMetricSpec(
        metric_key="NewConnectionCount_Sum",
        label="New Connections",
        metric_name="new_connections",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="RejectedConnectionCount_Sum",
        label="Rejected Connections",
        metric_name="rejected_connections",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="ProcessedBytes_Sum",
        label="Processed Bytes",
        metric_name="processed_bytes",
        render_type=RenderType.BYTES,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="ClientTLSNegotiationErrorCount_Sum",
        label="Client TLS Errors",
        metric_name="client_tls_errors",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="TargetTLSNegotiationErrorCount_Sum",
        label="Target TLS Errors",
        metric_name="target_tls_errors",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="TargetConnectionErrorCount_Sum",
        label="Target Connection Errors",
        metric_name="target_connection_errors",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="HTTPCode_ELB_3XX_Count_Sum",
        label="ALB 3XX",
        metric_name="httpcode_elb_3xx_count",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="HTTPCode_ELB_500_Count_Sum",
        label="ALB 500",
        metric_name="httpcode_elb_500_count",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="HTTPCode_ELB_502_Count_Sum",
        label="ALB 502",
        metric_name="httpcode_elb_502_count",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="HTTPCode_ELB_503_Count_Sum",
        label="ALB 503",
        metric_name="httpcode_elb_503_count",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="HTTPCode_ELB_504_Count_Sum",
        label="ALB 504",
        metric_name="httpcode_elb_504_count",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
]


def _check_alb_special(
    metrics_found: dict[str, dict[str, Any]],
    params: dict[str, Any],
    metric_prefix: str,
    **_kwargs: Any,
) -> CheckResult:
    """Check ALB-specific metrics using shared helpers."""
    # Healthy/Unhealthy targets
    yield from check_healthy_unhealthy_targets(metrics_found, params, metric_prefix)

    # HTTP error codes
    yield from check_http_error_codes(metrics_found, ALB_ERROR_CODES, metric_prefix)

    # Process successful target codes (informational, metrics only)
    yield from emit_sum_metrics(
        metrics_found,
        ["HTTPCode_Target_2XX_Count", "HTTPCode_Target_3XX_Count"],
        metric_prefix,
    )


# Create the check plugin using the factory
check_plugin_aws_cloudwatch_alb = create_cloudwatch_check(
    CheckConfig(
        service_key=SERVICE_ALB,
        service_name="ALB",
        resource_type="load balancer",
        metric_prefix="alb",
        metric_specs=ALB_METRIC_SPECS,
        info_metrics=ALB_INFO_METRICS,
        post_check_hook=_check_alb_special,
    )
)
