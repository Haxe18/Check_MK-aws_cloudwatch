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
        post_check_hook=_check_nlb_special,
    )
)
