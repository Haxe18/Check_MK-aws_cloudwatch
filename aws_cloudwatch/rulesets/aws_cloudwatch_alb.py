#!/usr/bin/env python3
"""WATO ruleset for AWS CloudWatch ALB check parameters."""

from ..lib.threshold_types import (
    float_threshold,
    milliseconds_threshold,
    percent_threshold,
)
from .ruleset_generator import generate_rule_spec

# ALB threshold definitions
ALB_THRESHOLDS = [
    milliseconds_threshold(
        "response_time_levels",
        "Target Response Time (ms)",
        "Alert when target response time exceeds these thresholds.",
    ),
    percent_threshold(
        "unhealthy_targets_levels",
        "Unhealthy Targets (%)",
        "Alert when percentage of unhealthy targets exceeds these thresholds.",
    ),
    float_threshold(
        "active_connections_levels",
        "Active Connections",
        "Alert when active connection count exceeds these thresholds.",
    ),
]

rule_spec_aws_cloudwatch_alb = generate_rule_spec("alb", "ALB", ALB_THRESHOLDS)
