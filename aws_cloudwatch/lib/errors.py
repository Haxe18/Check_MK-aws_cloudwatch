#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Error collection utilities for CloudWatch monitoring.

This module provides error aggregation functionality to track
and report errors that occur during CloudWatch data collection.
"""

import time
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CloudWatchError:
    """A single error that occurred during CloudWatch data collection.

    Attributes:
        category: Error category ("discovery", "metrics", "api", "cache")
        service: AWS service name (e.g., "ec2", "rds")
        region: AWS region where the error occurred
        message: Error message
        hint: Optional IAM permission hint for access errors
        timestamp: Unix timestamp when the error occurred
    """

    category: str
    service: str
    region: str
    message: str
    hint: str | None = None
    timestamp: float = field(default_factory=time.time)


class ErrorCollector:
    """Collects and aggregates errors during CloudWatch data collection.

    Provides methods to add and count errors and export them for the check output.
    """

    def __init__(self) -> None:
        """Initialize an empty error collector."""
        self._errors: list[CloudWatchError] = []

    def add(
        self,
        category: str,
        service: str,
        region: str,
        message: str,
        hint: str | None = None,
    ) -> None:
        """Add an error to the collection.

        Args:
            category: Error category ("discovery", "metrics", "api", "cache")
            service: AWS service name
            region: AWS region
            message: Error message
            hint: Optional IAM permission hint for access errors
        """
        self._errors.append(CloudWatchError(category, service, region, message, hint))

    def count(self) -> int:
        """Get the total number of errors.

        Returns:
            Number of errors collected
        """
        return len(self._errors)

    def to_list(self) -> list[dict[str, Any]]:
        """Convert errors to a list of dictionaries for JSON serialization.

        Returns:
            List of error dictionaries
        """
        return [asdict(e) for e in self._errors]
