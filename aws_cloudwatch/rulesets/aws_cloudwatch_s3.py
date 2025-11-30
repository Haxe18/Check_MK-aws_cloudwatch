#!/usr/bin/env python3
"""WATO ruleset for AWS CloudWatch S3 check parameters."""

from ..lib.threshold_types import datasize_large_threshold, float_threshold
from .ruleset_generator import generate_rule_spec

# S3 threshold definitions
S3_THRESHOLDS = [
    datasize_large_threshold(
        "bucket_size_levels",
        "Bucket Size",
        "Alert when bucket size exceeds these thresholds.",
    ),
    float_threshold(
        "object_count_levels",
        "Number of Objects",
        "Alert when object count exceeds these thresholds.",
    ),
]

rule_spec_aws_cloudwatch_s3 = generate_rule_spec(
    "s3",
    "S3",
    S3_THRESHOLDS,
    help_suffix="Note: S3 CloudWatch metrics are updated daily, not real-time.",
)
