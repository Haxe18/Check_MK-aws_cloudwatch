#!/usr/bin/env python3
"""WATO ruleset for AWS CloudWatch DynamoDB check parameters."""

from ..lib.threshold_types import float_threshold, milliseconds_threshold
from .ruleset_generator import generate_rule_spec

# DynamoDB threshold definitions
DYNAMODB_THRESHOLDS = [
    float_threshold(
        "read_capacity_levels",
        "Consumed Read Capacity Units",
        "Alert when consumed read capacity exceeds these thresholds. "
        "This is measured per period (typically 5 minutes).",
        unit="units",
    ),
    float_threshold(
        "write_capacity_levels",
        "Consumed Write Capacity Units",
        "Alert when consumed write capacity exceeds these thresholds. "
        "This is measured per period (typically 5 minutes).",
        unit="units",
    ),
    float_threshold(
        "read_throttle_levels",
        "Read Throttle Events",
        "Alert when read throttle events exceed these thresholds. "
        "Throttles indicate capacity issues.",
    ),
    float_threshold(
        "write_throttle_levels",
        "Write Throttle Events",
        "Alert when write throttle events exceed these thresholds. "
        "Throttles indicate capacity issues.",
    ),
    milliseconds_threshold(
        "latency_levels",
        "Request Latency (ms)",
        "Alert when the average request latency of the slowest operation "
        "(e.g. Scan, Query, GetItem) exceeds these thresholds.",
    ),
]

rule_spec_aws_cloudwatch_dynamodb = generate_rule_spec(
    "dynamodb", "DynamoDB", DYNAMODB_THRESHOLDS
)
