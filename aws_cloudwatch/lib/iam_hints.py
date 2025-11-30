#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IAM permission hints for AWS CloudWatch errors.

This module provides helpful permission hints for common AWS IAM
errors encountered during CloudWatch monitoring.
"""

from botocore.exceptions import ClientError

# Mapping: Error Code -> API context -> Required IAM permission
IAM_PERMISSION_HINTS: dict[str, dict[str, str]] = {
    "AccessDenied": {
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
    },
    "AccessDeniedException": {
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
    },
    "UnauthorizedAccess": {
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
    },
    "UnauthorizedOperation": {
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
    },
}


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

    hints_for_code = IAM_PERMISSION_HINTS.get(error_code)
    if hints_for_code:
        return hints_for_code.get(context)

    return None


def format_error_with_hint(message: str, hint: str | None) -> str:
    """Format an error message with an optional permission hint.

    Args:
        message: The original error message
        hint: Optional permission hint

    Returns:
        Formatted error message with hint appended if available
    """
    if hint:
        return f"{message} (Required: {hint})"
    return message
