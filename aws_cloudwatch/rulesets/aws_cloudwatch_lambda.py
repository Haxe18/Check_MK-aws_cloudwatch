#!/usr/bin/env python3
"""WATO ruleset for AWS CloudWatch Lambda check parameters."""

from ..lib.threshold_types import float_threshold, milliseconds_threshold
from .ruleset_generator import generate_rule_spec

# Lambda threshold definitions
LAMBDA_THRESHOLDS = [
    milliseconds_threshold(
        "duration_levels",
        "Duration (Milliseconds)",
        "Alert when Lambda function execution duration exceeds these thresholds.",
    ),
    float_threshold(
        "errors_levels",
        "Errors (Count)",
        "Alert when Lambda function error count exceeds these thresholds.",
    ),
    float_threshold(
        "throttles_levels",
        "Throttles (Count)",
        "Alert when Lambda function throttle count exceeds these thresholds. "
        "Throttles occur when concurrency limits are reached.",
    ),
    float_threshold(
        "concurrency_levels",
        "Concurrent Executions",
        "Alert when concurrent executions exceed these thresholds. "
        "Useful for monitoring functions approaching concurrency limits.",
    ),
    float_threshold(
        "invocations_levels",
        "Invocations (Count)",
        "Alert when Lambda function invocation count exceeds these thresholds. "
        "Useful for detecting unexpected traffic spikes.",
    ),
]

rule_spec_aws_cloudwatch_lambda = generate_rule_spec("lambda", "Lambda", LAMBDA_THRESHOLDS)
