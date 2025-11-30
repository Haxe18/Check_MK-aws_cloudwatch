#!/usr/bin/env python3
"""Checkmk check plugin for AWS RDS CloudWatch metrics.

This module provides the check plugin for RDS database instance metrics
with configurable thresholds for CPU, Storage, Connections, and Latency.
"""

from typing import Any

from cmk.agent_based.v2 import CheckResult, Metric, Result, State

from .aws_cloudwatch_helpers import (
    SERVICE_RDS,
    CheckConfig,
    LevelsType,
    MetricSpec,
    RenderType,
    create_cloudwatch_check,
)

# RDS-specific metric specifications
RDS_METRIC_SPECS = [
    # CPU Utilization
    MetricSpec(
        metric_key="CPUUtilization_Average",
        label="CPU Utilization",
        metric_name="cpu_utilization",
        param_key="cpu_levels",
        render_type=RenderType.PERCENT,
        levels_type=LevelsType.UPPER,
    ),
    # Storage (lower is bad)
    MetricSpec(
        metric_key="FreeStorageSpace_Average",
        label="Free Storage",
        metric_name="free_storage",
        param_key="storage_levels",
        render_type=RenderType.BYTES,
        levels_type=LevelsType.LOWER,
    ),
    # Memory (lower is bad)
    MetricSpec(
        metric_key="FreeableMemory_Average",
        label="Freeable Memory",
        metric_name="freeable_memory",
        param_key="memory_levels",
        render_type=RenderType.BYTES,
        levels_type=LevelsType.LOWER,
    ),
    # Connections
    MetricSpec(
        metric_key="DatabaseConnections_Average",
        label="Connections",
        metric_name="connections",
        param_key="connections_levels",
        render_type=RenderType.INTEGER,
        levels_type=LevelsType.UPPER,
    ),
    # Replica Lag
    MetricSpec(
        metric_key="ReplicaLag_Average",
        label="Replica Lag",
        metric_name="replica_lag",
        param_key="replica_lag_levels",
        render_type=RenderType.TIMESPAN,
        levels_type=LevelsType.UPPER,
    ),
    # Latency metrics (stored in seconds, displayed as ms)
    MetricSpec(
        metric_key="ReadLatency_Average",
        label="Read Latency",
        metric_name="read_latency",
        param_key="read_latency_levels",
        render_type=RenderType.MILLISECONDS_FROM_SECONDS,
        levels_type=LevelsType.UPPER,
    ),
    MetricSpec(
        metric_key="WriteLatency_Average",
        label="Write Latency",
        metric_name="write_latency",
        param_key="write_latency_levels",
        render_type=RenderType.MILLISECONDS_FROM_SECONDS,
        levels_type=LevelsType.UPPER,
    ),
]


def _check_rds_iops(
    metrics_found: dict[str, dict[str, Any]],
    _params: dict[str, Any],
    metric_prefix: str,
    **_kwargs: Any,
) -> CheckResult:
    """Check RDS IOPS with custom /s formatting."""
    for metric_key, label, metric_name in [
        ("ReadIOPS_Average", "Read IOPS", "read_iops"),
        ("WriteIOPS_Average", "Write IOPS", "write_iops"),
    ]:
        if metric_key in metrics_found:
            metric = metrics_found[metric_key]
            value = metric.get("value", 0)
            yield Result(state=State.OK, summary=f"{label}: {value:.0f}/s")
            yield Metric(f"{metric_prefix}_{metric_name}", value)


# Create the check plugin using the factory
check_plugin_aws_cloudwatch_rds = create_cloudwatch_check(
    CheckConfig(
        service_key=SERVICE_RDS,
        service_name="RDS",
        resource_type="instance",
        metric_prefix="rds",
        metric_specs=RDS_METRIC_SPECS,
        post_check_hook=_check_rds_iops,
    )
)
