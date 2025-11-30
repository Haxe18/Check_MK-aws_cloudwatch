#!/usr/bin/env python3
"""Checkmk check plugin for AWS Lambda CloudWatch metrics.

This module provides the check plugin for Lambda function metrics
with configurable thresholds for Duration, Errors, and Throttles.
"""

from .aws_cloudwatch_helpers import (
    SERVICE_LAMBDA,
    SERVICE_LAMBDA_INSIGHTS,
    CheckConfig,
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

# Create the check plugin using the factory
# Lambda uses multiple service filters (aws_lambda + lambda_insights)
check_plugin_aws_cloudwatch_lambda = create_cloudwatch_check(
    CheckConfig(
        service_key=[SERVICE_LAMBDA, SERVICE_LAMBDA_INSIGHTS],
        service_name="Lambda",
        resource_type="function",
        metric_prefix="lambda",
        metric_specs=LAMBDA_METRIC_SPECS,
    )
)
