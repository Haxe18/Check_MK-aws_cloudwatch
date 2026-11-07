#!/usr/bin/env python3
"""Checkmk check plugin for AWS EC2 CloudWatch metrics.

This module provides the check plugin for EC2 instance metrics
with configurable thresholds for CPU, Network, Disk, and Status Checks.
"""

from typing import Any

from cmk.agent_based.v2 import CheckResult, Metric, Result, State

from .aws_cloudwatch_helpers import (
    SERVICE_EC2,
    CheckConfig,
    InfoMetricSpec,
    LevelsType,
    MetricSpec,
    RenderType,
    create_cloudwatch_check,
)

# EC2-specific metric specifications
EC2_METRIC_SPECS = [
    # CPU Utilization
    MetricSpec(
        metric_key="CPUUtilization_Average",
        label="CPU Utilization",
        metric_name="cpu_utilization",
        param_key="cpu_levels",
        render_type=RenderType.PERCENT,
        levels_type=LevelsType.UPPER,
    ),
    # Network metrics
    MetricSpec(
        metric_key="NetworkIn_Sum",
        label="Network In",
        metric_name="network_in",
        param_key="network_in_levels",
        render_type=RenderType.BYTES,
        levels_type=LevelsType.UPPER,
    ),
    MetricSpec(
        metric_key="NetworkOut_Sum",
        label="Network Out",
        metric_name="network_out",
        param_key="network_out_levels",
        render_type=RenderType.BYTES,
        levels_type=LevelsType.UPPER,
    ),
    # Disk operations
    MetricSpec(
        metric_key="DiskReadOps_Sum",
        label="Disk Read Ops",
        metric_name="disk_read_ops",
        param_key="disk_read_ops_levels",
        render_type=RenderType.INTEGER,
        levels_type=LevelsType.UPPER,
    ),
    MetricSpec(
        metric_key="DiskWriteOps_Sum",
        label="Disk Write Ops",
        metric_name="disk_write_ops",
        param_key="disk_write_ops_levels",
        render_type=RenderType.INTEGER,
        levels_type=LevelsType.UPPER,
    ),
    # CPU Credit Balance (lower is bad for burstable instances)
    MetricSpec(
        metric_key="CPUCreditBalance_Average",
        label="CPU Credit Balance",
        metric_name="cpu_credit_balance",
        param_key="cpu_credit_balance_levels",
        render_type=RenderType.FLOAT,
        levels_type=LevelsType.LOWER,
    ),
]

# Informational metrics (no threshold checking)
EC2_INFO_METRICS = [
    InfoMetricSpec(
        metric_key="DiskReadBytes_Sum",
        label="Disk Read",
        metric_name="disk_read_bytes",
        render_type=RenderType.BYTES,
    ),
    InfoMetricSpec(
        metric_key="DiskWriteBytes_Sum",
        label="Disk Write",
        metric_name="disk_write_bytes",
        render_type=RenderType.BYTES,
    ),
    # Shown in the service details only
    InfoMetricSpec(
        metric_key="CPUCreditUsage_Average",
        label="CPU Credit Usage",
        metric_name="cpu_credit_usage",
        render_type=RenderType.FLOAT,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="NetworkPacketsIn_Sum",
        label="Network Packets In",
        metric_name="network_packets_in",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="NetworkPacketsOut_Sum",
        label="Network Packets Out",
        metric_name="network_packets_out",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="EBSReadOps_Sum",
        label="EBS Read Ops",
        metric_name="ebs_read_ops",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="EBSWriteOps_Sum",
        label="EBS Write Ops",
        metric_name="ebs_write_ops",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="EBSReadBytes_Sum",
        label="EBS Read",
        metric_name="ebs_read_bytes",
        render_type=RenderType.BYTES,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="EBSWriteBytes_Sum",
        label="EBS Write",
        metric_name="ebs_write_bytes",
        render_type=RenderType.BYTES,
        details_only=True,
    ),
]


def _check_ec2_status(
    metrics_found: dict[str, dict[str, Any]],
    _params: dict[str, Any],
    metric_prefix: str,
    **_kwargs: Any,
) -> CheckResult:
    """Check EC2 status check metrics with special handling.

    Status checks have interdependent logic: if the combined check fails,
    we don't report individual failures redundantly.
    """
    status_check_failed = False

    # Combined status check (0 = passed, 1 = failed)
    if "StatusCheckFailed_Maximum" in metrics_found:
        metric = metrics_found["StatusCheckFailed_Maximum"]
        value = metric.get("value", 0)
        if value > 0:
            status_check_failed = True
            yield Result(state=State.CRIT, summary="Status Check Failed!")
        else:
            yield Result(state=State.OK, summary="Status Checks: OK")
        yield Metric(f"{metric_prefix}_status_check_failed", value)

    # Instance status check
    if "StatusCheckFailed_Instance_Maximum" in metrics_found:
        metric = metrics_found["StatusCheckFailed_Instance_Maximum"]
        value = metric.get("value", 0)
        if value > 0 and not status_check_failed:
            yield Result(state=State.CRIT, summary="Instance Status Check Failed!")
        yield Metric(f"{metric_prefix}_status_check_failed_instance", value)

    # System status check
    if "StatusCheckFailed_System_Maximum" in metrics_found:
        metric = metrics_found["StatusCheckFailed_System_Maximum"]
        value = metric.get("value", 0)
        if value > 0 and not status_check_failed:
            yield Result(state=State.CRIT, summary="System Status Check Failed!")
        yield Metric(f"{metric_prefix}_status_check_failed_system", value)


# Create the check plugin using the factory
check_plugin_aws_cloudwatch_ec2 = create_cloudwatch_check(
    CheckConfig(
        service_key=SERVICE_EC2,
        service_name="EC2",
        resource_type="instance",
        metric_prefix="ec2",
        metric_specs=EC2_METRIC_SPECS,
        info_metrics=EC2_INFO_METRICS,
        post_check_hook=_check_ec2_status,
    )
)
