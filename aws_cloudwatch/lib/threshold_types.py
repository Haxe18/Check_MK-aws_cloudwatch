#!/usr/bin/env python3
"""Threshold type definitions for AWS CloudWatch check parameters.

This module provides the ThresholdDef dataclass and ThresholdType enum
for declarative definition of ruleset parameters.
"""

from dataclasses import dataclass
from enum import Enum

#: AWS CloudWatch free tier limit for GetMetricStatistics API calls per month.
#: Used in both the agent-side cache/orchestrator and the WATO ruleset texts.
CLOUDWATCH_FREE_TIER_LIMIT: int = 1_000_000


class ThresholdType(Enum):
    """Type of threshold form specification."""

    PERCENT = "percent"  # Percentage values (0-100%)
    FLOAT = "float"  # Generic float values
    MILLISECONDS = "milliseconds"  # Time in milliseconds
    SECONDS = "seconds"  # Time in seconds (for TimeSpan form)
    DATASIZE = "datasize"  # Data size (MB/GB range)
    DATASIZE_LARGE = "datasize_large"  # Large data size (GB/TB range)


class LevelDirection(Enum):
    """Direction for threshold levels."""

    UPPER = "upper"  # Warn when value exceeds threshold
    LOWER = "lower"  # Warn when value falls below threshold


@dataclass
class ThresholdDef:
    """Definition for a single threshold parameter.

    Attributes:
        key: Parameter key in the ruleset (e.g., "cpu_levels")
        title: Display title for the form element
        help_text: Help text describing the threshold
        threshold_type: Type of threshold (PERCENT, FLOAT, etc.)
        direction: UPPER or LOWER for threshold direction
        unit: Optional unit symbol for FLOAT type
    """

    key: str
    title: str
    help_text: str
    threshold_type: ThresholdType
    direction: LevelDirection = LevelDirection.UPPER
    unit: str = ""


# Convenience functions for creating common threshold definitions


def percent_threshold(
    key: str,
    title: str,
    help_text: str,
    direction: LevelDirection = LevelDirection.UPPER,
) -> ThresholdDef:
    """Create a percentage threshold definition."""
    return ThresholdDef(
        key=key,
        title=title,
        help_text=help_text,
        threshold_type=ThresholdType.PERCENT,
        direction=direction,
    )


def float_threshold(
    key: str,
    title: str,
    help_text: str,
    unit: str = "",
    direction: LevelDirection = LevelDirection.UPPER,
) -> ThresholdDef:
    """Create a float threshold definition."""
    return ThresholdDef(
        key=key,
        title=title,
        help_text=help_text,
        threshold_type=ThresholdType.FLOAT,
        direction=direction,
        unit=unit,
    )


def milliseconds_threshold(
    key: str,
    title: str,
    help_text: str,
    direction: LevelDirection = LevelDirection.UPPER,
) -> ThresholdDef:
    """Create a milliseconds threshold definition."""
    return ThresholdDef(
        key=key,
        title=title,
        help_text=help_text,
        threshold_type=ThresholdType.MILLISECONDS,
        direction=direction,
    )


def seconds_threshold(
    key: str,
    title: str,
    help_text: str,
    direction: LevelDirection = LevelDirection.UPPER,
) -> ThresholdDef:
    """Create a seconds/timespan threshold definition."""
    return ThresholdDef(
        key=key,
        title=title,
        help_text=help_text,
        threshold_type=ThresholdType.SECONDS,
        direction=direction,
    )


def datasize_threshold(
    key: str,
    title: str,
    help_text: str,
    direction: LevelDirection = LevelDirection.UPPER,
) -> ThresholdDef:
    """Create a data size (MB/GB) threshold definition."""
    return ThresholdDef(
        key=key,
        title=title,
        help_text=help_text,
        threshold_type=ThresholdType.DATASIZE,
        direction=direction,
    )


def datasize_large_threshold(
    key: str,
    title: str,
    help_text: str,
    direction: LevelDirection = LevelDirection.UPPER,
) -> ThresholdDef:
    """Create a large data size (GB/TB) threshold definition."""
    return ThresholdDef(
        key=key,
        title=title,
        help_text=help_text,
        threshold_type=ThresholdType.DATASIZE_LARGE,
        direction=direction,
    )
