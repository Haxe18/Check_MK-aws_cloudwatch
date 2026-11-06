#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CloudWatch orchestrator for coordinating service sections.

This module provides the main coordinator that runs all configured
CloudWatch sections across multiple regions.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError
from cmk.utils.paths import var_dir

from .cache import APICounter, DataCache
from .client import CloudWatchClient, FreeTierClient
from .errors import ErrorCollector
from .iam_hints import get_permission_hint
from .logger import get_logger

# Import all service sections
from .services import SECTION_REGISTRY
from .threshold_types import CLOUDWATCH_FREE_TIER_LIMIT
from .types import Resource

logger = get_logger("orchestrator")

# Service-specific metrics cache TTL overrides (seconds)
SERVICE_METRICS_TTL_OVERRIDES: dict[str, int] = {
    "s3": 24 * 3600,
}


@dataclass
class ServiceTask:
    """One region/service pair to process, with its own API counter and error collector.

    The orchestrator merges the counter and collector into the global ones
    after all tasks finished, in config order.
    """

    region: str
    service_name: str
    client: CloudWatchClient
    cache_dir: Path
    config_key: str
    api_counter: APICounter = field(default_factory=APICounter)
    error_collector: ErrorCollector = field(default_factory=ErrorCollector)
    phase: str = "discovery"


