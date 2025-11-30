#!/usr/bin/env python3
"""WATO ruleset for AWS CloudWatch RDS check parameters."""

from ..lib.threshold_types import (
    LevelDirection,
    datasize_large_threshold,
    datasize_threshold,
    float_threshold,
    percent_threshold,
    seconds_threshold,
)
from .ruleset_generator import generate_rule_spec

# RDS threshold definitions
RDS_THRESHOLDS = [
    percent_threshold(
        "cpu_levels",
        "CPU Utilization (%)",
        "Alert when RDS CPU utilization exceeds these thresholds.",
    ),
    datasize_large_threshold(
        "storage_levels",
        "Free Storage Space",
        "Alert when free storage space falls below these thresholds.",
        direction=LevelDirection.LOWER,
    ),
    datasize_threshold(
        "memory_levels",
        "Freeable Memory",
        "Alert when freeable memory falls below these thresholds.",
        direction=LevelDirection.LOWER,
    ),
    float_threshold(
        "connections_levels",
        "Database Connections",
        "Alert when the number of database connections exceeds these thresholds.",
    ),
    seconds_threshold(
        "replica_lag_levels",
        "Replica Lag",
        "Alert when replica lag exceeds these thresholds (for read replicas).",
    ),
    float_threshold(
        "read_latency_levels",
        "Read Latency",
        "Alert when read latency exceeds these thresholds.",
        unit="s",
    ),
    float_threshold(
        "write_latency_levels",
        "Write Latency",
        "Alert when write latency exceeds these thresholds.",
        unit="s",
    ),
]

rule_spec_aws_cloudwatch_rds = generate_rule_spec("rds", "RDS", RDS_THRESHOLDS)
