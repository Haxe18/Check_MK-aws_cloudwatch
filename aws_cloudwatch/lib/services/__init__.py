#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Service registry for CloudWatch sections.

This module imports all service sections and provides
a registry for the orchestrator to use.
"""

from typing import Type

from ..base import CloudWatchSection

# Import all service sections
from .cloudfront import CloudFrontFunctionsSection, CloudFrontSection
from .compute import EC2Section
from .database import RDSSection
from .dynamodb import DynamoDBSection
from .networking import ELBSection, ELBv2ApplicationSection, ELBv2NetworkSection
from .serverless import LambdaInsightsSection, LambdaSection
from .storage import EBSSection, S3Section

# Registry mapping service keys to section classes
SECTION_REGISTRY: dict[str, Type[CloudWatchSection]] = {
    # CloudFront
    "cloudfront": CloudFrontSection,
    "cloudfront_functions": CloudFrontFunctionsSection,
    # Compute
    "ec2": EC2Section,
    # Database
    "rds": RDSSection,
    # DynamoDB
    "dynamodb": DynamoDBSection,
    # Storage
    "ebs": EBSSection,
    "s3": S3Section,
    # Networking
    "elb": ELBSection,
    "elbv2_application": ELBv2ApplicationSection,
    "elbv2_network": ELBv2NetworkSection,
    # Serverless
    "aws_lambda": LambdaSection,
    "lambda_insights": LambdaInsightsSection,
}

__all__ = [
    "SECTION_REGISTRY",
    "CloudFrontSection",
    "CloudFrontFunctionsSection",
    "EC2Section",
    "RDSSection",
    "DynamoDBSection",
    "EBSSection",
    "S3Section",
    "ELBSection",
    "ELBv2ApplicationSection",
    "ELBv2NetworkSection",
    "LambdaSection",
    "LambdaInsightsSection",
]
