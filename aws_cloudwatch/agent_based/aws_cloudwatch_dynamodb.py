#!/usr/bin/env python3
"""Checkmk check plugin for AWS DynamoDB CloudWatch metrics.

This module provides the check plugin for DynamoDB table metrics
with configurable thresholds for Capacity, Throttles, and Latency.
"""

from typing import Any

from cmk.agent_based.v2 import CheckResult, State, check_levels

from .aws_cloudwatch_helpers import (
    SERVICE_DYNAMODB,
    CheckConfig,
    InfoMetricSpec,
    LevelsType,
    MetricSpec,
    RenderType,
    create_cloudwatch_check,
)

# DynamoDB-specific metric specifications
DYNAMODB_METRIC_SPECS = [
    # Consumed Capacity
    MetricSpec(
        metric_key="ConsumedReadCapacityUnits_Sum",
        label="Consumed Read Capacity",
        metric_name="consumed_read_capacity",
        param_key="read_capacity_levels",
        render_type=RenderType.UNITS,
        levels_type=LevelsType.UPPER,
    ),
    MetricSpec(
        metric_key="ConsumedWriteCapacityUnits_Sum",
        label="Consumed Write Capacity",
        metric_name="consumed_write_capacity",
        param_key="write_capacity_levels",
        render_type=RenderType.UNITS,
        levels_type=LevelsType.UPPER,
    ),
    # Latency
    MetricSpec(
        metric_key="SuccessfulRequestLatency_Average",
        label="Request Latency",
        metric_name="request_latency",
        param_key="latency_levels",
        render_type=RenderType.MILLISECONDS,
        levels_type=LevelsType.UPPER,
    ),
]


def _dynamodb_system_error_state(value: float) -> State:
    """Determine state for DynamoDB system errors."""
    return State.CRIT if value > 0 else State.OK


# Informational metrics with custom state functions
DYNAMODB_INFO_METRICS = [
    InfoMetricSpec(
        metric_key="SystemErrors_Sum",
        label="System Errors",
        metric_name="system_errors",
        render_type=RenderType.INTEGER,
        state_func=_dynamodb_system_error_state,
    ),
    InfoMetricSpec(
        metric_key="ProvisionedReadCapacityUnits_Average",
        label="Provisioned Read",
        metric_name="provisioned_read",
        render_type=RenderType.UNITS,
    ),
    InfoMetricSpec(
        metric_key="ProvisionedWriteCapacityUnits_Average",
        label="Provisioned Write",
        metric_name="provisioned_write",
        render_type=RenderType.UNITS,
    ),
    # Shown in the service details only
    InfoMetricSpec(
        metric_key="ConditionalCheckFailedRequests_Sum",
        label="Conditional Check Failed",
        metric_name="conditional_check_failed",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="TransactionConflict_Sum",
        label="Transaction Conflicts",
        metric_name="transaction_conflicts",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
]


def _check_dynamodb_throttles(
    metrics_found: dict[str, dict[str, Any]],
    params: dict[str, Any],
    metric_prefix: str,
    **_kwargs: Any,
) -> CheckResult:
    """Check DynamoDB throttle events (always process even if 0).

    Throttle events are critical for DynamoDB performance monitoring
    and should always be checked regardless of whether the metric exists.
    """
    # Read throttles
    read_throttle_value = 0
    if "ReadThrottleEvents_Sum" in metrics_found:
        read_throttle_value = metrics_found["ReadThrottleEvents_Sum"].get("value", 0)
    yield from check_levels(
        read_throttle_value,
        levels_upper=params.get("read_throttle_levels"),
        metric_name=f"{metric_prefix}_read_throttle_events",
        label="Read Throttles",
        render_func=lambda v: f"{v:.0f}",
    )

    # Write throttles
    write_throttle_value = 0
    if "WriteThrottleEvents_Sum" in metrics_found:
        write_throttle_value = metrics_found["WriteThrottleEvents_Sum"].get("value", 0)
    yield from check_levels(
        write_throttle_value,
        levels_upper=params.get("write_throttle_levels"),
        metric_name=f"{metric_prefix}_write_throttle_events",
        label="Write Throttles",
        render_func=lambda v: f"{v:.0f}",
    )


# Create the check plugin using the factory
check_plugin_aws_cloudwatch_dynamodb = create_cloudwatch_check(
    CheckConfig(
        service_key=SERVICE_DYNAMODB,
        service_name="DynamoDB",
        resource_type="table",
        metric_prefix="dynamodb",
        metric_specs=DYNAMODB_METRIC_SPECS,
        info_metrics=DYNAMODB_INFO_METRICS,
        post_check_hook=_check_dynamodb_throttles,
    )
)