class CloudWatchOrchestrator:
    """Coordinates running all CloudWatch sections across regions.

    This is the main entry point for the CloudWatch agent. It:
    - Creates region-specific clients and caches
    - Runs configured sections for each region
    - Aggregates results and API counters
    - Fetches AWS Free Tier usage data
    """

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        cache_ttl: int = 300,
        discovery_ttl: int = 3600,
        api_warn: int = 80,
        api_crit: int = 90,
        force_over_limit: bool = False,
        force_refresh: bool = False,
        max_workers: int = 1,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            access_key: AWS Access Key ID
            secret_key: AWS Secret Access Key
            cache_ttl: Cache time-to-live for metrics in seconds (must be multiple of 60)
            discovery_ttl: Cache time-to-live for resource discovery in seconds (must be >= cache_ttl)
            api_warn: Warning threshold for API usage percentage (integer 0-100)
            api_crit: Critical threshold for API usage percentage (integer 0-100)
            force_over_limit: Continue monitoring even when free tier limit is exceeded
            force_refresh: Ignore all caches and fetch fresh data from AWS API
            max_workers: Maximum number of parallel threads (1 = sequential; the agent
                passes min(4, 2 x CPUs) when nothing is configured)
        """
        # Store credentials for passing to clients (not as instance variables for security)
        # These are only used to create boto3 clients, not stored longer than necessary
        self.__credentials = (access_key, secret_key)
        # AWS CloudWatch API requires Period to be a multiple of 60 seconds
        # Round up to ensure we don't go below the requested TTL
        self._cache_ttl = ((cache_ttl + 59) // 60) * 60 if cache_ttl > 0 else 300
        self._discovery_ttl = ((discovery_ttl + 59) // 60) * 60 if discovery_ttl > 0 else 3600

        # Ensure discovery_ttl >= cache_ttl (logical constraint)
        if self._discovery_ttl < self._cache_ttl:
            logger.warning(
                "discovery_ttl (%d) < cache_ttl (%d), setting discovery_ttl = cache_ttl",
                self._discovery_ttl,
                self._cache_ttl,
            )
            self._discovery_ttl = self._cache_ttl

        self._api_warn = max(0, min(100, int(api_warn)))
        self._api_crit = max(0, min(100, int(api_crit)))
        self._force_over_limit = force_over_limit
        self._force_refresh = force_refresh

        self._max_workers = max(1, int(max_workers))
        self._api_counter = APICounter()
        self._error_collector = ErrorCollector()

    def _get_cache_dir(self, region: str) -> Path:
        """Get the cache directory for a region.

        Uses a hash of the access key to identify the profile without
        exposing any part of the credential in the filesystem.

        Args:
            region: AWS region name

        Returns:
            Path to the cache directory
        """
        # Use hash of access key to avoid exposing credentials in filesystem
        access_key = self.__credentials[0]
        profile_hash = CloudWatchClient.get_profile_hash(access_key)
        return Path(var_dir) / "agent_aws_cloudwatch" / f"{profile_hash}_{region}"

    def _load_known_resources(
        self, regions_services_map: dict[str, list[str]]
    ) -> dict[str, list[str]]:
        """Read the resource IDs from the last metrics cache files, regardless of age.

        Used while monitoring is stopped: no API calls are made, but the check
        plugins still need the known items, otherwise the service discovery
        sees all services as vanished.

        Args:
            regions_services_map: Dict mapping region names to service lists

        Returns:
            Dict mapping "region:service" to regionalized resource IDs ("region:id")
        """
        known_resources: dict[str, list[str]] = {}
        for region, services in regions_services_map.items():
            cache_dir = self._get_cache_dir(region)
            for service_name in services:
                metrics_cache = DataCache(
                    cache_dir=cache_dir,
                    ttl=self._cache_ttl,
                    prefix=f"metrics_{service_name}_",
                )
                cached_metrics = metrics_cache.load(service_name, ignore_ttl=True)
                if not cached_metrics or not isinstance(cached_metrics.get("metrics"), list):
                    continue
                resource_ids: list[str] = []
                for metric in cached_metrics["metrics"]:
                    resource_id = metric.get("resource_id") if isinstance(metric, dict) else None
                    if not isinstance(resource_id, str) or not resource_id:
                        continue
                    regionalized_id = f"{region}:{resource_id}"
                    if regionalized_id not in resource_ids:
                        resource_ids.append(regionalized_id)
                if resource_ids:
                    known_resources[f"{region}:{service_name}"] = resource_ids
        return known_resources

    def _fetch_aws_usage(self) -> tuple[int, int]:
        """Fetch CloudWatch API usage from AWS Free Tier API.

        Returns:
            Tuple of (actual_usage, forecasted_usage)
        """
        access_key, secret_key = self.__credentials
        try:
            client = FreeTierClient(access_key, secret_key)
            return client.get_cloudwatch_usage()
        except (BotoCoreError, ClientError) as err:
            logger.warning("Could not fetch Free Tier data: %s", err)
            hint = get_permission_hint(err, "free_tier")
            if self._error_collector:
                self._error_collector.add(
                    "free_tier",
                    "api_counter",
                    "global",
                    f"Free Tier API unavailable: {err}. Limit protection inactive.",
                    hint,
                )
            return 0, 0

    def _process_service(self, task: ServiceTask) -> dict[str, Any] | None:
        """Process a single service for a region.

        API calls and errors go to the task's own counter and collector. The
        caller merges them into the global ones in a fixed order. Tasks of the
        same region share the client (its lazy client creation is locked) and
        the cache directory (each service writes its own cache files).

        Args:
            task: Service task with region, client, cache settings and local trackers

        Returns:
            Result dict or None if service should be skipped (unknown or region constraint)
        """
        service_name = task.service_name
        region = task.region

        section_class = SECTION_REGISTRY.get(service_name)
        if not section_class:
            logger.warning("Unknown service '%s', skipping", service_name)
            return None

        logger.debug(
            "Creating section for service '%s' (%s)",
            service_name,
            section_class.__name__,
        )

        section = section_class(task.client, task.api_counter, task.error_collector)

        if not section.can_run_in_region(region):
            logger.warning("%s cannot run in %s, skipping", service_name, region)
            return None

        service_metrics_ttl = SERVICE_METRICS_TTL_OVERRIDES.get(service_name, self._cache_ttl)
        service_region_requests = 0

        discovery_cache = DataCache(
            cache_dir=task.cache_dir,
            ttl=self._discovery_ttl,
            prefix="discovery_",
        )

        # ========== PHASE 1: DISCOVERY (Long TTL Cache) ==========
        task.phase = "discovery"
        discovery_key = service_name
        resources: list[Resource] | None = None

        if self._force_refresh:
            cached_discovery = None
            logger.debug("Force refresh: skipping discovery cache for '%s'", service_name)
        else:
            cached_discovery = discovery_cache.load(discovery_key, config_key=task.config_key)

        if cached_discovery and "resources" in cached_discovery:
            logger.debug(
                "Using cached discovery for '%s' (%d resources)",
                service_name,
                len(cached_discovery["resources"]),
            )
            try:
                resources = [Resource.from_dict(r) for r in cached_discovery["resources"]]
            except (KeyError, TypeError) as err:
                logger.warning(
                    "Corrupted discovery cache for %s: %s, deleting and fetching fresh",
                    service_name,
                    err,
                )
                discovery_cache.delete(discovery_key)
                resources = None

            if resources is not None:
                # Re-add errors that occurred during the original discovery run
                task.error_collector.merge_from_list(cached_discovery.get("discovery_errors", []))

        if resources is None:
            logger.debug("Fetching fresh discovery for '%s'", service_name)
            calls_before = task.api_counter.get_count()
            try:
                resources = section.discover_resources()
                service_region_requests += task.api_counter.get_count() - calls_before

                # The collector holds only discovery errors at this point
                discovery_errors = task.error_collector.to_list()

                discovery_cache.save(
                    discovery_key,
                    {
                        "resources": [r.to_dict() for r in resources],
                        "timestamp": int(time.time()),
                        "discovery_errors": discovery_errors,
                    },
                    config_key=task.config_key,
                )
                logger.debug(
                    "Discovered %d resources for '%s'",
                    len(resources),
                    service_name,
                )
            except (BotoCoreError, ClientError) as err:
                # Count calls made before the failure (same as in _run_service_task)
                service_region_requests += task.api_counter.get_count() - calls_before
                hint = get_permission_hint(err, "list_metrics")
                task.error_collector.add("discovery", service_name, region, str(err), hint)
                logger.error(
                    "Discovery failed for %s in %s: %s",
                    service_name,
                    region,
                    err,
                    exc_info=True,
                )
                resources = []

        # Collect resource metadata (e.g., CloudFront comment/URL)
        service_metadata: dict[str, Any] = {}
        if resources:
            service_metadata = {r.id: r.metadata for r in resources if r.metadata}

        # ========== PHASE 2: METRICS (Short TTL Cache) ==========
        task.phase = "metrics"
        metrics_cache = DataCache(
            cache_dir=task.cache_dir,
            ttl=service_metrics_ttl,
            prefix=f"metrics_{service_name}_",
        )
        metrics_key = service_name

        if self._force_refresh:
            cached_metrics = None
            logger.debug("Force refresh: skipping metrics cache for '%s'", service_name)
        else:
            cached_metrics = metrics_cache.load(metrics_key, config_key=task.config_key)

        refresh_api_calls = 0.0

        if cached_metrics and "metrics" in cached_metrics:
            metrics_data = cached_metrics["metrics"]
            cached_api_calls = cached_metrics.get("api_calls", 0)
            refresh_api_calls = float(cached_api_calls)
            service_region_requests += cached_api_calls
            logger.debug(
                "Using cached metrics for '%s' (%d metrics, %d cached API calls)",
                service_name,
                len(metrics_data),
                cached_api_calls,
            )
        else:
            logger.debug(
                "Fetching fresh metrics for '%s' (%d resources)",
                service_name,
                len(resources),
            )
            calls_before = task.api_counter.get_count()
            try:
                results = section.fetch_all_metrics(
                    resources,
                    period=service_metrics_ttl,
                )
                api_calls = task.api_counter.get_count() - calls_before
                refresh_api_calls = float(api_calls)
                service_region_requests += api_calls

                metrics_data = [m.to_dict() for m in results]
                metrics_cache.save(
                    metrics_key,
                    {
                        "metrics": metrics_data,
                        "api_calls": api_calls,
                        "timestamp": int(time.time()),
                    },
                    config_key=task.config_key,
                )
                logger.debug(
                    "Got %d metrics, %d API calls for '%s'",
                    len(metrics_data),
                    api_calls,
                    service_name,
                )
            except (BotoCoreError, ClientError) as err:
                # Count calls made before the failure (same as in _run_service_task)
                service_region_requests += task.api_counter.get_count() - calls_before
                hint = get_permission_hint(err, "get_statistics")
                task.error_collector.add("metrics", service_name, region, str(err), hint)
                logger.error(
                    "Failed to fetch metrics for %s in %s: %s",
                    service_name,
                    region,
                    err,
                    exc_info=True,
                )
                metrics_data = []
                refresh_api_calls = 0.0

        # Regionalize resource IDs
        regionalized_metrics = []
        for metric in metrics_data:
            metric_copy = metric.copy()
            original_id = metric_copy.get("resource_id", "unknown")
            metric_copy["resource_id"] = f"{region}:{original_id}"
            metric_copy["region"] = region
            regionalized_metrics.append(metric_copy)

        logger.debug(
            "Added %d metrics for '%s:%s'",
            len(regionalized_metrics),
            region,
            service_name,
        )

        return {
            "service_name": service_name,
            "combined_key": f"{region}:{service_name}",
            "regionalized_metrics": regionalized_metrics,
            "service_metadata": service_metadata,
            "region_requests": service_region_requests,
            "refresh_api_calls": refresh_api_calls,
            "service_metrics_ttl": service_metrics_ttl,
            "is_empty": not resources,
            "section_title": section.title,
        }

    def _run_service_task(self, task: ServiceTask) -> dict[str, Any] | None:
        """Run one service task and turn unexpected errors into collected errors.

        Unexpected errors are filed under the phase that failed ("discovery"
        or "metrics"). API calls made before the failure stay in the task's
        counter; the caller adds them to the region and service totals.

        Args:
            task: Service task to run

        Returns:
            Result dict from _process_service, or None if skipped or failed
        """
        # Name the thread after the task, so debug log lines show region and service
        thread = threading.current_thread()
        original_name = thread.name
        thread.name = f"{task.region}:{task.service_name}"
        try:
            return self._process_service(task)
        except Exception as err:
            logger.error(
                "Unexpected error processing %s in %s: %s",
                task.service_name,
                task.region,
                err,
                exc_info=True,
            )
            task.error_collector.add(
                task.phase,
                task.service_name,
                task.region,
                f"Unexpected error: {type(err).__name__}: {err}",
            )
            return None
        finally:
            thread.name = original_name

    def run(self, regions_services_map: dict[str, list[str]]) -> dict[str, Any]:
        """Run all configured sections and return combined output.

        Args:
            regions_services_map: Dict mapping region names to service lists
                Example: {"us-east-1": ["cloudfront", "ec2"], "eu-central-1": ["rds"]}

        Returns:
            Combined output dictionary with metrics and API counter
        """
        logger.debug("Starting run with regions_services_map=%s", regions_services_map)
        logger.debug("Available services in registry: %s", list(SECTION_REGISTRY.keys()))

        # Fetch AWS Free Tier usage FIRST to check if limit is reached
        aws_usage, aws_forecast = self._fetch_aws_usage()
        limit_reached = aws_usage >= CLOUDWATCH_FREE_TIER_LIMIT

        # If limit reached and force is not enabled, stop monitoring
        if limit_reached and not self._force_over_limit:
            logger.warning(
                "Free tier limit reached (%s >= %s). "
                "Monitoring stopped to avoid AWS costs. Enable 'Force continue' to override.",
                f"{aws_usage:,}",
                f"{CLOUDWATCH_FREE_TIER_LIMIT:,}",
            )
            return {
                "CloudWatchMetrics": {},
                "CloudWatchKnownResources": self._load_known_resources(regions_services_map),
                "CloudWatchAPICounter": {
                    "requests_made": 0,
                    "requests_by_region": {},
                    "aws_monthly_total": aws_usage,
                    "aws_forecast_total": aws_forecast,
                    "free_tier_limit": CLOUDWATCH_FREE_TIER_LIMIT,
                    "percentage_used": (aws_usage / CLOUDWATCH_FREE_TIER_LIMIT) * 100
                    if CLOUDWATCH_FREE_TIER_LIMIT
                    else 0,
                    "forecast_percentage": (aws_forecast / CLOUDWATCH_FREE_TIER_LIMIT) * 100
                    if CLOUDWATCH_FREE_TIER_LIMIT
                    else 0,
                    "limit_reached": True,
                    "monitoring_stopped": True,
                },
                "CloudWatchAPIConfig": {
                    "services_count": 0,
                    "calls_per_check": 0,
                    "cache_ttl": self._cache_ttl,
                    "discovery_ttl": self._discovery_ttl,
                    "service_metrics_ttl_overrides": SERVICE_METRICS_TTL_OVERRIDES,
                    "weighted_calls_per_check_by_service": {},
                    "weighted_calls_per_check_overridden_total": 0.0,
                    "weighted_calls_per_check_default_total": 0.0,
                    "weighted_calls_per_check_overridden_by_service": {},
                    "weighted_calls_per_check_default_by_service": {},
                    "checks_per_month": 0,
                    "warning_threshold": self._api_warn,
                    "critical_threshold": self._api_crit,
                    "force_over_limit": self._force_over_limit,
                },
            }

        combined_metrics: dict[str, list[dict[str, Any]]] = {}
        requests_by_region: dict[str, int] = {}
        empty_services: dict[str, list[str]] = {}
        resource_metadata: dict[str, dict[str, Any]] = {}
        total_services_count = 0
        estimated_calls_per_check = 0.0
        weighted_calls_per_check_by_service: dict[str, dict[str, float]] = {}
        weighted_calls_per_check_overridden_total = 0.0
        weighted_calls_per_check_default_total = 0.0
        weighted_calls_per_check_overridden_by_service: dict[str, float] = {}
        weighted_calls_per_check_default_by_service: dict[str, float] = {}

        access_key, secret_key = self.__credentials

        # Build one task per region/service pair. Clients are created up front
        # (sequentially), so a single pool can run all pairs with max_workers threads.
        # Each plan holds either the region's tasks or the (message, hint) of its client error.
        region_plans: list[tuple[str, list[ServiceTask], tuple[str, str | None] | None]] = []
        for region, services in regions_services_map.items():
            logger.debug("Processing region '%s' with services %s", region, services)
            try:
                client = CloudWatchClient(
                    access_key=access_key,
                    secret_key=secret_key,
                    region=region,
                )
            except (BotoCoreError, ClientError) as err:
                hint = get_permission_hint(err, "create_client")
                logger.error("Failed to create client for region %s: %s", region, err)
                region_plans.append((region, [], (str(err), hint)))
                continue

            config_key = ",".join(sorted(services))
            cache_dir = self._get_cache_dir(region)
            logger.debug("Cache dir: %s", cache_dir)
            logger.debug(
                "Discovery TTL: %ds, Default Metrics TTL: %ds",
                self._discovery_ttl,
                self._cache_ttl,
            )
            region_tasks = [
                ServiceTask(
                    region=region,
                    service_name=service_name,
                    client=client,
                    cache_dir=cache_dir,
                    config_key=config_key,
                )
                for service_name in services
            ]
            region_plans.append((region, region_tasks, None))

        all_tasks = [task for _, region_tasks, _ in region_plans for task in region_tasks]
        if self._max_workers > 1 and len(all_tasks) > 1:
            with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                all_results = list(executor.map(self._run_service_task, all_tasks))
        else:
            all_results = [self._run_service_task(task) for task in all_tasks]
        # all_results is in the same order as all_tasks, i.e. config order
        results_in_order = iter(all_results)

        # Aggregate in config order, so errors and lists come out the same on every run
        for region, region_tasks, client_error in region_plans:
            if client_error is not None:
                message, hint = client_error
                self._error_collector.add("api", "client", region, message, hint)
                continue

            requests_by_region[region] = 0
            for task in region_tasks:
                self._api_counter.add_counts(
                    task.api_counter.get_count(), task.api_counter.get_breakdown()
                )
                self._error_collector.merge_from_list(task.error_collector.to_list())

                service_result = next(results_in_order)
                if service_result is None:
                    # Skipped (0 calls) or failed: count the calls made before the failure
                    requests_by_region[region] += task.api_counter.get_count()
                    continue

                total_services_count += 1
                requests_by_region[region] += service_result["region_requests"]

                combined_key = service_result["combined_key"]
                combined_metrics[combined_key] = service_result["regionalized_metrics"]

                if service_result["service_metadata"]:
                    resource_metadata[combined_key] = service_result["service_metadata"]

                if service_result["is_empty"]:
                    if region not in empty_services:
                        empty_services[region] = []
                    empty_services[region].append(service_result["section_title"])

                # Weighted API calls calculation
                service_name = service_result["service_name"]
                service_metrics_ttl = service_result["service_metrics_ttl"]
                refresh_api_calls = service_result["refresh_api_calls"]

                refresh_ratio = (
                    self._cache_ttl / service_metrics_ttl if service_metrics_ttl > 0 else 1.0
                )
                refresh_ratio = max(0.0, min(1.0, refresh_ratio))
                weighted_calls = refresh_api_calls * refresh_ratio
                estimated_calls_per_check += weighted_calls

                service_breakdown = weighted_calls_per_check_by_service.get(
                    service_name,
                    {
                        "refresh_ttl": float(service_metrics_ttl),
                        "refresh_ratio": refresh_ratio,
                        "last_refresh_api_calls": 0.0,
                        "weighted_calls_per_check": 0.0,
                    },
                )
                service_breakdown["refresh_ttl"] = float(service_metrics_ttl)
                service_breakdown["refresh_ratio"] = refresh_ratio
                service_breakdown["last_refresh_api_calls"] += refresh_api_calls
                service_breakdown["weighted_calls_per_check"] += weighted_calls
                weighted_calls_per_check_by_service[service_name] = service_breakdown

                if service_metrics_ttl != self._cache_ttl:
                    weighted_calls_per_check_overridden_total += weighted_calls
                    weighted_calls_per_check_overridden_by_service[service_name] = (
                        weighted_calls_per_check_overridden_by_service.get(service_name, 0.0)
                        + weighted_calls
                    )
                else:
                    weighted_calls_per_check_default_total += weighted_calls
                    weighted_calls_per_check_default_by_service[service_name] = (
                        weighted_calls_per_check_default_by_service.get(service_name, 0.0)
                        + weighted_calls
                    )

        # Calculate checks per month based on cache TTL
        checks_per_month = (
            (30 * 24 * 60 * 60) // self._cache_ttl if self._cache_ttl > 0 else 8640
        )

        return {
            "CloudWatchMetrics": combined_metrics,
            "CloudWatchResourceMetadata": resource_metadata,
            "CloudWatchAPICounter": {
                "requests_made": sum(requests_by_region.values()),
                "requests_by_region": requests_by_region,
                "requests_by_service": self._api_counter.get_breakdown(),
                "aws_monthly_total": aws_usage,
                "aws_forecast_total": aws_forecast,
                "free_tier_limit": CLOUDWATCH_FREE_TIER_LIMIT,
                "percentage_used": (aws_usage / CLOUDWATCH_FREE_TIER_LIMIT) * 100
                if CLOUDWATCH_FREE_TIER_LIMIT
                else 0,
                "forecast_percentage": (aws_forecast / CLOUDWATCH_FREE_TIER_LIMIT) * 100
                if CLOUDWATCH_FREE_TIER_LIMIT
                else 0,
                "limit_reached": limit_reached,
                "monitoring_stopped": False,
            },
            "CloudWatchAPIConfig": {
                "services_count": total_services_count,
                "calls_per_check": round(estimated_calls_per_check, 3),
                "cache_ttl": self._cache_ttl,
                "discovery_ttl": self._discovery_ttl,
                "service_metrics_ttl_overrides": SERVICE_METRICS_TTL_OVERRIDES,
                "weighted_calls_per_check_by_service": weighted_calls_per_check_by_service,
                "weighted_calls_per_check_overridden_total": round(
                    weighted_calls_per_check_overridden_total, 3
                ),
                "weighted_calls_per_check_default_total": round(
                    weighted_calls_per_check_default_total, 3
                ),
                "weighted_calls_per_check_overridden_by_service": {
                    service: round(value, 3)
                    for service, value in weighted_calls_per_check_overridden_by_service.items()
                },
                "weighted_calls_per_check_default_by_service": {
                    service: round(value, 3)
                    for service, value in weighted_calls_per_check_default_by_service.items()
                },
                "checks_per_month": checks_per_month,
                "warning_threshold": self._api_warn,
                "critical_threshold": self._api_crit,
                "force_over_limit": self._force_over_limit,
            },
            "CloudWatchErrors": self._error_collector.to_list(),
            "CloudWatchEmptyServices": empty_services,
        }
