#!/usr/bin/env python3
"""WATO ruleset for AWS CloudWatch EC2 check parameters."""

from ..lib.threshold_types import (
    LevelDirection,
    datasize_threshold,
    float_threshold,
    percent_threshold,
)
from .ruleset_generator import generate_rule_spec

# EC2 threshold definitions
EC2_THRESHOLDS = [
    percent_threshold(
        "cpu_levels",
        "CPU Utilization (%)",
        "Alert when EC2 CPU utilization exceeds these thresholds.",
    ),
    datasize_threshold(
        "network_in_levels",
        "Network In (per period)",
        "Alert when incoming network traffic exceeds these thresholds. "
        "Measured per CloudWatch period (typically 5 minutes).",
    ),
    datasize_threshold(
        "network_out_levels",
        "Network Out (per period)",
        "Alert when outgoing network traffic exceeds these thresholds. "
        "Measured per CloudWatch period (typically 5 minutes).",
    ),
    float_threshold(
        "disk_read_ops_levels",
        "Disk Read Operations (per period)",
        "Alert when disk read operations exceed these thresholds.",
    ),
    float_threshold(
        "disk_write_ops_levels",
        "Disk Write Operations (per period)",
        "Alert when disk write operations exceed these thresholds.",
    ),
    float_threshold(
        "cpu_credit_balance_levels",
        "CPU Credit Balance (for burstable instances)",
        "Alert when CPU credit balance falls below these thresholds. "
        "Only applicable to T2/T3 burstable instance types.",
        direction=LevelDirection.LOWER,
    ),
]

rule_spec_aws_cloudwatch_ec2 = generate_rule_spec("ec2", "EC2", EC2_THRESHOLDS)
