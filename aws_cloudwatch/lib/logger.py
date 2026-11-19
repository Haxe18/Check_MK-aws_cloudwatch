#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Logging configuration for AWS CloudWatch agent.

This module provides a centralized logging configuration that can be
enabled via the AWS_CLOUDWATCH_DEBUG environment variable.
"""

import logging
import os
import sys

# Check if debug mode is enabled
_DEBUG_ENABLED = os.environ.get("AWS_CLOUDWATCH_DEBUG", "").lower() in ("1", "true", "yes")

# Configure root logger for aws_cloudwatch
_root_logger = logging.getLogger("aws_cloudwatch")

if _DEBUG_ENABLED:
    _root_logger.setLevel(logging.DEBUG)
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - [%(threadName)s] - %(levelname)s - %(message)s"
        )
    )
    _root_logger.addHandler(_handler)
else:
    # In production, only show warnings and errors
    _root_logger.setLevel(logging.WARNING)
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    _root_logger.addHandler(_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given module name.

    Args:
        name: Module name (e.g., 'orchestrator', 'client')

    Returns:
        Configured logger instance
    """
    return logging.getLogger(f"aws_cloudwatch.{name}")
