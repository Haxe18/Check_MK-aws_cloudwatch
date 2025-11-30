#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load Balancer service sections.

This module provides CloudWatch monitoring for:
- Classic ELB
- Application Load Balancer (ALB)
- Network Load Balancer (NLB)
"""

from ..base import CloudWatchSection
from ..types import MetricDefinition, Resource


class ELBSection(CloudWatchSection):
    """Classic Elastic Load Balancer metrics.

    Monitors requests, health, latency, and HTTP response codes.
    """

    @property
    def name(self) -> str:
        return "elb"

    @property
    def title(self) -> str:
        return "ELB Classic"

    @property
    def namespace(self) -> str:
        return "AWS/ELB"

    @property
    def dimension_key(self) -> str:
        return "LoadBalancerName"

    @property
    def metrics(self) -> list[MetricDefinition]:
        return [
            # Request metrics
            MetricDefinition("RequestCount", "Sum", "Count"),
            # Health metrics
            MetricDefinition("HealthyHostCount", "Average", "Count"),
            MetricDefinition("UnHealthyHostCount", "Average", "Count"),
            # Latency
            MetricDefinition("Latency", "Average", "Seconds"),
            # HTTP codes (backend)
            MetricDefinition("HTTPCode_Backend_2XX", "Sum", "Count"),
            MetricDefinition("HTTPCode_Backend_3XX", "Sum", "Count"),
            MetricDefinition("HTTPCode_Backend_4XX", "Sum", "Count"),
            MetricDefinition("HTTPCode_Backend_5XX", "Sum", "Count"),
            # HTTP codes (ELB)
            MetricDefinition("HTTPCode_ELB_4XX", "Sum", "Count"),
            MetricDefinition("HTTPCode_ELB_5XX", "Sum", "Count"),
            # Spillover and surge queue
            MetricDefinition("SpilloverCount", "Sum", "Count"),
            MetricDefinition("SurgeQueueLength", "Maximum", "Count"),
        ]


class ELBv2ApplicationSection(CloudWatchSection):
    """Application Load Balancer (ALB) metrics.

    Monitors requests, connections, response times, and HTTP codes.
    ALB uses the LoadBalancer dimension format: "app/name/hash".
    """

    @property
    def name(self) -> str:
        return "elbv2_application"

    @property
    def title(self) -> str:
        return "Application Load Balancer (ALB)"

    @property
    def namespace(self) -> str:
        return "AWS/ApplicationELB"

    @property
    def dimension_key(self) -> str:
        return "LoadBalancer"

    @property
    def metrics(self) -> list[MetricDefinition]:
        return [
            # Request metrics
            MetricDefinition("RequestCount", "Sum", "Count"),
            MetricDefinition("RequestCountPerTarget", "Sum", "Count"),
            # Connection metrics
            MetricDefinition("ActiveConnectionCount", "Sum", "Count"),
            MetricDefinition("NewConnectionCount", "Sum", "Count"),
            MetricDefinition("RejectedConnectionCount", "Sum", "Count"),
            MetricDefinition("ClientTLSNegotiationErrorCount", "Sum", "Count"),
            # Response time
            MetricDefinition("TargetResponseTime", "Average", "Seconds"),
            # Data transfer
            MetricDefinition("ProcessedBytes", "Sum", "Bytes"),
            # HTTP codes (Target)
            MetricDefinition("HTTPCode_Target_2XX_Count", "Sum", "Count"),
            MetricDefinition("HTTPCode_Target_3XX_Count", "Sum", "Count"),
            MetricDefinition("HTTPCode_Target_4XX_Count", "Sum", "Count"),
            MetricDefinition("HTTPCode_Target_5XX_Count", "Sum", "Count"),
            # HTTP codes (ELB)
            MetricDefinition("HTTPCode_ELB_3XX_Count", "Sum", "Count"),
            MetricDefinition("HTTPCode_ELB_4XX_Count", "Sum", "Count"),
            MetricDefinition("HTTPCode_ELB_5XX_Count", "Sum", "Count"),
            MetricDefinition("HTTPCode_ELB_500_Count", "Sum", "Count"),
            MetricDefinition("HTTPCode_ELB_502_Count", "Sum", "Count"),
            MetricDefinition("HTTPCode_ELB_503_Count", "Sum", "Count"),
            MetricDefinition("HTTPCode_ELB_504_Count", "Sum", "Count"),
            # Target health
            MetricDefinition("HealthyHostCount", "Average", "Count"),
            MetricDefinition("UnHealthyHostCount", "Average", "Count"),
            # Target connection errors
            MetricDefinition("TargetConnectionErrorCount", "Sum", "Count"),
            MetricDefinition("TargetTLSNegotiationErrorCount", "Sum", "Count"),
        ]

    def _extract_resource(self, metric_info: dict) -> Resource | None:
        """Extract ALB from metric dimensions.

        ALB LoadBalancer dimension format: "app/my-alb/50dc6c495c0c9188"
        We extract a friendly name from this format.
        """
        dimensions = metric_info.get("Dimensions", [])
        load_balancer = None

        for dim in dimensions:
            if dim["Name"] == "LoadBalancer":
                load_balancer = dim["Value"]
                break

        if not load_balancer:
            return None

        # Extract friendly name from "app/my-alb/hash" format
        parts = load_balancer.split("/")
        friendly_name = parts[1] if len(parts) >= 2 else load_balancer

        return Resource(
            id=friendly_name,
            dimensions={"LoadBalancer": load_balancer},
            available_metrics=[],
        )


class ELBv2NetworkSection(CloudWatchSection):
    """Network Load Balancer (NLB) metrics.

    Monitors flows, connections, bytes, and TCP resets.
    NLB uses the LoadBalancer dimension format: "net/name/hash".
    """

    @property
    def name(self) -> str:
        return "elbv2_network"

    @property
    def title(self) -> str:
        return "Network Load Balancer (NLB)"

    @property
    def namespace(self) -> str:
        return "AWS/NetworkELB"

    @property
    def dimension_key(self) -> str:
        return "LoadBalancer"

    @property
    def metrics(self) -> list[MetricDefinition]:
        return [
            # Flow metrics
            MetricDefinition("ActiveFlowCount", "Average", "Count"),
            MetricDefinition("ActiveFlowCount_TCP", "Average", "Count"),
            MetricDefinition("ActiveFlowCount_UDP", "Average", "Count"),
            MetricDefinition("ActiveFlowCount_TLS", "Average", "Count"),
            MetricDefinition("NewFlowCount", "Sum", "Count"),
            MetricDefinition("NewFlowCount_TCP", "Sum", "Count"),
            MetricDefinition("NewFlowCount_UDP", "Sum", "Count"),
            MetricDefinition("NewFlowCount_TLS", "Sum", "Count"),
            MetricDefinition("ConsumedLCUs", "Average", "Count"),
            # Data transfer
            MetricDefinition("ProcessedBytes", "Sum", "Bytes"),
            MetricDefinition("ProcessedBytes_TCP", "Sum", "Bytes"),
            MetricDefinition("ProcessedBytes_UDP", "Sum", "Bytes"),
            MetricDefinition("ProcessedBytes_TLS", "Sum", "Bytes"),
            MetricDefinition("ProcessedPackets", "Sum", "Count"),
            # TCP resets
            MetricDefinition("TCP_Client_Reset_Count", "Sum", "Count"),
            MetricDefinition("TCP_Target_Reset_Count", "Sum", "Count"),
            MetricDefinition("TCP_ELB_Reset_Count", "Sum", "Count"),
            # TLS errors
            MetricDefinition("ClientTLSNegotiationErrorCount", "Sum", "Count"),
            MetricDefinition("TargetTLSNegotiationErrorCount", "Sum", "Count"),
            # Health
            MetricDefinition("HealthyHostCount", "Average", "Count"),
            MetricDefinition("UnHealthyHostCount", "Average", "Count"),
        ]

    def _extract_resource(self, metric_info: dict) -> Resource | None:
        """Extract NLB from metric dimensions.

        NLB LoadBalancer dimension format: "net/my-nlb/50dc6c495c0c9188"
        We extract a friendly name from this format.
        """
        dimensions = metric_info.get("Dimensions", [])
        load_balancer = None

        for dim in dimensions:
            if dim["Name"] == "LoadBalancer":
                load_balancer = dim["Value"]
                break

        if not load_balancer:
            return None

        # Extract friendly name from "net/my-nlb/hash" format
        parts = load_balancer.split("/")
        friendly_name = parts[1] if len(parts) >= 2 else load_balancer

        return Resource(
            id=friendly_name,
            dimensions={"LoadBalancer": load_balancer},
            available_metrics=[],
        )
