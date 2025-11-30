#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS CloudWatch Library for Checkmk.

This package provides the class-based architecture for monitoring
AWS CloudWatch metrics using the GetMetricStatistics API (Free Tier).

Uses stable Checkmk APIs only:
- cmk.utils.paths.var_dir for cache directory
- Own DataCache implementation for file-based caching
"""

from .base import CloudWatchSection
from .cache import APICounter, DataCache
from .client import CloudWatchClient
from .errors import CloudWatchError, ErrorCollector
from .orchestrator import CloudWatchOrchestrator
from .types import MetricDefinition, MetricResult, Resource

__all__ = [
    "MetricDefinition",
    "Resource",
    "MetricResult",
    "CloudWatchSection",
    "CloudWatchClient",
    "APICounter",
    "DataCache",
    "CloudWatchOrchestrator",
    "ErrorCollector",
    "CloudWatchError",
]
