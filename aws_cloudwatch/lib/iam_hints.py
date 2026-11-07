#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IAM permission hints for AWS CloudWatch errors.

This module provides helpful permission hints for common AWS IAM
errors encountered during CloudWatch monitoring.
"""

from botocore.exceptions import ClientError

# API context -> required IAM permission
_PERMISSION_BY_CONTEXT: dict[str, str] = {
    "list_metrics": "cloudwatch:ListMetrics",
    "get_statistics": "cloudwatch:GetMetricStatistics",
    "free_tier": "freetier:GetFreeTierUsage",
    "create_client": "cloudwatch:*",
    "list_functions": "lambda:ListFunctions",
    "list_lambda_edge": "lambda:ListFunctions",
    "list_cloudfront_functions": "cloudfront:ListFunctions",
    "list_cloudfront_distributions": "cloudfront:ListDistributions",
    "list_ec2": "ec2:DescribeInstances",
    "list_rds": "rds:DescribeDBInstances",
}

# AWS error codes that mean a missing IAM permission
_ACCESS_ERROR_CODES = frozenset(
    {"AccessDenied", "AccessDeniedException", "UnauthorizedAccess", "UnauthorizedOperation"}
)


def get_permission_hint(error: ClientError | Exception, context: str) -> str | None:
    """Extract helpful IAM permission hint from a ClientError.

    Args:
        error: The boto3 ClientError or other exception
        context: API context ("list_metrics", "get_statistics", "free_tier", "create_client")

    Returns:
        Permission hint string or None if no hint available
    """
    if not isinstance(error, ClientError):
        return None

    try:
        error_code = error.response.get("Error", {}).get("Code", "")
    except (AttributeError, KeyError):
        return None

    if error_code in _ACCESS_ERROR_CODES:
        return _PERMISSION_BY_CONTEXT.get(context)

    return None

