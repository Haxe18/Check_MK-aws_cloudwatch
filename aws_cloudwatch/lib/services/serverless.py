#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serverless service sections (Lambda).

This module provides CloudWatch monitoring for Lambda functions.
"""

from dataclasses import replace
from typing import TYPE_CHECKING

from ..base import CloudWatchSection
from ..errors import ErrorCollector
from ..types import MetricDefinition, Resource

if TYPE_CHECKING:
    from ..cache import APICounter
    from ..client import CloudWatchClient


def _is_lambda_edge(resource_id: str) -> bool:
    """Check if resource_id is a Lambda@Edge metric.

    Lambda@Edge functions are always created in us-east-1 (AWS requirement).
    Their metrics appear in other regions with 'us-east-1.' as prefix.
    """
    return resource_id.startswith("us-east-1.")


class LambdaSection(CloudWatchSection):
    """Lambda function metrics.

    Monitors invocations, errors, throttles, duration, and concurrency.
    """

    def __init__(
        self,
        client: "CloudWatchClient",
        api_counter: "APICounter",
        error_collector: ErrorCollector | None = None,
        filter_deleted: bool = False,
    ) -> None:
        """Initialize the section.

        Args:
            client: CloudWatch client for API calls
            api_counter: Counter for tracking API usage
            error_collector: Optional collector for surfacing errors into Checkmk output
            filter_deleted: Check discovered functions against the Lambda API and drop
                deleted ones. Off by default: lambda:ListFunctions also returns the
                environment variables of every function in clear text.
        """
        super().__init__(client, api_counter, error_collector)
        self._filter_deleted = filter_deleted

    @property
    def name(self) -> str:
        return "aws_lambda"

    @property
    def title(self) -> str:
        return "Lambda"

    @property
    def namespace(self) -> str:
        return "AWS/Lambda"

    @property
    def dimension_key(self) -> str:
        return "FunctionName"

    @property
    def metrics(self) -> list[MetricDefinition]:
        metrics = [
            # Invocation metrics
            MetricDefinition("Invocations", "Sum", "Count"),
            MetricDefinition("Errors", "Sum", "Count"),
            MetricDefinition("Throttles", "Sum", "Count"),
            MetricDefinition("DeadLetterErrors", "Sum", "Count"),
            MetricDefinition("DestinationDeliveryFailures", "Sum", "Count"),
            # Duration metrics
            MetricDefinition("Duration", "Average", "Milliseconds"),
            MetricDefinition("Duration", "Maximum", "Milliseconds"),
            MetricDefinition("Duration", "Minimum", "Milliseconds"),
            # Iterator age (for stream-based invocations)
            MetricDefinition("IteratorAge", "Average", "Milliseconds"),
            # Concurrency
            MetricDefinition("ConcurrentExecutions", "Maximum", "Count"),
            MetricDefinition("UnreservedConcurrentExecutions", "Maximum", "Count"),
            MetricDefinition("ProvisionedConcurrentExecutions", "Maximum", "Count"),
            MetricDefinition("ProvisionedConcurrencyInvocations", "Sum", "Count"),
            MetricDefinition("ProvisionedConcurrencySpilloverInvocations", "Sum", "Count"),
            MetricDefinition("ProvisionedConcurrencyUtilization", "Maximum", "Percent"),
            # Async metrics
            MetricDefinition("AsyncEventsReceived", "Sum", "Count"),
            MetricDefinition("AsyncEventAge", "Average", "Milliseconds"),
            MetricDefinition("AsyncEventsDropped", "Sum", "Count"),
        ]
        # Idle or deleted functions count as 0 without a call: most functions run
        # only now and then, a call per metric each refresh would cost the most
        return [replace(m, skip_idle=True) for m in metrics]

    def discover_resources(self) -> list[Resource]:
        """Discover Lambda functions, optionally filtering out deleted ones.

        Uses CloudWatch list_metrics for discovery. Only when filter_deleted
        is set, validates against the Lambda API to remove deleted functions.
        """
        # Get all resources with metrics (including deleted ones)
        resources = super().discover_resources()
        if not resources or not self._filter_deleted:
            return resources

        # Separate Lambda@Edge (us-east-1.* prefix) from regular functions
        lambda_edge = [res for res in resources if _is_lambda_edge(res.id)]
        regular = [res for res in resources if not _is_lambda_edge(res.id)]

        # Filter regular functions against current region (only if any exist)
        kept: list[Resource] = []
        if regular:
            kept = self._filter_to_existing(
                regular, self._client.list_lambda_functions, "list_functions", "functions"
            )

        # Filter Lambda@Edge against us-east-1 (where they are always created)
        if lambda_edge:
            kept += self._filter_to_existing(
                lambda_edge,
                self._client.list_lambda_edge_functions,
                "list_lambda_edge",
                "Lambda@Edge functions",
                resource_key=lambda res: res.id.removeprefix("us-east-1."),
            )
        return kept


class LambdaInsightsSection(CloudWatchSection):
    """Lambda Insights enhanced metrics.

    Requires Lambda Insights extension to be enabled on functions.
    Uses the LambdaInsights namespace for enhanced performance metrics.
    """

    @property
    def name(self) -> str:
        return "lambda_insights"

    @property
    def title(self) -> str:
        return "Lambda Insights"

    @property
    def namespace(self) -> str:
        return "LambdaInsights"

    @property
    def dimension_key(self) -> str:
        return "function_name"

    @property
    def metrics(self) -> list[MetricDefinition]:
        metrics = [
            # Memory metrics
            MetricDefinition("memory_utilization", "Average", "Percent"),
            MetricDefinition("total_memory", "Average", "Megabytes"),
            MetricDefinition("used_memory_max", "Maximum", "Megabytes"),
            # CPU metrics
            MetricDefinition("cpu_total_time", "Sum", "Milliseconds"),
            # Network metrics
            MetricDefinition("tx_bytes", "Sum", "Bytes"),
            MetricDefinition("rx_bytes", "Sum", "Bytes"),
            # Init/cold start
            MetricDefinition("init_duration", "Average", "Milliseconds"),
            MetricDefinition("cold_starts", "Sum", "Count"),
            # Disk I/O
            MetricDefinition("tmp_used", "Maximum", "Bytes"),
            MetricDefinition("tmp_max", "Maximum", "Bytes"),
        ]
        # Same as LambdaSection: idle functions cost no call per metric
        return [replace(m, skip_idle=True) for m in metrics]
