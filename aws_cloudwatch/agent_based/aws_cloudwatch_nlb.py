#!/usr/bin/env python3
"""Checkmk check plugin for AWS Network Load Balancer (NLB) CloudWatch metrics.

This module provides the check plugin for NLB metrics
with configurable thresholds for Flows, Connections, and Processed Bytes.
"""

from typing import Any

from cmk.agent_based.v2 import CheckResult, Metric, Result, State

from .aws_cloudwatch_helpers import (
    SERVICE_NLB,
    CheckConfig,
    InfoMetricSpec,
    LevelsType,
    MetricSpec,
    RenderType,
    check_healthy_unhealthy_targets,
    create_cloudwatch_check,
)

# NLB-specific metric specifications
NLB_METRIC_SPECS = [
    # Active Flow Count
    MetricSpec(
        metric_key="ActiveFlowCount_Average",
        label="Active Flows",
        metric_name="active_flows",
        param_key="active_flows_levels",
        render_type=RenderType.INTEGER,
        levels_type=LevelsType.UPPER,
    ),
    # New Flow Count
    MetricSpec(
        metric_key="NewFlowCount_Sum",
        label="New Flows",
        metric_name="new_flows",
        param_key="new_flows_levels",
        render_type=RenderType.INTEGER,
        levels_type=LevelsType.UPPER,
    ),
    # Processed Bytes
    MetricSpec(
        metric_key="ProcessedBytes_Sum",
        label="Processed Bytes",
        metric_name="processed_bytes",
        param_key="processed_bytes_levels",
        render_type=RenderType.BYTES,
        levels_type=LevelsType.UPPER,
    ),
]

# Informational metrics, shown in the service details only
NLB_INFO_METRICS = [
    InfoMetricSpec(
        metric_key="ActiveFlowCount_TCP_Average",
        label="Active Flows TCP",
        metric_name="active_flows_tcp",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="ActiveFlowCount_UDP_Average",
        label="Active Flows UDP",
        metric_name="active_flows_udp",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="ActiveFlowCount_TLS_Average",
        label="Active Flows TLS",
        metric_name="active_flows_tls",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="NewFlowCount_TCP_Sum",
        label="New Flows TCP",
        metric_name="new_flows_tcp",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="NewFlowCount_UDP_Sum",
        label="New Flows UDP",
        metric_name="new_flows_udp",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="NewFlowCount_TLS_Sum",
        label="New Flows TLS",
        metric_name="new_flows_tls",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="ProcessedBytes_TCP_Sum",
        label="Processed Bytes TCP",
        metric_name="processed_bytes_tcp",
        render_type=RenderType.BYTES,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="ProcessedBytes_UDP_Sum",
        label="Processed Bytes UDP",
        metric_name="processed_bytes_udp",
        render_type=RenderType.BYTES,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="ProcessedBytes_TLS_Sum",
        label="Processed Bytes TLS",
        metric_name="processed_bytes_tls",
        render_type=RenderType.BYTES,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="ProcessedPackets_Sum",
        label="Processed Packets",
        metric_name="processed_packets",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="ConsumedLCUs_Average",
        label="Consumed LCUs",
        metric_name="consumed_lcus",
        render_type=RenderType.FLOAT,
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
]


def _check_nlb_special(
    metrics_found: dict[str, dict[str, Any]],
    params: dict[str, Any],
    metric_prefix: str,
    **_kwargs: Any,
) -> CheckResult:
    """Check NLB-specific metrics using shared helpers."""
    # Healthy/Unhealthy targets
    yield from check_healthy_unhealthy_targets(metrics_found, params, metric_prefix)

    # TCP Reset counts with custom state logic
    for code, label in [
        ("TCP_Client_Reset_Count", "Client Resets"),
        ("TCP_Target_Reset_Count", "Target Resets"),
        ("TCP_ELB_Reset_Count", "NLB Resets"),
    ]:
        key = f"{code}_Sum"
        if key in metrics_found:
            metric = metrics_found[key]
            value = metric.get("value", 0)
            state = State.WARN if value > 100 else State.OK
            yield Result(state=state, summary=f"{label}: {value:.0f}")
            yield Metric(f"{metric_prefix}_{code.lower()}", value)


# Create the check plugin using the factory
check_plugin_aws_cloudwatch_nlb = create_cloudwatch_check(
    CheckConfig(
        service_key=SERVICE_NLB,
        service_name="NLB",
        resource_type="load balancer",
        metric_prefix="nlb",
        metric_specs=NLB_METRIC_SPECS,
        info_metrics=NLB_INFO_METRICS,
        post_check_hook=_check_nlb_special,
    )
)
