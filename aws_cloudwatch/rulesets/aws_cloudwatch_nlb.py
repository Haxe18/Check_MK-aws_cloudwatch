#!/usr/bin/env python3
"""WATO ruleset for AWS CloudWatch NLB check parameters."""

from ..lib.threshold_types import (
    datasize_large_threshold,
    float_threshold,
    percent_threshold,
)
from .ruleset_generator import generate_rule_spec

# NLB threshold definitions
NLB_THRESHOLDS = [
    float_threshold(
        "active_flows_levels",
        "Active Flows",
        "Alert when active flow count exceeds these thresholds.",
    ),
    float_threshold(
        "new_flows_levels",
        "New Flows (per period)",
        "Alert when new flow count exceeds these thresholds.",
    ),
    datasize_large_threshold(
        "processed_bytes_levels",
        "Processed Bytes (per period)",
        "Alert when processed bytes exceed these thresholds.",
    ),
    percent_threshold(
        "unhealthy_targets_levels",
        "Unhealthy Targets (%)",
        "Alert when percentage of unhealthy targets exceeds these thresholds.",
    ),
]

rule_spec_aws_cloudwatch_nlb = generate_rule_spec("nlb", "NLB", NLB_THRESHOLDS)
