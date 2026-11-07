#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serverless service sections (Lambda).

This module provides CloudWatch monitoring for Lambda functions.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from botocore.exceptions import BotoCoreError, ClientError

from ..base import CloudWatchSection
from ..errors import ErrorCollector
from ..iam_hints import get_permission_hint
from ..logger import get_logger
from ..types import MetricDefinition, MetricResult, Resource

if TYPE_CHECKING:
    from ..cache import APICounter
    from ..client import CloudWatchClient

logger = get_logger("serverless")

# Time window of ListMetrics RecentlyActive=PT3H
RECENTLY_ACTIVE_SECONDS = 3 * 3600


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
        # (function id, metric name) pairs with data in the past 3 hours;
        # None = unknown, fetch everything
        self._recently_active: set[tuple[str, str]] | None = None

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
        return [
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

    def fetch_all_metrics(
        self, resources: list[Resource], period: int = 300
    ) -> list[MetricResult]:
        """Fetch metrics, skipping functions/metrics without recent data.

        One ListMetrics call (RecentlyActive=PT3H) tells which metrics had data
        in the past 3 hours. All others (idle or deleted functions) are reported
        as 0 without a GetMetricStatistics call - the same value AWS would give.
        """
        self._recently_active = None
        lookback_seconds, _ = self.metric_query_window(period)
        # RecentlyActive only covers 3 hours; a longer lookback could miss real data
        if resources and lookback_seconds <= RECENTLY_ACTIVE_SECONDS:
            try:
                response = self._client.list_metrics(self.namespace, recently_active=True)
                self._api_counter.increment(
                    response.get("PageCount", 1), service=self.name, api_type="list_metrics"
                )
                active: set[tuple[str, str]] = set()
                for metric_info in response.get("Metrics", []):
                    resource = self._extract_resource(metric_info)
                    if resource:
                        active.add((resource.id, metric_info["MetricName"]))
                self._recently_active = active
                logger.debug(
                    "[%s] %d metric/function pairs active in the past 3 hours",
                    self.name,
                    len(active),
                )
            except (BotoCoreError, ClientError) as err:
                hint = get_permission_hint(err, "list_metrics")
                if self._error_collector:
                    self._error_collector.add(
                        category="metrics",
                        service=self.name,
                        region=self._client.region,
                        message=(
                            "Could not list recently active metrics, fetching all "
                            f"(more API calls): {err}"
                        ),
                        hint=hint,
                    )
                logger.warning(
                    "[%s] Could not list recently active metrics, fetching all: %s",
                    self.name,
                    err,
                )
        return super().fetch_all_metrics(resources, period)

    def fetch_metric(
        self,
        resource: Resource,
        metric: MetricDefinition,
        start_time: datetime,
        end_time: datetime,
        period: int,
    ) -> MetricResult | None:
        """Return 0 without an API call when the metric had no recent data."""
        if (
            self._recently_active is not None
            and (resource.id, metric.name) not in self._recently_active
        ):
            logger.debug(
                "[%s] Skipping %s for %s: no data in the past 3 hours",
                self.name,
                metric.name,
                resource.id,
            )
            return MetricResult(
                resource_id=resource.id,
                metric_name=metric.name,
                value=0,
                unit=metric.unit,
                stat=metric.stat,
                timestamp=None,
                period=period,
                region=self._client.region,
            )
        return super().fetch_metric(resource, metric, start_time, end_time, period)


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
