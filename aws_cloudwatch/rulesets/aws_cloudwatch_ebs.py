#!/usr/bin/env python3
"""WATO ruleset for AWS CloudWatch EBS check parameters."""

from ..lib.threshold_types import (
    LevelDirection,
    datasize_threshold,
    float_threshold,
    percent_threshold,
)
from .ruleset_generator import generate_rule_spec

# EBS threshold definitions
EBS_THRESHOLDS = [
    float_threshold(
        "read_ops_levels",
        "Read Operations (per period)",
        "Alert when read operations exceed these thresholds.",
    ),
    float_threshold(
        "write_ops_levels",
        "Write Operations (per period)",
        "Alert when write operations exceed these thresholds.",
    ),
    datasize_threshold(
        "read_throughput_levels",
        "Read Throughput (per period)",
        "Alert when read throughput exceeds these thresholds.",
    ),
    datasize_threshold(
        "write_throughput_levels",
        "Write Throughput (per period)",
        "Alert when write throughput exceeds these thresholds.",
    ),
    float_threshold(
        "queue_length_levels",
        "Queue Length",
        "Alert when volume queue length exceeds these thresholds. "
        "High queue length indicates I/O bottleneck.",
    ),
    percent_threshold(
        "burst_balance_levels",
        "Burst Balance (%)",
        "Alert when burst balance falls below these thresholds. "
        "Only applicable to gp2 volumes.",
        direction=LevelDirection.LOWER,
    ),
]

rule_spec_aws_cloudwatch_ebs = generate_rule_spec("ebs", "EBS", EBS_THRESHOLDS)
