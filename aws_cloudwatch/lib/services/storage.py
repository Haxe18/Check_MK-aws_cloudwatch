#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Storage service sections (EBS, S3).

This module provides CloudWatch monitoring for:
- EBS volumes
- S3 buckets (storage metrics)
"""

from ..base import CloudWatchSection
from ..types import MetricDefinition, Resource


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
            MetricDefinition("VolumeTotalReadTime", "Sum", "Seconds"),
            MetricDefinition("VolumeTotalWriteTime", "Sum", "Seconds"),
            MetricDefinition("VolumeIdleTime", "Sum", "Seconds"),
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
    AWS publishes both only per StorageType; the values of all StorageTypes
    listed for a bucket are summed (AWS lists NumberOfObjects only under
    AllStorageTypes).
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
            MetricDefinition(
                "BucketSizeBytes", "Average", "Bytes", extra_dimension="StorageType"
            ),
            MetricDefinition(
                "NumberOfObjects", "Average", "Count", extra_dimension="StorageType"
            ),
        ]

    def discover_resources(self) -> list[Resource]:
        """Keep only buckets with storage metrics (request metrics alone are not monitored)."""
        storage_metrics = {metric.name for metric in self.metrics}
        return [
            resource
            for resource in super().discover_resources()
            if storage_metrics.intersection(resource.available_metrics)
        ]

    def metric_query_window(self, default_period: int) -> tuple[int, int]:
        """Use daily window for S3 storage metrics.

        S3 BucketSizeBytes/NumberOfObjects are reported daily by AWS.
        """
        _ = default_period
        return 48 * 3600, 24 * 3600
