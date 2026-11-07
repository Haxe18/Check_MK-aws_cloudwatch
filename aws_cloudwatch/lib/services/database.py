#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RDS database service section.

This module provides CloudWatch monitoring for RDS instances.
"""

from ..base import CloudWatchSection
from ..types import MetricDefinition, Resource


class RDSSection(CloudWatchSection):
    """RDS database instance metrics.

    Monitors CPU, memory, storage, connections, IOPS, and latency.
    Includes extended metrics for replica monitoring.
    """

    @property
    def name(self) -> str:
        return "rds"

    @property
    def title(self) -> str:
        return "RDS"

    @property
    def namespace(self) -> str:
        return "AWS/RDS"

    @property
    def dimension_key(self) -> str:
        return "DBInstanceIdentifier"

    @property
    def metrics(self) -> list[MetricDefinition]:
        return [
            # CPU metrics
            MetricDefinition("CPUUtilization", "Average", "Percent"),
            MetricDefinition("CPUCreditUsage", "Average", "Count"),
            MetricDefinition("CPUCreditBalance", "Average", "Count"),
            # Memory metrics
            MetricDefinition("FreeableMemory", "Average", "Bytes"),
            MetricDefinition("SwapUsage", "Average", "Bytes"),
            # Storage metrics
            MetricDefinition("FreeStorageSpace", "Average", "Bytes"),
            MetricDefinition("FreeLocalStorage", "Average", "Bytes"),
            # Connection metrics
            MetricDefinition("DatabaseConnections", "Average", "Count"),
            # IOPS metrics
            MetricDefinition("ReadIOPS", "Average", "Count/Second"),
            MetricDefinition("WriteIOPS", "Average", "Count/Second"),
            MetricDefinition("DiskQueueDepth", "Average", "Count"),
            # Throughput metrics
            MetricDefinition("ReadThroughput", "Average", "Bytes/Second"),
            MetricDefinition("WriteThroughput", "Average", "Bytes/Second"),
            MetricDefinition("NetworkReceiveThroughput", "Average", "Bytes/Second"),
            MetricDefinition("NetworkTransmitThroughput", "Average", "Bytes/Second"),
            # Latency metrics
            MetricDefinition("ReadLatency", "Average", "Seconds"),
            MetricDefinition("WriteLatency", "Average", "Seconds"),
            # Burst balance (for gp2/gp3 storage)
            MetricDefinition("BurstBalance", "Average", "Percent"),
            MetricDefinition("EBSIOBalance%", "Average", "Percent"),
            MetricDefinition("EBSByteBalance%", "Average", "Percent"),
            # Replica metrics
            MetricDefinition("ReplicaLag", "Average", "Seconds"),
            MetricDefinition("ReplicationSlotDiskUsage", "Average", "Bytes"),
            # Transaction metrics
            MetricDefinition("CommitLatency", "Average", "Milliseconds"),
            MetricDefinition("CommitThroughput", "Average", "Count/Second"),
            # Aurora specific (if applicable)
            MetricDefinition("AuroraBinlogReplicaLag", "Average", "Seconds"),
            MetricDefinition("AuroraReplicaLag", "Average", "Milliseconds"),
        ]

    def discover_resources(self) -> list[Resource]:
        """Discover RDS instances and filter out deleting/deleted ones.

        Uses CloudWatch list_metrics for initial discovery, then
        validates against RDS API to remove deleted instances.
        """
        resources = super().discover_resources()
        if not resources:
            return resources

        return self._filter_to_existing(
            resources, self._client.list_rds_instances, "list_rds", "RDS instances"
        )
