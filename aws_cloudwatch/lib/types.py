#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Data types for AWS CloudWatch monitoring.

This module defines the core data structures used throughout the
CloudWatch monitoring implementation.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricDefinition:
    """Definition of a CloudWatch metric to fetch.

    Attributes:
        name: CloudWatch metric name (e.g., "CPUUtilization")
        stat: Statistic to retrieve ("Sum", "Average", "Maximum", "Minimum")
        unit: Unit of measurement (e.g., "Percent", "Bytes", "Count")
    """

    name: str
    stat: str
    unit: str


@dataclass
class Resource:
    """A discovered AWS resource.

    Attributes:
        id: Resource identifier for display (e.g., "i-1234567890abcdef0")
        dimensions: CloudWatch dimensions for API calls
        available_metrics: List of metric names available for this resource
        metadata: Optional service-specific metadata (e.g., CloudFront comment/URL)
    """

    id: str  # pylint: disable=invalid-name
    dimensions: dict[str, str] = field(default_factory=dict)
    available_metrics: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "dimensions": self.dimensions,
            "available_metrics": self.available_metrics,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Resource":
        """Deserialize from cached dictionary."""
        return cls(
            id=data["id"],
            dimensions=data.get("dimensions", {}),
            available_metrics=data.get("available_metrics", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class MetricResult:
    """Result of fetching a single metric.

    Attributes:
        resource_id: Identifier of the resource
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement
        stat: Statistic type used
        timestamp: ISO timestamp of the datapoint (or None)
        period: Time period in seconds
        region: AWS region
    """

    resource_id: str
    metric_name: str
    value: float
    unit: str
    stat: str
    timestamp: str | None
    period: int
    region: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "resource_id": self.resource_id,
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "stat": self.stat,
            "timestamp": self.timestamp,
            "period": self.period,
            "region": self.region,
        }
