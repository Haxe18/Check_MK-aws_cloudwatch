#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serverless service sections (Lambda).

This module provides CloudWatch monitoring for Lambda functions.
"""

from botocore.exceptions import BotoCoreError, ClientError

from ..base import CloudWatchSection
from ..iam_hints import get_permission_hint
from ..logger import get_logger
from ..types import MetricDefinition, Resource

logger = get_logger("serverless")


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
        """Discover Lambda functions and filter out deleted ones.

        Uses CloudWatch list_metrics for initial discovery, then
        validates against Lambda API to remove deleted functions.
        """
        # Get all resources with metrics (including deleted ones)
        resources = super().discover_resources()
        if not resources:
            return resources

        try:
            # Separate Lambda@Edge (us-east-1.* prefix) from regular functions
            lambda_edge = [res for res in resources if _is_lambda_edge(res.id)]
            regular = [res for res in resources if not _is_lambda_edge(res.id)]

            # Filter regular functions against current region (only if any exist)
            filtered_resources = []
            if regular:
                active_functions = set(self._client.list_lambda_functions())
                filtered_resources = [res for res in regular if res.id in active_functions]
                for res in regular:
                    if res.id not in active_functions:
                        logger.debug(
                            "[%s] Filtering out deleted function: %s", self.name, res.id
                        )

            # Filter Lambda@Edge against us-east-1 (where they are always created)
            if lambda_edge:
                try:
                    active_edge = set(self._client.list_lambda_edge_functions())
                    for resource in lambda_edge:
                        base_name = resource.id[len("us-east-1.") :]
                        if base_name in active_edge:
                            filtered_resources.append(resource)
                        else:
                            logger.debug(
                                "[%s] Filtering out deleted Lambda@Edge: %s",
                                self.name,
                                resource.id,
                            )
                except (BotoCoreError, ClientError) as err:
                    hint = get_permission_hint(err, "list_lambda_edge")
                    if self._error_collector:
                        self._error_collector.add(
                            "discovery", self.name, self._client.region, str(err), hint
                        )
                    hint_msg = f" (Required: {hint})" if hint else ""
                    logger.warning(
                        "[%s] Failed to list Lambda@Edge functions: %s%s. Keeping all.",
                        self.name,
                        err,
                        hint_msg,
                    )
                    filtered_resources.extend(lambda_edge)

            logger.info(
                "[%s] Filtered %d deleted functions (Active: %d, Total: %d)",
                self.name,
                len(resources) - len(filtered_resources),
                len(filtered_resources),
                len(resources),
            )
            return filtered_resources

        except (BotoCoreError, ClientError) as err:
            hint = get_permission_hint(err, "list_functions")
            if self._error_collector:
                self._error_collector.add(
                    "discovery", self.name, self._client.region, str(err), hint
                )
            hint_msg = f" (Required: {hint})" if hint else ""
            logger.warning(
                "[%s] Failed to list lambda functions for filtering: %s%s. "
                "Returning all discovered metrics.",
                self.name,
                err,
                hint_msg,
            )
            return resources


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
        return [
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
            MetricDefinition("tmp_used", "Maximum", "Megabytes"),
            MetricDefinition("tmp_max", "Maximum", "Megabytes"),
        ]
