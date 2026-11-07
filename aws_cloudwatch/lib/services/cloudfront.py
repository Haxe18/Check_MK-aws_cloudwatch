#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CloudFront service sections.

This module provides CloudWatch monitoring for:
- CloudFront distributions
- CloudFront Functions
"""

from typing import TYPE_CHECKING

from botocore.exceptions import BotoCoreError, ClientError

from ..base import CloudWatchSection
from ..errors import ErrorCollector
from ..iam_hints import get_permission_hint
from ..logger import get_logger
from ..types import MetricDefinition, Resource

if TYPE_CHECKING:
    from ..cache import APICounter
    from ..client import CloudWatchClient

logger = get_logger("cloudfront")


class CloudFrontSection(CloudWatchSection):
    """CloudFront distribution metrics.

    CloudFront metrics are only available in us-east-1 and require
    the Region="Global" dimension.
    """

    def __init__(
        self,
        client: "CloudWatchClient",
        api_counter: "APICounter",
        error_collector: ErrorCollector | None = None,
        fetch_metadata: bool = False,
    ) -> None:
        """Initialize the section.

        Args:
            client: CloudWatch client for API calls
            api_counter: Counter for tracking API usage
            error_collector: Optional collector for surfacing errors into Checkmk output
            fetch_metadata: Fetch comment/domain/aliases via ListDistributions. Off by
                default: the response also carries origin custom headers in clear text.
        """
        super().__init__(client, api_counter, error_collector)
        self._fetch_metadata = fetch_metadata

    @property
    def name(self) -> str:
        return "cloudfront"

    @property
    def title(self) -> str:
        return "CloudFront"

    @property
    def namespace(self) -> str:
        return "AWS/CloudFront"

    @property
    def dimension_key(self) -> str:
        return "DistributionId"

    @property
    def region_constraints(self) -> list[str]:
        return ["us-east-1"]

    @property
    def metrics(self) -> list[MetricDefinition]:
        return [
            MetricDefinition("Requests", "Sum", "None"),
            MetricDefinition("BytesDownloaded", "Sum", "Bytes"),
            MetricDefinition("BytesUploaded", "Sum", "Bytes"),
            MetricDefinition("TotalErrorRate", "Average", "Percent"),
            MetricDefinition("4xxErrorRate", "Average", "Percent"),
            MetricDefinition("5xxErrorRate", "Average", "Percent"),
            MetricDefinition("CacheHitRate", "Average", "Percent"),
            MetricDefinition("OriginLatency", "Average", "Milliseconds"),
        ]

    def discover_resources(self) -> list[Resource]:
        """Discover CloudFront distributions, optionally enriched with metadata."""
        resources = super().discover_resources()
        if not resources or not self._fetch_metadata:
            return resources

        try:
            distributions = self._client.list_cloudfront_distributions()
            dist_map = {d["Id"]: d for d in distributions}
            for resource in resources:
                dist = dist_map.get(resource.id)
                if dist:
                    resource.metadata = {
                        "comment": dist.get("Comment", ""),
                        "domain_name": dist.get("DomainName", ""),
                        "aliases": dist.get("Aliases", {}).get("Items", []),
                    }
        except (BotoCoreError, ClientError) as err:
            hint = get_permission_hint(err, "list_cloudfront_distributions")
            self._error_collector.add(
                category="discovery",
                service="cloudfront",
                region=self._client.region,
                message=f"Failed to list distributions for metadata (URL/alias will not be shown): {err}",
                hint=hint,
            )
            logger.warning("[cloudfront] Failed to list distributions for metadata: %s", err)

        return resources

    def _extract_resource(self, metric_info: dict) -> Resource | None:
        """Extract CloudFront distribution from metric dimensions.

        Skip CloudFront Functions metrics (those start with "Function").
        """
        metric_name = metric_info.get("MetricName", "")
        if metric_name.startswith("Function"):
            return None

        dimensions = metric_info.get("Dimensions", [])
        for dim in dimensions:
            if dim["Name"] == "DistributionId":
                return Resource(
                    id=dim["Value"],
                    dimensions={
                        "DistributionId": dim["Value"],
                        "Region": "Global",
                    },
                    available_metrics=[],
                )
        return None


class CloudFrontFunctionsSection(CloudWatchSection):
    """CloudFront Functions metrics.

    CloudFront Functions have complex dimension handling with
    DistributionId and FunctionName combinations.
    """

    @property
    def name(self) -> str:
        return "cloudfront_functions"

    @property
    def title(self) -> str:
        return "CloudFront Functions"

    @property
    def namespace(self) -> str:
        return "AWS/CloudFront"

    @property
    def dimension_key(self) -> str:
        return "FunctionName"

    @property
    def region_constraints(self) -> list[str]:
        return ["us-east-1"]

    @property
    def metrics(self) -> list[MetricDefinition]:
        return [
            MetricDefinition("FunctionInvocations", "Sum", "Count"),
            MetricDefinition("FunctionComputeUtilization", "Average", "Percent"),
            MetricDefinition("FunctionExecutionErrors", "Sum", "Count"),
            MetricDefinition("FunctionValidationErrors", "Sum", "Count"),
        ]

    def discover_resources(self) -> list[Resource]:
        """Discover CloudFront Functions and filter out deleted ones."""
        resources = super().discover_resources()
        if not resources:
            return resources

        # resource.id is always the plain function name
        return self._filter_to_existing(
            resources,
            self._client.list_cloudfront_functions,
            "list_cloudfront_functions",
            "CloudFront Functions",
        )

    def _extract_resource(self, metric_info: dict) -> Resource | None:
        """Extract CloudFront Function from metric dimensions.

        Only process metrics starting with "Function".
        Uses plain function name as ID to avoid duplicates across distributions.
        """
        metric_name = metric_info.get("MetricName", "")
        if not metric_name.startswith("Function"):
            return None

        dimensions = metric_info.get("Dimensions", [])
        func_name = None
        func_region = None

        for dim in dimensions:
            if dim["Name"] == "FunctionName":
                func_name = dim["Value"]
            elif dim["Name"] == "Region":
                func_region = dim["Value"]

        if not func_name:
            return None

        # Always use plain function name as ID to avoid duplicates.
        # CloudWatch reports metrics both with and without DistributionId dimension,
        # which would create duplicate resources for the same function.
        resource_id = func_name

        dims = {"FunctionName": func_name}
        if func_region:
            dims["Region"] = func_region

        return Resource(
            id=resource_id,
            dimensions=dims,
            available_metrics=[],
        )
