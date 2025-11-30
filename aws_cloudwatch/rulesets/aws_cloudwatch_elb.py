#!/usr/bin/env python3
"""WATO ruleset for AWS CloudWatch ELB Classic check parameters."""

from ..lib.threshold_types import milliseconds_threshold, percent_threshold
from .ruleset_generator import generate_rule_spec

# ELB Classic threshold definitions
ELB_THRESHOLDS = [
    milliseconds_threshold(
        "latency_levels",
        "Latency (ms)",
        "Alert when request latency exceeds these thresholds.",
    ),
    percent_threshold(
        "unhealthy_hosts_levels",
        "Unhealthy Hosts (%)",
        "Alert when percentage of unhealthy hosts exceeds these thresholds.",
    ),
]

rule_spec_aws_cloudwatch_elb = generate_rule_spec("elb", "ELB Classic", ELB_THRESHOLDS)
