#!/usr/bin/env python3
"""Checkmk check plugin for AWS EBS CloudWatch metrics.

This module provides the check plugin for EBS volume metrics
with configurable thresholds for IOPS, Throughput, Queue Length, and Burst Balance.
"""

from typing import Any

from cmk.agent_based.v2 import CheckResult, Metric, Result, State

from .aws_cloudwatch_helpers import (
    SERVICE_EBS,
    CheckConfig,
    InfoMetricSpec,
    LevelsType,
    MetricSpec,
    RenderType,
    create_cloudwatch_check,
)

# EBS-specific metric specifications
EBS_METRIC_SPECS = [
    # IOPS
    MetricSpec(
        metric_key="VolumeReadOps_Sum",
        label="Read Ops",
        metric_name="read_ops",
        param_key="read_ops_levels",
        render_type=RenderType.INTEGER,
        levels_type=LevelsType.UPPER,
    ),
    MetricSpec(
        metric_key="VolumeWriteOps_Sum",
        label="Write Ops",
        metric_name="write_ops",
        param_key="write_ops_levels",
        render_type=RenderType.INTEGER,
        levels_type=LevelsType.UPPER,
    ),
    # Throughput
    MetricSpec(
        metric_key="VolumeReadBytes_Sum",
        label="Read Throughput",
        metric_name="read_bytes",
        param_key="read_throughput_levels",
        render_type=RenderType.BYTES,
        levels_type=LevelsType.UPPER,
    ),
    MetricSpec(
        metric_key="VolumeWriteBytes_Sum",
        label="Write Throughput",
        metric_name="write_bytes",
        param_key="write_throughput_levels",
        render_type=RenderType.BYTES,
        levels_type=LevelsType.UPPER,
    ),
    # Queue Length
    MetricSpec(
        metric_key="VolumeQueueLength_Average",
        label="Queue Length",
        metric_name="queue_length",
        param_key="queue_length_levels",
        render_type=RenderType.FLOAT,
        levels_type=LevelsType.UPPER,
    ),
    # Burst Balance (lower is bad for gp2 volumes)
    MetricSpec(
        metric_key="BurstBalance_Average",
        label="Burst Balance",
        metric_name="burst_balance",
        param_key="burst_balance_levels",
        render_type=RenderType.PERCENT,
        levels_type=LevelsType.LOWER,
    ),
]

# Informational metrics
EBS_INFO_METRICS = [
    InfoMetricSpec(
        metric_key="VolumeIdleTime_Sum",
        label="Idle Time",
        metric_name="idle_time",
        render_type=RenderType.TIMESPAN,
    ),
    # Shown in the service details only
    InfoMetricSpec(
        metric_key="VolumeThroughputPercentage_Average",
        label="Throughput Percentage",
        metric_name="throughput_percentage",
        render_type=RenderType.PERCENT,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="VolumeConsumedReadWriteOps_Sum",
        label="Consumed Read/Write Ops",
        metric_name="consumed_read_write_ops",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
]


def _check_ebs_latency(
    metrics_found: dict[str, dict[str, Any]],
    _params: dict[str, Any],
    metric_prefix: str,
    **_kwargs: Any,
) -> CheckResult:
    """Check EBS latency calculated from total time / ops."""
    for op_type in ["Read", "Write"]:
        time_key = f"VolumeTotal{op_type}Time_Sum"
        ops_key = f"Volume{op_type}Ops_Sum"
        if time_key in metrics_found and ops_key in metrics_found:
            total_time = metrics_found[time_key].get("value", 0)
            ops = metrics_found[ops_key].get("value", 0)
            if ops > 0:
                latency_ms = (total_time / ops) * 1000
                yield Result(state=State.OK, summary=f"{op_type} Latency: {latency_ms:.2f} ms")
                yield Metric(f"{metric_prefix}_{op_type.lower()}_latency", latency_ms)


# Create the check plugin using the factory
check_plugin_aws_cloudwatch_ebs = create_cloudwatch_check(
    CheckConfig(
        service_key=SERVICE_EBS,
        service_name="EBS",
        resource_type="volume",
        metric_prefix="ebs",
        metric_specs=EBS_METRIC_SPECS,
        info_metrics=EBS_INFO_METRICS,
        post_check_hook=_check_ebs_latency,
    )
)
