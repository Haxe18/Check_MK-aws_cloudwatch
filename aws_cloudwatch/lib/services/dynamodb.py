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
            MetricDefinition("SuccessfulRequestLatency", "Average", "Milliseconds"),
            MetricDefinition("GetRecords.SuccessfulRequestLatency", "Average", "Milliseconds"),
            # Error metrics
            MetricDefinition("UserErrors", "Sum", "Count"),
            MetricDefinition("SystemErrors", "Sum", "Count"),
            MetricDefinition("ConditionalCheckFailedRequests", "Sum", "Count"),
            # Request metrics
            MetricDefinition("ThrottledRequests", "Sum", "Count"),
            MetricDefinition("TransactionConflict", "Sum", "Count"),
            # Item counts
            MetricDefinition("ReturnedItemCount", "Sum", "Count"),
            MetricDefinition("ReturnedRecordsCount", "Sum", "Count"),
            # On-demand capacity
            MetricDefinition("AccountMaxReads", "Maximum", "Count"),
            MetricDefinition("AccountMaxTableLevelReads", "Maximum", "Count"),
            MetricDefinition("AccountMaxWrites", "Maximum", "Count"),
            MetricDefinition("AccountMaxTableLevelWrites", "Maximum", "Count"),
            MetricDefinition(
                "AccountProvisionedReadCapacityUtilization", "Average", "Percent"
            ),
            MetricDefinition(
                "AccountProvisionedWriteCapacityUtilization", "Average", "Percent"
            ),
            # Global tables
            MetricDefinition("ReplicationLatency", "Average", "Milliseconds"),
            MetricDefinition("PendingReplicationCount", "Sum", "Count"),
        ]
