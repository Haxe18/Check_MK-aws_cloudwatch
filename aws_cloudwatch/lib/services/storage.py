#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Storage service sections (EBS, S3).

This module provides CloudWatch monitoring for:
- EBS volumes
- S3 buckets (storage metrics)
"""

from datetime import datetime, timezone

from ..base import CloudWatchSection
from ..types import MetricDefinition, MetricResult, Resource


class EBSSection(CloudWatchSection):
    """EBS volume metrics.

    Monitors volume operations, throughput, and burst balance.
    """

    @property
    def name(self) -> str:
        return "ebs"

    @property
    def title(self) -> str:
        return "EBS"

    @property
    def namespace(self) -> str:
        return "AWS/EBS"

    @property
    def dimension_key(self) -> str:
        return "VolumeId"

    @property
    def metrics(self) -> list[MetricDefinition]:
        return [
            # Volume operations
            MetricDefinition("VolumeReadOps", "Sum", "Count"),
            MetricDefinition("VolumeWriteOps", "Sum", "Count"),
            MetricDefinition("VolumeReadBytes", "Sum", "Bytes"),
            MetricDefinition("VolumeWriteBytes", "Sum", "Bytes"),
            # Queue and latency
            MetricDefinition("VolumeQueueLength", "Average", "Count"),
            MetricDefinition("VolumeTotalReadTime", "Average", "Seconds"),
            MetricDefinition("VolumeTotalWriteTime", "Average", "Seconds"),
            # Throughput percentage (Provisioned IOPS)
            MetricDefinition("VolumeThroughputPercentage", "Average", "Percent"),
            MetricDefinition("VolumeConsumedReadWriteOps", "Sum", "Count"),
            # Burst balance (gp2)
            MetricDefinition("BurstBalance", "Average", "Percent"),
        ]


class S3Section(CloudWatchSection):
    """S3 bucket storage metrics.

    Monitors bucket size and object count.
    These metrics are reported daily by AWS.
    """

    @property
    def name(self) -> str:
        return "s3"

    @property
    def title(self) -> str:
        return "S3"

    @property
    def namespace(self) -> str:
        return "AWS/S3"

    @property
    def dimension_key(self) -> str:
        return "BucketName"

    @property
    def metrics(self) -> list[MetricDefinition]:
        return [
            MetricDefinition("BucketSizeBytes", "Average", "Bytes"),
            MetricDefinition("NumberOfObjects", "Average", "Count"),
        ]

    @staticmethod
    def _extract_bucket_and_storage_type(metric_info: dict) -> tuple[str | None, str | None]:
        """Return bucket name and storage type from metric dimensions."""
        dimensions = metric_info.get("Dimensions", [])
        bucket_name: str | None = None
        storage_type: str | None = None

        for dim in dimensions:
            if dim.get("Name") == "BucketName":
                bucket_name = dim.get("Value")
            elif dim.get("Name") == "StorageType":
                storage_type = dim.get("Value")

        return bucket_name, storage_type

    def discover_resources(self) -> list[Resource]:
        """Discover S3 buckets and remember metric-specific storage type dimensions."""
        response = self._client.list_metrics(self.namespace)
        self._api_counter.increment(
            response.get("PageCount", 1), service=self.name, api_type="list_metrics"
        )
        metrics_list = response.get("Metrics", [])

        resources: dict[str, Resource] = {}

        for metric_info in metrics_list:
            metric_name = metric_info.get("MetricName")
            bucket_name, storage_type = self._extract_bucket_and_storage_type(metric_info)

            if not bucket_name:
                continue
            if metric_name not in {"BucketSizeBytes", "NumberOfObjects"}:
                continue

            if bucket_name not in resources:
                resources[bucket_name] = Resource(
                    id=bucket_name,
                    dimensions={"BucketName": bucket_name},
                    available_metrics=[],
                    metadata={
                        "bucket_size_storage_types": [],
                        "object_count_storage_types": [],
                    },
                )

            resource = resources[bucket_name]
            if metric_name not in resource.available_metrics:
                resource.available_metrics.append(metric_name)

            if not storage_type:
                continue

            if metric_name == "BucketSizeBytes":
                key = "bucket_size_storage_types"
            else:
                key = "object_count_storage_types"

            storage_types = resource.metadata.setdefault(key, [])
            if isinstance(storage_types, list) and storage_type not in storage_types:
                storage_types.append(storage_type)

        return list(resources.values())

    @staticmethod
    def _storage_types_from_metadata(resource: Resource, key: str) -> list[str]:
        storage_types = resource.metadata.get(key, [])
        if not isinstance(storage_types, list):
            return []
        return [st for st in storage_types if isinstance(st, str) and st]

    def _fetch_bucket_metric(
        self,
        bucket_name: str,
        storage_type: str,
        metric: MetricDefinition,
        start_time: datetime,
        end_time: datetime,
        period: int,
    ) -> MetricResult | None:
        bucket_resource = Resource(
            id=bucket_name,
            dimensions={
                "BucketName": bucket_name,
                "StorageType": storage_type,
            },
            available_metrics=[metric.name],
        )
        return self.fetch_metric(bucket_resource, metric, start_time, end_time, period)

    def fetch_all_metrics(
        self, resources: list[Resource], period: int = 300
    ) -> list[MetricResult]:
        """Fetch S3 metrics with metric-specific StorageType handling.

        Bucket size is aggregated across all storage classes for the bucket.
        Object count is fetched using AllStorageTypes when available.
        """
        lookback_seconds, query_period = self.metric_query_window(period)
        end_time = datetime.now(timezone.utc)
        start_time = datetime.fromtimestamp(
            end_time.timestamp() - lookback_seconds, tz=timezone.utc
        )

        bucket_size_metric = MetricDefinition("BucketSizeBytes", "Average", "Bytes")
        object_count_metric = MetricDefinition("NumberOfObjects", "Average", "Count")
        results: list[MetricResult] = []

        for resource in resources:
            bucket_name = resource.id

            size_storage_types = self._storage_types_from_metadata(
                resource, "bucket_size_storage_types"
            )
            size_storage_types = [st for st in size_storage_types if st != "AllStorageTypes"]
            if not size_storage_types:
                size_storage_types = ["StandardStorage"]

            total_size = 0.0
            latest_size_ts: datetime | None = None
            for storage_type in size_storage_types:
                size_result = self._fetch_bucket_metric(
                    bucket_name,
                    storage_type,
                    bucket_size_metric,
                    start_time,
                    end_time,
                    query_period,
                )
                if not size_result:
                    continue
                total_size += float(size_result.value)
                if size_result.timestamp:
                    try:
                        ts = datetime.fromisoformat(size_result.timestamp)
                        if latest_size_ts is None or ts > latest_size_ts:
                            latest_size_ts = ts
                    except ValueError:
                        pass

            results.append(
                MetricResult(
                    resource_id=bucket_name,
                    metric_name=bucket_size_metric.name,
                    value=total_size,
                    unit=bucket_size_metric.unit,
                    stat=bucket_size_metric.stat,
                    timestamp=latest_size_ts.isoformat() if latest_size_ts else None,
                    period=query_period,
                    region=self._client.region,
                )
            )

            object_storage_types = self._storage_types_from_metadata(
                resource, "object_count_storage_types"
            )
            object_storage_type = (
                "AllStorageTypes"
                if "AllStorageTypes" in object_storage_types
                else (object_storage_types[0] if object_storage_types else "AllStorageTypes")
            )
            object_result = self._fetch_bucket_metric(
                bucket_name,
                object_storage_type,
                object_count_metric,
                start_time,
                end_time,
                query_period,
            )
            if object_result:
                results.append(object_result)
            else:
                results.append(
                    MetricResult(
                        resource_id=bucket_name,
                        metric_name=object_count_metric.name,
                        value=0.0,
                        unit=object_count_metric.unit,
                        stat=object_count_metric.stat,
                        timestamp=None,
                        period=query_period,
                        region=self._client.region,
                    )
                )

        return results

    def metric_query_window(self, default_period: int) -> tuple[int, int]:
        """Use daily window for S3 storage metrics.

        S3 BucketSizeBytes/NumberOfObjects are reported daily by AWS.
        """
        _ = default_period
        return 48 * 3600, 24 * 3600
