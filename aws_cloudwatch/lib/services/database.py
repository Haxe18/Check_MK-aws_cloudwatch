#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RDS database service section.

This module provides CloudWatch monitoring for RDS instances.
"""

from botocore.exceptions import BotoCoreError, ClientError

from ..base import CloudWatchSection
from ..iam_hints import get_permission_hint
from ..logger import get_logger
from ..types import MetricDefinition, Resource

logger = get_logger("database")


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

        try:
            active_instances = set(self._client.list_rds_instances())

            filtered_resources = []
            for resource in resources:
                if resource.id in active_instances:
                    filtered_resources.append(resource)
                else:
                    logger.debug(
                        "[%s] Filtering out deleting/deleted instance: %s",
                        self.name,
                        resource.id,
                    )

            logger.info(
                "[%s] Filtered %d deleted instances (Active: %d, Total: %d)",
                self.name,
                len(resources) - len(filtered_resources),
                len(filtered_resources),
                len(resources),
            )
            return filtered_resources

        except (BotoCoreError, ClientError) as err:
            hint = get_permission_hint(err, "list_rds")
            if self._error_collector:
                self._error_collector.add(
                    "discovery", self.name, self._client.region, str(err), hint
                )
            hint_msg = f" (Required: {hint})" if hint else ""
            logger.warning(
                "[%s] Failed to list instances for filtering: %s%s. "
                "Returning all discovered metrics.",
                self.name,
                err,
                hint_msg,
            )
            return resources
