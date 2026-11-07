#!/usr/bin/env python3
"""Server-side calls configuration for AWS CloudWatch Monitoring special agent.

This module defines how WATO configuration parameters are transformed into
command-line arguments for the special agent executable. It bridges the
gap between the web UI configuration and the agent invocation.

The module handles:
    - AWS credential mapping (access key, secret key via .unsafe())
    - Multi-region service mapping
    - Cache TTL and threshold settings
"""

import json
from collections.abc import Generator
from typing import Any

from cmk.server_side_calls.v1 import (
    SpecialAgentCommand,
    SpecialAgentConfig,
    noop_parser,
)


def _extract_cascading_value(value: Any, default: Any = None) -> Any:
    """Extract value from WATO CascadingSingleChoice tuple format.

    WATO CascadingSingleChoice returns tuples where the last element
    is the actual value. This helper normalizes the extraction.

    Args:
        value: The value that may be a tuple from WATO
        default: Default value if extraction fails

    Returns:
        The extracted value or default
    """
    if isinstance(value, tuple):
        return value[-1] if len(value) >= 2 else value[0] if value else default
    return value if value is not None else default


def _agent_arguments(
    params: dict[str, Any], _host_config: Any
) -> Generator[SpecialAgentCommand, None, None]:
    """Transform WATO configuration parameters into agent CLI arguments.

    Converts the structured configuration from the WATO ruleset into
    command-line arguments for the special agent executable.

    Args:
        params: Configuration dictionary from WATO ruleset containing:
            - aws_access_key_id: AWS access key
            - aws_secret_access_key: AWS secret key (Password object)
            - cloudwatch_regions: List of region configurations
            - cloudwatch_cache_ttl: Metrics cache TTL in seconds
            - cloudwatch_discovery_ttl: Resource discovery cache TTL in seconds
            - cloudwatch_api_warn: Warning threshold percentage
            - cloudwatch_api_crit: Critical threshold percentage
            - cloudwatch_max_workers: Parallel threads (optional, 1-10)
            - cloudwatch_lambda_filter_deleted: Check Lambda functions against the
              Lambda API (optional, off by default)
            - cloudwatch_cloudfront_metadata: Fetch CloudFront description/URL
              (optional, off by default)
        host_config: Host configuration object (unused).

    Yields:
        SpecialAgentCommand: Command with arguments for agent execution.

    Example:
        WATO config produces arguments like:
        --access-key AKIA... --secret-key <secret>
        --cloudwatch-regions-map '{"us-east-1": ["cloudfront"]}'
    """
    secret = params.get("aws_secret_access_key")
    secret_value = secret.unsafe() if hasattr(secret, "unsafe") else str(secret or "")

    args: list[str] = [
        "--access-key",
        str(params.get("aws_access_key_id", "")),
        "--secret-key",
        secret_value,
    ]

    # Multi-region configuration
    regions_config = params.get("cloudwatch_regions", [])
    if regions_config:
        # Build region-to-services mapping
        region_services_map = {}
        for region_conf in regions_config:
            region_name = _extract_cascading_value(
                region_conf.get("region_name"), default="us-east-1"
            )
            services = region_conf.get("services", [])
            if services:
                # Same region added more than once: merge its services
                merged_services = region_services_map.setdefault(region_name, [])
                merged_services.extend(s for s in services if s not in merged_services)

        if region_services_map:
            # Pass as JSON-encoded argument
            args.extend(["--cloudwatch-regions-map", json.dumps(region_services_map)])

    # CloudWatch cache TTL (metrics)
    if params.get("cloudwatch_cache_ttl"):
        args.extend(["--cloudwatch-cache-ttl", str(params.get("cloudwatch_cache_ttl"))])

    # CloudWatch discovery TTL (resource discovery)
    if params.get("cloudwatch_discovery_ttl"):
        args.extend(
            ["--cloudwatch-discovery-ttl", str(params.get("cloudwatch_discovery_ttl"))]
        )

    # CloudWatch API thresholds
    if params.get("cloudwatch_api_warn"):
        args.extend(["--cloudwatch-api-warn", str(int(params.get("cloudwatch_api_warn")))])

    if params.get("cloudwatch_api_crit"):
        args.extend(["--cloudwatch-api-crit", str(int(params.get("cloudwatch_api_crit")))])

    # Free tier limit behavior
    limit_behavior = params.get("cloudwatch_stop_at_limit")
    if limit_behavior:
        behavior = _extract_cascading_value(limit_behavior)
        if behavior == "force":
            args.append("--force-over-limit")

    # Parallel workers
    max_workers = params.get("cloudwatch_max_workers")
    if max_workers is not None:
        args.extend(["--max-workers", str(int(max_workers))])

    # Lambda: hide deleted functions via Lambda API (exposes env vars, opt-in)
    if params.get("cloudwatch_lambda_filter_deleted"):
        args.append("--lambda-filter-deleted")

    # CloudFront: description/URL via ListDistributions (exposes origin headers, opt-in)
    if params.get("cloudwatch_cloudfront_metadata"):
        args.append("--cloudfront-metadata")

    yield SpecialAgentCommand(command_arguments=args)


#: Special agent configuration for AWS CloudWatch Monitoring.
#:
#: Registers the special agent with Checkmk and defines the parameter
#: parser and command generation function. The noop_parser is used
#: since parameters come pre-parsed from WATO.
special_agent_aws_cloudwatch = SpecialAgentConfig(
    name="aws_cloudwatch",
    parameter_parser=noop_parser,
    commands_function=_agent_arguments,
)
