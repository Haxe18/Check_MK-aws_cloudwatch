#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DynamoDB service section.

This module provides CloudWatch monitoring for DynamoDB tables.
"""

from ..base import CloudWatchSection
from ..types import MetricDefinition


class DynamoDBSection(CloudWatchSection):
    """DynamoDB table metrics.

    Monitors capacity, latency, throttling, and errors.
    """

    @property
    def name(self) -> str:
        return "dynamodb"

    @property
    def title(self) -> str:
        return "DynamoDB"

    @property
    def namespace(self) -> str:
        return "AWS/DynamoDB"

    @property
    def dimension_key(self) -> str:
        return "TableName"

    @property
    def metrics(self) -> list[MetricDefinition]:
        return [
            # Capacity metrics
            MetricDefinition("ConsumedReadCapacityUnits", "Sum", "Count"),
            MetricDefinition("ConsumedWriteCapacityUnits", "Sum", "Count"),
            MetricDefinition("ProvisionedReadCapacityUnits", "Average", "Count"),
            MetricDefinition("ProvisionedWriteCapacityUnits", "Average", "Count"),
            MetricDefinition("ReadThrottleEvents", "Sum", "Count"),
            MetricDefinition("WriteThrottleEvents", "Sum", "Count"),
            # Latency metrics
            MetricDefinition(
                "SuccessfulRequestLatency",
                "Average",
                "Milliseconds",
                extra_dimension="Operation",
                combine="max",
                # Operations used only now and then would cost a call each refresh
                skip_idle=True,
            ),
            # Error metrics (no skip_idle: a fresh burst must not be missed)
            MetricDefinition("SystemErrors", "Sum", "Count", extra_dimension="Operation"),
            MetricDefinition("ConditionalCheckFailedRequests", "Sum", "Count"),
            # Request metrics
            MetricDefinition("TransactionConflict", "Sum", "Count"),
        ]
