#!/usr/bin/env python3
"""WATO ruleset for AWS CloudWatch CloudFront Functions check parameters."""

from ..lib.threshold_types import float_threshold, percent_threshold
from .ruleset_generator import generate_rule_spec

CLOUDFRONT_FUNCTIONS_THRESHOLDS = [
    percent_threshold(
        "compute_utilization_levels",
        "Compute Utilization (%)",
        "Alert when CloudFront Functions compute utilization exceeds these thresholds.",
    ),
    float_threshold(
        "execution_errors_levels",
        "Execution Errors",
        "Alert when CloudFront Functions execution errors exceed these thresholds.",
    ),
    float_threshold(
        "validation_errors_levels",
        "Validation Errors",
        "Alert when CloudFront Functions validation errors exceed these thresholds.",
    ),
]

rule_spec_aws_cloudwatch_cloudfront_functions = generate_rule_spec(
    "cloudfront_functions",
    "CloudFront Functions",
    CLOUDFRONT_FUNCTIONS_THRESHOLDS,
    help_suffix="Note: CloudFront Functions metrics are only available in us-east-1.",
)
