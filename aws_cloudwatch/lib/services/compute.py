#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EC2 compute service section.

This module provides CloudWatch monitoring for EC2 instances.
"""

from botocore.exceptions import BotoCoreError, ClientError

from ..base import CloudWatchSection
from ..iam_hints import get_permission_hint
from ..logger import get_logger
from ..types import MetricDefinition, Resource

logger = get_logger("compute")


class EC2Section(CloudWatchSection):
    """EC2 instance metrics.

    Monitors CPU, network, disk, and status check metrics.
    Includes extended metrics for T-series burstable instances.
    """

    @property
    def name(self) -> str:
        return "ec2"

    @property
    def title(self) -> str:
        return "EC2"

    @property
    def namespace(self) -> str:
        return "AWS/EC2"

    @property
    def dimension_key(self) -> str:
        return "InstanceId"

    @property
    def metrics(self) -> list[MetricDefinition]:
        return [
            # CPU metrics
            MetricDefinition("CPUUtilization", "Average", "Percent"),
            MetricDefinition("CPUCreditUsage", "Average", "Count"),
            MetricDefinition("CPUCreditBalance", "Average", "Count"),
            # Network metrics
            MetricDefinition("NetworkIn", "Sum", "Bytes"),
            MetricDefinition("NetworkOut", "Sum", "Bytes"),
            MetricDefinition("NetworkPacketsIn", "Sum", "Count"),
            MetricDefinition("NetworkPacketsOut", "Sum", "Count"),
            # Disk metrics (instance store)
            MetricDefinition("DiskReadOps", "Sum", "Count"),
            MetricDefinition("DiskWriteOps", "Sum", "Count"),
            MetricDefinition("DiskReadBytes", "Sum", "Bytes"),
            MetricDefinition("DiskWriteBytes", "Sum", "Bytes"),
            # EBS metrics (through EC2)
            MetricDefinition("EBSReadOps", "Sum", "Count"),
            MetricDefinition("EBSWriteOps", "Sum", "Count"),
            MetricDefinition("EBSReadBytes", "Sum", "Bytes"),
            MetricDefinition("EBSWriteBytes", "Sum", "Bytes"),
            # Status checks
            MetricDefinition("StatusCheckFailed", "Maximum", "Count"),
            MetricDefinition("StatusCheckFailed_Instance", "Maximum", "Count"),
            MetricDefinition("StatusCheckFailed_System", "Maximum", "Count"),
        ]

    def discover_resources(self) -> list[Resource]:
        """Discover EC2 instances and filter out terminated ones.

        Uses CloudWatch list_metrics for initial discovery, then
        validates against EC2 API to remove terminated instances.
        """
        resources = super().discover_resources()
        if not resources:
            return resources

        try:
            active_instances = set(self._client.list_ec2_instances())

            filtered_resources = []
            for resource in resources:
                if resource.id in active_instances:
                    filtered_resources.append(resource)
                else:
                    logger.debug(
                        "[%s] Filtering out terminated instance: %s", self.name, resource.id
                    )

            logger.info(
                "[%s] Filtered %d terminated instances (Active: %d, Total: %d)",
                self.name,
                len(resources) - len(filtered_resources),
                len(filtered_resources),
                len(resources),
            )
            return filtered_resources

        except (BotoCoreError, ClientError) as err:
            hint = get_permission_hint(err, "list_ec2")
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
