#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CloudWatch client wrapper.

This module provides a wrapper around the boto3 CloudWatch client
for making API calls with proper configuration.
"""

import hashlib
from datetime import datetime
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from .logger import get_logger

logger = get_logger("client")

# Retry configuration with adaptive mode (exponential backoff with jitter)
BOTO3_RETRY_CONFIG = Config(
    retries={
        "max_attempts": 3,
        "mode": "adaptive",  # Handles throttling automatically
    },
    connect_timeout=10,
    read_timeout=30,
)


class CloudWatchClient:
    """Wrapper for boto3 CloudWatch client.

    Provides methods for listing metrics and fetching statistics
    using the GetMetricStatistics API (Free Tier).
    """

    def __init__(self, access_key: str, secret_key: str, region: str) -> None:
        """Initialize the CloudWatch client.

        Note: Credentials are passed to a boto3 Session and not stored
        as explicit instance variables (other than within the Session) to
        minimize credential exposure.

        Args:
            access_key: AWS Access Key ID
            secret_key: AWS Secret Access Key
            region: AWS region name
        """
        self._region = region

        # Create a session to manage credentials and clients
        self._session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

        # CloudWatch client is always needed, so we initialize it upfront
        self._client = self._session.client(
            "cloudwatch",
            config=BOTO3_RETRY_CONFIG,
        )

        # Lazy-loaded clients for other services
        self._service_clients: dict[str, Any] = {}

    def _get_service_client(self, service_name: str) -> Any:
        """Get or create a client for a specific service (lazy initialization).

        Args:
            service_name: Name of the AWS service (e.g. 'lambda', 'ec2')

        Returns:
            boto3 client for the service
        """
        if service_name not in self._service_clients:
            self._service_clients[service_name] = self._session.client(
                service_name,
                config=BOTO3_RETRY_CONFIG,
            )
        return self._service_clients[service_name]

    @staticmethod
    def get_profile_hash(access_key: str) -> str:
        """Generate a hash of the access key for use in cache directory names.

        This avoids exposing any part of the access key in the filesystem.

        Args:
            access_key: AWS Access Key ID

        Returns:
            First 8 characters of SHA-256 hash
        """
        return hashlib.sha256(access_key.encode()).hexdigest()[:8]

    @property
    def region(self) -> str:
        """Get the region this client is configured for."""
        return self._region

    def list_metrics(self, namespace: str) -> dict[str, Any]:
        """List metrics in a CloudWatch namespace with pagination.

        Uses paginator to handle namespaces with >500 metrics.

        Args:
            namespace: CloudWatch namespace (e.g., "AWS/EC2")

        Returns:
            Response dictionary containing 'Metrics' list (all pages combined)
            and 'PageCount' (each page is one billed API request)
        """
        all_metrics: list[dict[str, Any]] = []
        page_count = 0
        paginator = self._client.get_paginator("list_metrics")

        for page in paginator.paginate(Namespace=namespace):
            page_count += 1
            all_metrics.extend(page.get("Metrics", []))

        return {"Metrics": all_metrics, "PageCount": page_count}

    def get_metric_statistics(
        self,
        namespace: str,
        metric_name: str,
        dimensions: list[dict[str, str]],
        start_time: datetime,
        end_time: datetime,
        period: int,
        statistics: list[str],
    ) -> dict[str, Any]:
        """Fetch metric statistics using GetMetricStatistics API.

        This uses the Free Tier API (1M requests/month free).

        Args:
            namespace: CloudWatch namespace
            metric_name: Name of the metric
            dimensions: List of dimension dicts with 'Name' and 'Value'
            start_time: Start of the time range
            end_time: End of the time range
            period: Granularity in seconds
            statistics: List of statistics to retrieve

        Returns:
            Response dictionary containing 'Datapoints' list
        """
        return self._client.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=period,
            Statistics=statistics,
        )

    def list_lambda_functions(self) -> list[str]:
        """List all Lambda functions in the region.

        Returns:
            List of function names
        """
        function_names = []
        client = self._get_service_client("lambda")
        paginator = client.get_paginator("list_functions")

        for page in paginator.paginate():
            for function in page.get("Functions", []):
                function_names.append(function["FunctionName"])

        return function_names

    def list_ec2_instances(self) -> list[str]:
        """List all active EC2 instances in the region.

        Excludes terminated instances.

        Returns:
            List of instance IDs
        """
        instance_ids = []
        client = self._get_service_client("ec2")
        paginator = client.get_paginator("describe_instances")

        for page in paginator.paginate():
            for reservation in page.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    # Filter out terminated instances
                    if instance.get("State", {}).get("Name") != "terminated":
                        instance_ids.append(instance["InstanceId"])

        return instance_ids

    def list_rds_instances(self) -> list[str]:
        """List all active RDS instances in the region.

        Excludes instances that are being deleted or already deleted.
        Stopped instances are still considered active (they exist and can be restarted).

        Returns:
            List of DB instance identifiers
        """
        inactive_states = {"deleting", "deleted"}
        db_ids = []
        client = self._get_service_client("rds")
        paginator = client.get_paginator("describe_db_instances")

        for page in paginator.paginate():
            for db_instance in page.get("DBInstances", []):
                if db_instance.get("DBInstanceStatus") not in inactive_states:
                    db_ids.append(db_instance["DBInstanceIdentifier"])

        return db_ids

    def list_lambda_edge_functions(self) -> list[str]:
        """List Lambda@Edge functions from us-east-1.

        Lambda@Edge functions are always created in us-east-1 (AWS requirement).
        This method uses a us-east-1-specific client regardless of the current region.

        Returns:
            List of function names
        """
        function_names = []
        lambda_client = self._session.client(
            "lambda", region_name="us-east-1", config=BOTO3_RETRY_CONFIG
        )
        paginator = lambda_client.get_paginator("list_functions")

        for page in paginator.paginate():
            for function in page.get("Functions", []):
                function_names.append(function["FunctionName"])

        return function_names

    def list_cloudfront_distributions(self) -> list[dict]:
        """List all CloudFront distributions with metadata (Comment, DomainName, Aliases).

        Returns:
            List of distribution dicts from AWS API
        """
        client = self._get_service_client("cloudfront")
        paginator = client.get_paginator("list_distributions")
        distributions = []
        for page in paginator.paginate():
            items = page.get("DistributionList", {}).get("Items", [])
            distributions.extend(items)
        return distributions

    def list_cloudfront_functions(self) -> list[str]:
        """List all deployed (LIVE) CloudFront Functions.

        Uses manual pagination (boto3 has no paginator for CloudFront list_functions).

        Returns:
            List of function names
        """
        function_names = []
        client = self._get_service_client("cloudfront")
        kwargs: dict = {"Stage": "LIVE"}

        while True:
            response = client.list_functions(**kwargs)
            func_list = response.get("FunctionList", {})
            for func in func_list.get("Items", []):
                function_names.append(func["Name"])
            next_marker = func_list.get("NextMarker")
            if not next_marker:
                break
            kwargs["Marker"] = next_marker

        return function_names


class FreeTierClient:
    """Client for AWS Free Tier API.

    Used to fetch CloudWatch API usage information.
    """

    def __init__(self, access_key: str, secret_key: str) -> None:
        """Initialize the Free Tier client.

        Note: Credentials are passed directly to boto3 and not stored
        as instance variables to minimize credential exposure.

        Args:
            access_key: AWS Access Key ID
            secret_key: AWS Secret Access Key
        """
        config = Config(
            retries={"max_attempts": 2, "mode": "standard"},
            connect_timeout=5,
            read_timeout=10,
        )
        # Credentials passed directly to boto3, not stored
        self._client = boto3.client(
            "freetier",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
            config=config,
        )

    def get_cloudwatch_usage(self) -> tuple[int, int]:
        """Fetch CloudWatch API usage from Free Tier API.

        Uses pagination to handle accounts with many free tier offerings.

        Returns:
            Tuple of (actual_usage, forecasted_usage) or (0, 0) if unavailable
        """
        try:
            paginator = self._client.get_paginator("get_free_tier_usage")
            for page in paginator.paginate():
                for entry in page.get("freeTierUsages", []):
                    service = entry.get("service", "")
                    usage_type = entry.get("usageType", "")

                    if service == "AmazonCloudWatch" and "CW:Requests" in usage_type:
                        actual = int(float(entry.get("actualUsageAmount", 0)))
                        forecast = int(float(entry.get("forecastedUsageAmount", 0)))
                        return actual, forecast
        except (BotoCoreError, ClientError) as err:
            logger.warning("FreeTier API error: %s", err)
        except (TypeError, ValueError) as err:
            logger.warning("Error parsing FreeTier response: %s", err)

        return 0, 0
