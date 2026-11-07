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
        extra_dimension: Second dimension AWS publishes this metric under only
            (e.g., "TargetGroup"); the metric is then fetched once per value
        combine: How values over all extra_dimension values are merged ("sum" or "max")
        skip_idle: Count the metric as 0 without a call when it had no data in the past
            3 hours (per extra_dimension value, if set; costs one ListMetrics call per
            refresh). Not for metrics that only report now and then and must alert:
            ListMetrics lists new data with a delay, a fresh burst could be missed
    """

    name: str
    stat: str
    unit: str
    extra_dimension: str | None = None
    combine: str = "sum"
    skip_idle: bool = False


@dataclass
class Resource:
    """A discovered AWS resource.

    Attributes:
        id: Resource identifier for display (e.g., "i-1234567890abcdef0")
        dimensions: CloudWatch dimensions for API calls
        available_metrics: List of metric names available for this resource
        metadata: Optional service-specific metadata (e.g., CloudFront comment/URL)
        metric_dimensions: Extra dimension sets per metric name, from ListMetrics
            (only for metrics with MetricDefinition.extra_dimension)
    """

    id: str  # pylint: disable=invalid-name
    dimensions: dict[str, str] = field(default_factory=dict)
    available_metrics: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    metric_dimensions: dict[str, list[dict[str, str]]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "dimensions": self.dimensions,
            "available_metrics": self.available_metrics,
            "metadata": self.metadata,
            "metric_dimensions": self.metric_dimensions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Resource":
        """Deserialize from cached dictionary."""
        return cls(
            id=data["id"],
            dimensions=data.get("dimensions", {}),
            available_metrics=data.get("available_metrics", []),
            metadata=data.get("metadata", {}),
            metric_dimensions=data.get("metric_dimensions", {}),
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
        parts: Value per extra-dimension value (e.g. per TargetGroup) for metrics
            merged by _fetch_combined_metric(); None for all other metrics
    """

    resource_id: str
    metric_name: str
    value: float
    unit: str
    stat: str
    timestamp: str | None
    period: int
    region: str
    parts: dict[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data: dict[str, Any] = {
            "resource_id": self.resource_id,
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "stat": self.stat,
            "timestamp": self.timestamp,
            "period": self.period,
            "region": self.region,
        }
        if self.parts is not None:
            data["parts"] = self.parts
        return data
