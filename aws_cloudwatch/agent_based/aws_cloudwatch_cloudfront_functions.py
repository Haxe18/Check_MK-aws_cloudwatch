#!/usr/bin/env python3
"""Checkmk check plugin for AWS CloudFront Functions CloudWatch metrics."""

from .aws_cloudwatch_helpers import (
    SERVICE_CLOUDFRONT_FUNCTIONS,
    CheckConfig,
    InfoMetricSpec,
    LevelsType,
    MetricSpec,
    RenderType,
    create_cloudwatch_check,
)

CLOUDFRONT_FUNCTIONS_METRIC_SPECS = [
    MetricSpec(
        metric_key="FunctionComputeUtilization_Average",
        label="Compute Utilization",
        metric_name="compute_utilization",
        param_key="compute_utilization_levels",
        render_type=RenderType.PERCENT,
        levels_type=LevelsType.UPPER,
    ),
    MetricSpec(
        metric_key="FunctionExecutionErrors_Sum",
        label="Execution Errors",
        metric_name="execution_errors",
        param_key="execution_errors_levels",
        render_type=RenderType.INTEGER,
        levels_type=LevelsType.UPPER,
    ),
    MetricSpec(
        metric_key="FunctionValidationErrors_Sum",
        label="Validation Errors",
        metric_name="validation_errors",
        param_key="validation_errors_levels",
        render_type=RenderType.INTEGER,
        levels_type=LevelsType.UPPER,
    ),
]

CLOUDFRONT_FUNCTIONS_INFO_METRICS = [
    InfoMetricSpec(
        metric_key="FunctionInvocations_Sum",
        label="Invocations",
        metric_name="invocations",
        render_type=RenderType.INTEGER,
    ),
]

check_plugin_aws_cloudwatch_cloudfront_functions = create_cloudwatch_check(
    CheckConfig(
        service_key=SERVICE_CLOUDFRONT_FUNCTIONS,
        service_name="CloudFront Functions",
        resource_type="function",
        metric_prefix="cloudfront_functions",
        metric_specs=CLOUDFRONT_FUNCTIONS_METRIC_SPECS,
        info_metrics=CLOUDFRONT_FUNCTIONS_INFO_METRICS,
    )
)
