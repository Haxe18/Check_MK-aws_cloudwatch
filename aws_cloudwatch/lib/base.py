#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Base classes for CloudWatch sections.

This module defines the abstract base class that all CloudWatch
service sections must implement.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from botocore.exceptions import BotoCoreError, ClientError

from .errors import ErrorCollector
from .iam_hints import get_permission_hint
from .logger import get_logger
from .types import MetricDefinition, MetricResult, Resource

if TYPE_CHECKING:
    from .cache import APICounter
    from .client import CloudWatchClient

logger = get_logger("base")

# Time window of ListMetrics RecentlyActive=PT3H
RECENTLY_ACTIVE_SECONDS = 3 * 3600


class CloudWatchSection(ABC):
    """Abstract base class for AWS CloudWatch metric sections.

    Each service (EC2, RDS, Lambda, etc.) implements this class
    to define how resources are discovered and metrics are fetched.
    """

    def __init__(
        self,
        client: "CloudWatchClient",
        api_counter: "APICounter",
        error_collector: ErrorCollector | None = None,
    ) -> None:
        """Initialize the section.

        Args:
            client: CloudWatch client for API calls
            api_counter: Counter for tracking API usage
            error_collector: Optional collector for surfacing errors into Checkmk output
        """
        self._client = client
        self._api_counter = api_counter
        self._error_collector = error_collector
        # (resource id, metric name, extra-dimension value or "") with data in the past
        # 3 hours, for skip_idle metrics; None = unknown, fetch everything
        self._active_combos: set[tuple[str, str, str]] | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Service identifier (e.g., 'ec2', 'rds').

        This is used as the service key in the output.
        """

    @property
    @abstractmethod
    def title(self) -> str:
        """Human-readable service name (e.g., 'EC2', 'Application Load Balancer (ALB)')."""

    @property
    @abstractmethod
    def namespace(self) -> str:
        """CloudWatch namespace (e.g., 'AWS/EC2')."""

    @property
    @abstractmethod
    def dimension_key(self) -> str:
        """Primary dimension for resource identification.

        E.g., 'InstanceId' for EC2, 'DBInstanceIdentifier' for RDS.
        """

    @property
    @abstractmethod
    def metrics(self) -> list[MetricDefinition]:
        """List of metrics to fetch for this service."""

    @property
    def region_constraints(self) -> list[str] | None:
        """Regions where this service can be monitored.

        Returns:
            List of allowed region names, or None for all regions.
            E.g., ['us-east-1'] for CloudFront.
        """
        return None

    def can_run_in_region(self, region: str) -> bool:
        """Check if this section can run in the given region.

        Args:
            region: AWS region name

        Returns:
            True if the section can run in this region
        """
        constraints = self.region_constraints
        if constraints is None:
            return True
        return region in constraints

    def discover_resources(self) -> list[Resource]:
        """Discover resources by listing metrics in the namespace.

        This is the default implementation that works for most services.
        Override this method for services with special discovery logic.

        Returns:
            List of discovered resources
        """
        logger.debug("[%s] Discovering resources in namespace %s", self.name, self.namespace)

        response = self._client.list_metrics(self.namespace)
        self._api_counter.increment(
            response.get("PageCount", 1), service=self.name, api_type="list_metrics"
        )

        metrics_list = response.get("Metrics", [])
        logger.debug("[%s] list_metrics returned %d metrics", self.name, len(metrics_list))
        if metrics_list:
            # Show first 3 metrics for debugging
            for count, metrics in enumerate(metrics_list[:3]):
                logger.debug(
                    "[%s] Sample metric %d: %s dims=%s",
                    self.name,
                    count + 1,
                    metrics.get("MetricName"),
                    metrics.get("Dimensions", []),
                )

        resources: dict[str, Resource] = {}
        extra_dimensions = self._extra_dimensions()

        for metric_info in metrics_list:
            resource = self._extract_resource(metric_info)
            if resource:
                metric_name = metric_info["MetricName"]
                if resource.id not in resources:
                    resources[resource.id] = resource
                if metric_name not in resources[resource.id].available_metrics:
                    resources[resource.id].available_metrics.append(metric_name)
                combo = self._extra_dimension_combo(
                    metric_info, extra_dimensions.get(metric_name)
                )
                if combo:
                    combos = resources[resource.id].metric_dimensions.setdefault(
                        metric_name, []
                    )
                    if combo not in combos:
                        combos.append(combo)
            else:
                # Log why extraction failed
                dims = metric_info.get("Dimensions", [])
                dim_names = [d["Name"] for d in dims]
                logger.debug(
                    "[%s] Could not extract resource from metric %s, dims=%s, looking for '%s'",
                    self.name,
                    metric_info.get("MetricName"),
                    dim_names,
                    self.dimension_key,
                )

        logger.debug("[%s] Discovered %d resources", self.name, len(resources))
        for rid, res in list(resources.items())[:3]:
            logger.debug(
                "[%s] Resource '%s' has %d available metrics: %s",
                self.name,
                rid,
                len(res.available_metrics),
                res.available_metrics[:5],
            )

        return list(resources.values())

    def _extract_resource(self, metric_info: dict) -> Resource | None:
        """Extract resource from metric dimensions.

        Default implementation looks for the dimension_key.
        Override for services with complex dimension handling.

        Args:
            metric_info: Metric information from list_metrics

        Returns:
            Resource object or None if not extractable
        """
        dimensions = metric_info.get("Dimensions", [])
        for dim in dimensions:
            if dim["Name"] == self.dimension_key:
                return Resource(
                    id=dim["Value"],
                    dimensions={dim["Name"]: dim["Value"]},
                    available_metrics=[],
                )
        return None

    def _filter_to_existing(
        self,
        resources: list[Resource],
        list_existing: Callable[[], list[str]],
        hint_key: str,
        kind: str,
        resource_key: Callable[[Resource], str] | None = None,
    ) -> list[Resource]:
        """Keep only resources whose key is returned by list_existing.

        On an AWS error the error is collected (with IAM hint) and all resources
        are returned unfiltered.

        Args:
            resources: Resources discovered via ListMetrics
            list_existing: Client call returning the IDs that still exist
            hint_key: Key for get_permission_hint (e.g. "list_ec2")
            kind: Plural noun for log lines (e.g. "EC2 instances")
            resource_key: Maps a resource to the ID compared against list_existing
                (default: resource.id)

        Returns:
            Filtered resources, or all resources if listing failed
        """
        try:
            existing = set(list_existing())
        except (BotoCoreError, ClientError) as err:
            hint = get_permission_hint(err, hint_key)
            if self._error_collector:
                self._error_collector.add(
                    "discovery", self.name, self._client.region, str(err), hint
                )
            hint_msg = f" (Required: {hint})" if hint else ""
            logger.warning(
                "[%s] Failed to list %s for filtering: %s%s. "
                "Returning all discovered resources.",
                self.name,
                kind,
                err,
                hint_msg,
            )
            return resources

        filtered_resources = []
        for resource in resources:
            key = resource_key(resource) if resource_key else resource.id
            if key in existing:
                filtered_resources.append(resource)
            else:
                logger.debug("[%s] Filtering out deleted %s: %s", self.name, kind, resource.id)

        logger.info(
            "[%s] Filtered %d deleted %s (Active: %d, Total: %d)",
            self.name,
            len(resources) - len(filtered_resources),
            kind,
            len(filtered_resources),
            len(resources),
        )
        return filtered_resources

    def metric_query_window(self, default_period: int) -> tuple[int, int]:
        """Return lookback window and query period for metric requests.

        Args:
            default_period: Default period from orchestrator configuration.

        Returns:
            Tuple of (lookback_seconds, period_seconds).
        """
        return default_period, default_period

    def fetch_metric(
        self,
        resource: Resource,
        metric: MetricDefinition,
        start_time: datetime,
        end_time: datetime,
        period: int,
    ) -> MetricResult | None:
        """Fetch a single metric using GetMetricStatistics.

        Args:
            resource: The resource to fetch metrics for
            metric: The metric definition
            start_time: Start of time range
            end_time: End of time range
            period: Granularity in seconds

        Returns:
            MetricResult or None if fetch failed
        """
        dimensions = [
            {"Name": name, "Value": value} for name, value in resource.dimensions.items()
        ]

        logger.debug(
            "[%s] get_metric_statistics(%s, %s, dims=%s, stat=%s)",
            self.name,
            self.namespace,
            metric.name,
            dimensions,
            metric.stat,
        )

        try:
            response = self._client.get_metric_statistics(
                namespace=self.namespace,
                metric_name=metric.name,
                dimensions=dimensions,
                start_time=start_time,
                end_time=end_time,
                period=period,
                statistics=[metric.stat],
            )
            self._api_counter.increment(1, service=self.name, api_type="get_statistics")

            datapoints = response.get("Datapoints", [])
            logger.debug(
                "[%s] Got %d datapoints for %s", self.name, len(datapoints), metric.name
            )

            if datapoints:
                latest = max(datapoints, key=lambda x: x.get("Timestamp", datetime.min))
                return MetricResult(
                    resource_id=resource.id,
                    metric_name=metric.name,
                    value=latest.get(metric.stat, 0),
                    unit=metric.unit,
                    stat=metric.stat,
                    timestamp=latest.get("Timestamp").isoformat()
                    if latest.get("Timestamp")
                    else None,
                    period=period,
                    region=self._client.region,
                )

            # No datapoints in time range - return 0 value
            # This indicates the metric exists but has no recent data
            logger.debug("[%s] No datapoints, returning 0 for %s", self.name, metric.name)
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
        except (BotoCoreError, ClientError) as err:
            # AWS API errors (throttling, access denied, etc.)
            hint = get_permission_hint(err, "get_statistics")
            hint_msg = f" (Required: {hint})" if hint else ""
            logger.warning(
                "[%s] AWS API error fetching %s for %s: %s%s",
                self.name,
                metric.name,
                resource.id,
                err,
                hint_msg,
            )
            if self._error_collector:
                self._error_collector.add(
                    category="metrics",
                    service=self.name,
                    region=self._client.region,
                    message=f"Failed to fetch metric {metric.name} for {resource.id}: {err}",
                    hint=hint,
                )
        except (ValueError, TypeError, KeyError) as err:
            # Data processing errors
            logger.warning(
                "[%s] Data error processing %s for %s: %s",
                self.name,
                metric.name,
                resource.id,
                err,
            )

        return None

    def _fetch_combined_metric(
        self,
        resource: Resource,
        metric: MetricDefinition,
        start_time: datetime,
        end_time: datetime,
        period: int,
    ) -> MetricResult | None:
        """Fetch a metric once per extra-dimension combination and merge the values.

        Returns None when no combination is known or any single fetch failed
        (the error is already collected; a partial sum would be wrong).
        """
        combos = resource.metric_dimensions.get(metric.name, [])
        if not combos:
            logger.debug(
                "[%s] No %s values known for %s on %s, skipping",
                self.name,
                metric.extra_dimension,
                metric.name,
                resource.id,
            )
            return None

        parts: dict[str, float] = {}
        timestamps: list[str] = []
        for combo in combos:
            extra_value = combo[metric.extra_dimension]
            if self._is_idle(resource, metric, extra_value):
                parts.setdefault(extra_value, 0.0)
                continue
            part = Resource(
                id=resource.id,
                dimensions={**resource.dimensions, **combo},
                available_metrics=[metric.name],
            )
            result = self.fetch_metric(part, metric, start_time, end_time, period)
            if result is None:
                return None
            value = float(result.value)
            # The same value can come twice (target group listed under an old and a
            # recreated load balancer): merge instead of overwriting
            if extra_value in parts:
                previous = parts[extra_value]
                value = max(previous, value) if metric.combine == "max" else previous + value
            parts[extra_value] = value
            if result.timestamp:
                timestamps.append(result.timestamp)

        values = parts.values()
        value = max(values) if metric.combine == "max" else sum(values)
        return MetricResult(
            resource_id=resource.id,
            metric_name=metric.name,
            value=value,
            unit=metric.unit,
            stat=metric.stat,
            timestamp=max(timestamps) if timestamps else None,
            period=period,
            region=self._client.region,
            parts=parts,
        )

    def _extra_dimensions(self) -> dict[str, str]:
        """Return metric name -> extra dimension for metrics with extra_dimension."""
        return {m.name: m.extra_dimension for m in self.metrics if m.extra_dimension}

    def _extra_dimension_combo(
        self, metric_info: dict, extra_dimension: str | None
    ) -> dict[str, str] | None:
        """Return the dimensions of a listed metric if they are its extra-dimension pair.

        Only the exact pair counts, e.g. LoadBalancer+TargetGroup without the
        AvailabilityZone variant. The full primary value is kept: ALB/NLB resources
        are keyed by name only, a recreated load balancer has a new LoadBalancer value.

        Args:
            metric_info: Metric information from list_metrics
            extra_dimension: The metric's extra dimension (from _extra_dimensions()),
                None for metrics without one

        Returns:
            {primary dimension: value, extra dimension: value}, or None for metrics
            without extra_dimension or with other dimension sets
        """
        if not extra_dimension:
            return None
        dims = {d["Name"]: d["Value"] for d in metric_info.get("Dimensions", [])}
        if set(dims) != {self.dimension_key, extra_dimension}:
            return None
        return dims

    def _is_idle(
        self, resource: Resource, metric: MetricDefinition, extra_value: str = ""
    ) -> bool:
        """Tell whether a skip_idle metric had no data in the past 3 hours.

        Such a metric counts as 0, as AWS would answer, without a call.

        Args:
            resource: Resource the metric belongs to
            metric: Metric definition
            extra_value: Extra-dimension value, "" for metrics without extra_dimension

        Returns:
            True when the call can be skipped
        """
        if (
            not metric.skip_idle
            or self._active_combos is None
            or (resource.id, metric.name, extra_value) in self._active_combos
        ):
            return False
        logger.debug(
            "[%s] Skipping %s for %s %s: no data in the past 3 hours",
            self.name,
            metric.name,
            resource.id,
            extra_value,
        )
        return True

    def _list_recently_active(self) -> list[dict] | None:
        """List the metrics with data in the past 3 hours (ListMetrics RecentlyActive=PT3H).

        Returns:
            The listed metrics, or None on error (the error is collected with IAM
            hint; the caller then fetches everything)
        """
        try:
            response = self._client.list_metrics(self.namespace, recently_active=True)
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
            return None
        self._api_counter.increment(
            response.get("PageCount", 1), service=self.name, api_type="list_metrics"
        )
        return response.get("Metrics", [])

    def _list_active_combos(self) -> set[tuple[str, str, str]] | None:
        """List the metric combinations with data in the past 3 hours.

        Combinations missing from the result (idle functions or operations, deleted
        target groups) are not fetched.

        Returns:
            Set of (resource id, metric name, extra-dimension value or ""), or None on
            error (then everything is fetched)
        """
        metrics_list = self._list_recently_active()
        if metrics_list is None:
            return None

        extra_dimensions = self._extra_dimensions()
        active: set[tuple[str, str, str]] = set()
        for metric_info in metrics_list:
            resource = self._extract_resource(metric_info)
            if not resource:
                continue
            metric_name = metric_info["MetricName"]
            extra_dimension = extra_dimensions.get(metric_name)
            if not extra_dimension:
                active.add((resource.id, metric_name, ""))
                continue
            combo = self._extra_dimension_combo(metric_info, extra_dimension)
            if combo:
                active.add((resource.id, metric_name, combo[extra_dimension]))
        logger.debug(
            "[%s] %d metric combinations active in the past 3 hours", self.name, len(active)
        )
        return active

    def fetch_all_metrics(
        self, resources: list[Resource], period: int = 300
    ) -> list[MetricResult]:
        """Fetch metrics for given resources without discovery.

        This allows the orchestrator to use cached discovery results
        while fetching fresh metric data.

        Args:
            resources: List of resources to fetch metrics for
            period: Time period/granularity in seconds

        Returns:
            List of metric results
        """
        lookback_seconds, query_period = self.metric_query_window(period)
        end_time = datetime.now(timezone.utc)
        start_time = datetime.fromtimestamp(
            end_time.timestamp() - lookback_seconds, tz=timezone.utc
        )

        logger.debug(
            "[%s] Fetching metrics for %d resources with lookback=%ds, period=%ds",
            self.name,
            len(resources),
            lookback_seconds,
            query_period,
        )

        self._active_combos = None
        # RecentlyActive only covers 3 hours; a longer lookback (S3) could miss real data.
        # Without a skip_idle metric to fetch there is nothing to skip.
        skip_idle = [m for m in self.metrics if m.skip_idle]
        if lookback_seconds <= RECENTLY_ACTIVE_SECONDS and any(
            resource.metric_dimensions.get(m.name)
            if m.extra_dimension
            else m.name in resource.available_metrics
            for resource in resources
            for m in skip_idle
        ):
            self._active_combos = self._list_active_combos()

        results: list[MetricResult] = []
        configured_metric_names = [m.name for m in self.metrics]
        logger.debug("[%s] Configured metrics: %s", self.name, configured_metric_names)

        for resource in resources:
            logger.debug(
                "[%s] Processing resource '%s' with available metrics: %s",
                self.name,
                resource.id,
                resource.available_metrics,
            )

            for metric in self.metrics:
                if metric.name in resource.available_metrics:
                    logger.debug(
                        "[%s] Fetching metric '%s' for resource '%s'",
                        self.name,
                        metric.name,
                        resource.id,
                    )
                    if metric.extra_dimension:
                        result = self._fetch_combined_metric(
                            resource, metric, start_time, end_time, query_period
                        )
                    elif self._is_idle(resource, metric):
                        result = MetricResult(
                            resource_id=resource.id,
                            metric_name=metric.name,
                            value=0,
                            unit=metric.unit,
                            stat=metric.stat,
                            timestamp=None,
                            period=query_period,
                            region=self._client.region,
                        )
                    else:
                        result = self.fetch_metric(
                            resource,
                            metric,
                            start_time,
                            end_time,
                            query_period,
                        )
                    if result:
                        results.append(result)
                        logger.debug(
                            "[%s] Got result: %s=%s",
                            self.name,
                            metric.name,
                            result.value,
                        )
                else:
                    logger.debug(
                        "[%s] Metric '%s' not in available metrics for resource '%s'",
                        self.name,
                        metric.name,
                        resource.id,
                    )

        return results
