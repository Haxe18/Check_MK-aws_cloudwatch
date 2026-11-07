#!/usr/bin/env python3
"""Checkmk check plugin for AWS Lambda CloudWatch metrics.

This module provides the check plugin for Lambda function metrics
with configurable thresholds for Duration, Errors, and Throttles.
"""

from .aws_cloudwatch_helpers import (
    SERVICE_LAMBDA,
    SERVICE_LAMBDA_INSIGHTS,
    CheckConfig,
    InfoMetricSpec,
    LevelsType,
    MetricSpec,
    RenderType,
    create_cloudwatch_check,
)

# Lambda-specific metric specifications
LAMBDA_METRIC_SPECS = [
    # Duration metrics
    MetricSpec(
        metric_key="Duration_Average",
        label="Duration (Average)",
        metric_name="duration_average",
        param_key="duration_levels",
        render_type=RenderType.MILLISECONDS,
        levels_type=LevelsType.UPPER,
    ),
    MetricSpec(
        metric_key="Duration_Maximum",
        label="Duration (Maximum)",
        metric_name="duration_maximum",
        param_key="duration_levels",
        render_type=RenderType.MILLISECONDS,
        levels_type=LevelsType.UPPER,
    ),
    # Errors
    MetricSpec(
        metric_key="Errors_Sum",
        label="Errors",
        metric_name="errors",
        param_key="errors_levels",
        render_type=RenderType.INTEGER,
        levels_type=LevelsType.UPPER,
    ),
    # Throttles
    MetricSpec(
        metric_key="Throttles_Sum",
        label="Throttles",
        metric_name="throttles",
        param_key="throttles_levels",
        render_type=RenderType.INTEGER,
        levels_type=LevelsType.UPPER,
    ),
    # Invocations
    MetricSpec(
        metric_key="Invocations_Sum",
        label="Invocations",
        metric_name="invocations",
        param_key="invocations_levels",
        render_type=RenderType.INTEGER,
        levels_type=LevelsType.UPPER,
    ),
    # Concurrent Executions
    MetricSpec(
        metric_key="ConcurrentExecutions_Maximum",
        label="Concurrent Executions",
        metric_name="concurrent_executions",
        param_key="concurrency_levels",
        render_type=RenderType.INTEGER,
        levels_type=LevelsType.UPPER,
    ),
]

# Informational metrics, shown in the service details only
LAMBDA_INFO_METRICS = [
    InfoMetricSpec(
        metric_key="Duration_Minimum",
        label="Duration (Minimum)",
        metric_name="duration_minimum",
        render_type=RenderType.MILLISECONDS,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="IteratorAge_Average",
        label="Iterator Age",
        metric_name="iterator_age",
        render_type=RenderType.MILLISECONDS,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="DeadLetterErrors_Sum",
        label="Dead Letter Errors",
        metric_name="dead_letter_errors",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="DestinationDeliveryFailures_Sum",
        label="Destination Delivery Failures",
        metric_name="destination_delivery_failures",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="AsyncEventsReceived_Sum",
        label="Async Events Received",
        metric_name="async_events_received",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="AsyncEventAge_Average",
        label="Async Event Age",
        metric_name="async_event_age",
        render_type=RenderType.MILLISECONDS,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="AsyncEventsDropped_Sum",
        label="Async Events Dropped",
        metric_name="async_events_dropped",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="UnreservedConcurrentExecutions_Maximum",
        label="Unreserved Concurrent Executions",
        metric_name="unreserved_concurrent_executions",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="ProvisionedConcurrentExecutions_Maximum",
        label="Provisioned Concurrent Executions",
        metric_name="provisioned_concurrent_executions",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="ProvisionedConcurrencyInvocations_Sum",
        label="Provisioned Concurrency Invocations",
        metric_name="provisioned_concurrency_invocations",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="ProvisionedConcurrencySpilloverInvocations_Sum",
        label="Provisioned Concurrency Spillover",
        metric_name="provisioned_concurrency_spillover",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="ProvisionedConcurrencyUtilization_Maximum",
        label="Provisioned Concurrency Utilization",
        metric_name="provisioned_concurrency_utilization",
        render_type=RenderType.PERCENT,
        value_transform=lambda v: v * 100,  # CloudWatch fraction (0.7) -> percent
        details_only=True,
    ),
    # Lambda Insights
    InfoMetricSpec(
        metric_key="memory_utilization_Average",
        label="Memory Utilization",
        metric_name="memory_utilization",
        render_type=RenderType.PERCENT,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="total_memory_Average",
        label="Total Memory",
        metric_name="total_memory",
        render_type=RenderType.BYTES,
        value_transform=lambda v: v * 1024 * 1024,  # CloudWatch megabytes -> bytes
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="used_memory_max_Maximum",
        label="Used Memory (Maximum)",
        metric_name="used_memory_max",
        render_type=RenderType.BYTES,
        value_transform=lambda v: v * 1024 * 1024,  # CloudWatch megabytes -> bytes
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="cpu_total_time_Sum",
        label="CPU Time",
        metric_name="cpu_total_time",
        render_type=RenderType.MILLISECONDS,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="tx_bytes_Sum",
        label="Network Sent",
        metric_name="tx_bytes",
        render_type=RenderType.BYTES,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="rx_bytes_Sum",
        label="Network Received",
        metric_name="rx_bytes",
        render_type=RenderType.BYTES,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="init_duration_Average",
        label="Init Duration",
        metric_name="init_duration",
        render_type=RenderType.MILLISECONDS,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="cold_starts_Sum",
        label="Cold Starts",
        metric_name="cold_starts",
        render_type=RenderType.INTEGER,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="tmp_used_Maximum",
        label="Temp Space Used",
        metric_name="tmp_used",
        render_type=RenderType.BYTES,
        details_only=True,
    ),
    InfoMetricSpec(
        metric_key="tmp_max_Maximum",
        label="Temp Space Available",
        metric_name="tmp_max",
        render_type=RenderType.BYTES,
        details_only=True,
    ),
]

# Create the check plugin using the factory
# Lambda uses multiple service filters (aws_lambda + lambda_insights)
check_plugin_aws_cloudwatch_lambda = create_cloudwatch_check(
    CheckConfig(
        service_key=[SERVICE_LAMBDA, SERVICE_LAMBDA_INSIGHTS],
        service_name="Lambda",
        resource_type="function",
        metric_prefix="lambda",
        metric_specs=LAMBDA_METRIC_SPECS,
        info_metrics=LAMBDA_INFO_METRICS,
    )
)
