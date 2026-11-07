#!/usr/bin/env python3
"""Shared helper functions for AWS CloudWatch check plugins.

This module provides common utilities used across all service-specific
check plugins to reduce code duplication.
"""

from collections.abc import Callable, Generator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    Metric,
    Result,
    Service,
    State,
    check_levels,
    render,
)

# Type aliases for parsed CloudWatch section
CloudWatchSection = dict[str, Any]
MetricEntry = dict[str, Any]
MetricsByService = dict[str, list[MetricEntry]]

# Service key constants - centralized definitions
SERVICE_EC2 = ":ec2"
SERVICE_RDS = ":rds"
SERVICE_LAMBDA = ":aws_lambda"
SERVICE_LAMBDA_INSIGHTS = ":lambda_insights"
SERVICE_S3 = ":s3"
SERVICE_EBS = ":ebs"
SERVICE_DYNAMODB = ":dynamodb"
SERVICE_ALB = ":elbv2_application"
SERVICE_NLB = ":elbv2_network"
SERVICE_ELB = ":elb"
SERVICE_ELB_V2 = ":elbv2"  # Exclusion marker for classic ELB
SERVICE_CLOUDFRONT = ":cloudfront"
SERVICE_CLOUDFRONT_FUNCTIONS = ":cloudfront_functions"  # Exclusion marker


def extract_region_from_key(service_key: str) -> str:
    """Extract region from 'region:service' format.

    Args:
        service_key: Key in format "region:service_name"

    Returns:
        Region name

    Raises:
        ValueError: If service_key has invalid format (missing ':')
    """
    if ":" not in service_key:
        raise ValueError(
            f"Invalid service_key format, expected 'region:service': {service_key}"
        )
    return service_key.split(":", 1)[0]


def extract_resource_id(resource_id: str) -> str:
    """Extract clean resource ID from 'region:resource' format.

    Args:
        resource_id: Resource ID potentially prefixed with region

    Returns:
        Clean resource ID without region prefix

    Raises:
        ValueError: If resource_id is empty
    """
    if not resource_id:
        raise ValueError("Empty resource_id in metric data")
    return resource_id.split(":", 1)[1] if ":" in resource_id else resource_id


def _get_metrics_root(section: CloudWatchSection) -> MetricsByService:
    """Safely return CloudWatchMetrics as a normalized dictionary."""
    metrics_root = section.get("CloudWatchMetrics")
    if not isinstance(metrics_root, dict):
        return {}

    normalized: MetricsByService = {}
    for service_key, metrics_list in metrics_root.items():
        if not isinstance(service_key, str) or not isinstance(metrics_list, list):
            continue
        normalized[service_key] = [m for m in metrics_list if isinstance(m, dict)]
    return normalized


def discover_cloudwatch_resources(
    section: dict[str, Any],
    service_filter: str | list[str],
    exclude_filter: str | None = None,
) -> Generator[tuple[str, str], None, None]:
    """Generic discovery yielding (region, resource_id) tuples.

    This function implements the common discovery pattern used by all
    CloudWatch service check plugins.

    Resources come from CloudWatchMetrics and, while monitoring is stopped,
    from CloudWatchKnownResources (last known resources, no metrics), so the
    services do not vanish during the pause.

    Args:
        section: Parsed section containing CloudWatchMetrics
        service_filter: Service key to match (e.g., ":ec2") or list of keys
        exclude_filter: Optional pattern to exclude (e.g., ":cloudfront_functions")

    Yields:
        Tuples of (region, resource_id) for each discovered resource
    """
    if not section:
        return

    metrics_root = dict(_get_metrics_root(section))
    known_resources = section.get("CloudWatchKnownResources")
    if isinstance(known_resources, dict):
        for service_key, resource_ids in known_resources.items():
            if isinstance(service_key, str) and isinstance(resource_ids, list):
                metrics_root.setdefault(service_key, []).extend(
                    {"resource_id": resource_id} for resource_id in resource_ids
                )
    if not metrics_root:
        return

    filters = [service_filter] if isinstance(service_filter, str) else service_filter
    discovered: set[str] = set()

    for service_key, metrics_list in metrics_root.items():
        # Check inclusion filters
        if not any(f in service_key for f in filters):
            continue
        # Check exclusion filter
        if exclude_filter and exclude_filter in service_key:
            continue

        try:
            region = extract_region_from_key(service_key)
        except ValueError:
            # Skip invalid service keys during discovery
            continue

        for metric_data in metrics_list:
            try:
                raw_resource_id = metric_data.get("resource_id")
                if not isinstance(raw_resource_id, str):
                    continue
                if not raw_resource_id:
                    continue
                resource_id = extract_resource_id(raw_resource_id)
                key = f"{region}:{resource_id}"
                if key not in discovered:
                    discovered.add(key)
                    yield region, resource_id
            except ValueError:
                # Skip invalid resource IDs during discovery
                continue


def validate_check_input(
    section: dict[str, Any],
    item: str,
    resource_type: str = "resource",
) -> tuple[str, str] | Result:
    """Validate section and parse item into region and resource_id.

    Args:
        section: Parsed section containing CloudWatchMetrics
        item: Service item in format "region resource_id"
        resource_type: Human-readable resource type for error messages

    Returns:
        Tuple of (region, resource_id) on success, or Result on error
    """
    if not section or "CloudWatchMetrics" not in section:
        return Result(state=State.UNKNOWN, summary="No CloudWatch data available")

    parts = item.split(" ", 1)
    if len(parts) != 2:
        return Result(
            state=State.UNKNOWN, summary=f"Invalid {resource_type} item format: {item}"
        )

    return parts[0], parts[1]


def collect_metrics_for_item(
    section: dict[str, Any],
    target_region: str,
    target_resource: str,
    service_filter: str,
    exclude_filter: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Collect all metrics for a specific resource as metric_key -> metric_data dict.

    This function implements the common metric collection pattern used across
    all check plugins. The key format is "{metric_name}_{stat}".

    Args:
        section: Parsed section containing CloudWatchMetrics
        target_region: Target AWS region
        target_resource: Target resource identifier
        service_filter: Service key pattern to match (e.g., ":elbv2_application")
        exclude_filter: Optional pattern to exclude

    Returns:
        Dictionary mapping metric keys to full metric data dicts
    """
    metrics_found: dict[str, dict[str, Any]] = {}

    if not section:
        return metrics_found

    metrics_root = _get_metrics_root(section)
    if not metrics_root:
        return metrics_found

    for service_key, metrics_list in metrics_root.items():
        # Check service filter
        if service_filter not in service_key:
            continue
        # Check exclusion filter
        if exclude_filter and exclude_filter in service_key:
            continue

        try:
            region = extract_region_from_key(service_key)
        except ValueError:
            continue

        if region != target_region:
            continue

        for metric_data in metrics_list:
            try:
                raw_resource_id = metric_data.get("resource_id")
                if not isinstance(raw_resource_id, str):
                    continue
                if not raw_resource_id:
                    continue
                clean_resource_id = extract_resource_id(raw_resource_id)

                if clean_resource_id != target_resource:
                    continue

                metric_name = metric_data.get("metric_name")
                if not isinstance(metric_name, str):
                    continue
                if not metric_name:
                    continue

                stat = metric_data.get("stat", "Average")
                key = f"{metric_name}_{stat}"
                metrics_found[key] = metric_data
            except ValueError:
                continue

    return metrics_found


def _worst_target_group(
    metrics_found: dict[str, dict[str, Any]],
) -> tuple[str, float, float] | None:
    """Return (target group, unhealthy, total) of the group with the highest unhealthy share.

    Uses the per-target-group values ("parts") the agent sends for ALB/NLB.
    Groups without targets (e.g. deleted ones still listed by AWS) are skipped.

    Returns:
        The worst target group, or None without per-group values (Classic ELB,
        older agent output) or when no group has targets
    """
    healthy_parts = metrics_found.get("HealthyHostCount_Average", {}).get("parts")
    unhealthy_parts = metrics_found.get("UnHealthyHostCount_Average", {}).get("parts")
    if not healthy_parts or not unhealthy_parts:
        return None

    worst: tuple[str, float, float] | None = None
    for target_group in sorted(healthy_parts.keys() | unhealthy_parts.keys()):
        unhealthy = float(unhealthy_parts.get(target_group, 0))
        total = float(healthy_parts.get(target_group, 0)) + unhealthy
        if total <= 0:
            continue
        if worst is None or unhealthy / total > worst[1] / worst[2]:
            worst = (target_group, unhealthy, total)
    return worst


def check_healthy_unhealthy_targets(
    metrics_found: dict[str, dict[str, Any]],
    params: dict[str, Any],
    metric_prefix: str,
    levels_param: str = "unhealthy_targets_levels",
    label_type: str = "Targets",
) -> CheckResult:
    """Check healthy/unhealthy target metrics for load balancers.

    Args:
        metrics_found: Dictionary of collected metrics
        params: Check parameters with threshold settings
        metric_prefix: Prefix for metric names (e.g., "alb", "elb", "nlb")
        levels_param: Parameter key for unhealthy levels (default: "unhealthy_targets_levels")
        label_type: Label for output (e.g., "Targets" or "Hosts")

    With per-target-group values (ALB/NLB) the levels apply to the worst target
    group, so one group that is completely down is not hidden by healthy ones.
    The graphed percentage stays the share over all target groups.

    Yields:
        Results and Metrics for healthy/unhealthy state
    """
    # AWS publishes both together; one missing usually means its fetch failed (the
    # agent shows that error). Treating it as 0 would report 100% healthy or unhealthy.
    if (
        "HealthyHostCount_Average" not in metrics_found
        or "UnHealthyHostCount_Average" not in metrics_found
    ):
        return

    healthy = metrics_found["HealthyHostCount_Average"].get("value", 0)
    unhealthy = metrics_found["UnHealthyHostCount_Average"].get("value", 0)

    if healthy > 0 or unhealthy > 0:
        unhealthy_pct = (unhealthy / (healthy + unhealthy)) * 100
        pct_metric_name = f"{metric_prefix}_unhealthy_{label_type.lower()}_pct"
        worst = _worst_target_group(metrics_found)
        # All target groups healthy: no group worth naming, the total says it all
        if worst is None or worst[1] == 0:
            yield from check_levels(
                unhealthy_pct,
                levels_upper=params.get(levels_param),
                metric_name=pct_metric_name,
                label=f"Unhealthy {label_type}",
                render_func=lambda v: f"{v:.1f}%",
            )
        else:
            target_group, group_unhealthy, group_total = worst
            # "targetgroup/<name>/<id>" -> "<name>"
            group_name = (
                target_group.split("/")[1] if target_group.count("/") == 2 else target_group
            )
            yield from check_levels(
                group_unhealthy / group_total * 100,
                levels_upper=params.get(levels_param),
                label=(
                    f"Unhealthy {label_type} in worst target group {group_name} "
                    f"({group_unhealthy:.0f}/{group_total:.0f})"
                ),
                render_func=lambda v: f"{v:.1f}%",
            )
            yield Metric(pct_metric_name, unhealthy_pct)
        yield Result(
            state=State.OK,
            summary=f"{label_type}: {healthy:.0f} healthy, {unhealthy:.0f} unhealthy",
        )
        yield Metric(f"{metric_prefix}_healthy_{label_type.lower()}", healthy)
        yield Metric(f"{metric_prefix}_unhealthy_{label_type.lower()}", unhealthy)


def check_http_error_codes(
    metrics_found: dict[str, dict[str, Any]],
    error_codes: list[tuple[str, str]],
    metric_prefix: str,
) -> CheckResult:
    """Check HTTP error code metrics.

    Args:
        metrics_found: Dictionary of collected metrics
        error_codes: List of (code_name, label) tuples to check
        metric_prefix: Prefix for metric names (e.g., "alb", "elb")

    Yields:
        Results and Metrics for each error code
    """
    for code, label in error_codes:
        key = f"{code}_Sum"
        if key in metrics_found:
            metric = metrics_found[key]
            value = metric.get("value", 0)
            state = State.OK
            if value > 0:
                if "5XX" in code:
                    state = State.WARN
                elif "4XX" in code and value > 10:
                    state = State.WARN
            yield Result(state=state, summary=f"{label}: {value:.0f}")
            yield Metric(f"{metric_prefix}_{code.lower()}", value)


def check_cpu_utilization(
    metrics_found: dict[str, dict[str, Any]],
    params: dict[str, Any],
    metric_prefix: str,
) -> CheckResult:
    """Check CPU utilization and emit threshold-aware results.

    Args:
        metrics_found: Collected CloudWatch metrics keyed by
            ``<MetricName>_<Stat>`` (for example ``CPUUtilization_Average``).
        params: Check parameters that may include ``cpu_levels`` thresholds.
        metric_prefix: Prefix for emitted Checkmk metric names (for example
            ``ec2`` or ``rds``).

    Yields:
        Checkmk ``Result`` and ``Metric`` objects from ``check_levels`` when
        CPU utilization is present.
    """
    metric = metrics_found.get("CPUUtilization_Average")
    if metric is None:
        return

    value = metric.get("value", 0)
    yield from check_levels(
        value,
        levels_upper=params.get("cpu_levels"),
        metric_name=f"{metric_prefix}_cpu_utilization",
        label="CPU Utilization",
        render_func=lambda v: f"{v:.1f}%",
    )


def emit_sum_metrics(
    metrics_found: dict[str, dict[str, Any]],
    metric_codes: list[str],
    metric_prefix: str,
) -> CheckResult:
    """Emit raw *_Sum metrics as performance data."""
    for code in metric_codes:
        key = f"{code}_Sum"
        if key in metrics_found:
            metric = metrics_found[key]
            value = metric.get("value", 0)
            yield Metric(f"{metric_prefix}_{code.lower()}", value)


# =============================================================================
# Metric Specification Framework
# =============================================================================


class LevelsType(Enum):
    """Type of threshold levels for metrics."""

    UPPER = "upper"  # Warn when value exceeds threshold
    LOWER = "lower"  # Warn when value falls below threshold
    NONE = "none"  # Informational only, no threshold checking


class RenderType(Enum):
    """Predefined render function types."""

    PERCENT = "percent"  # e.g., "45.1%"
    BYTES = "bytes"  # e.g., "1.5 GB"
    BYTES_PER_SECOND = "bytes_per_second"  # e.g., "1.5 MB/s"
    TIMESPAN = "timespan"  # e.g., "5 minutes"
    FLOAT = "float"  # e.g., "123.45"
    INTEGER = "integer"  # e.g., "123"
    MILLISECONDS = "milliseconds"  # e.g., "45.23 ms"
    MILLISECONDS_FROM_SECONDS = "ms_from_s"  # Convert seconds to ms display
    COUNT = "count"  # e.g., "1,234"
    UNITS = "units"  # e.g., "123.4 units"


def get_render_func(render_type: RenderType) -> Callable[[float], str]:
    """Get render function for a render type."""
    render_funcs: dict[RenderType, Callable[[float], str]] = {
        RenderType.PERCENT: lambda v: f"{v:.1f}%",
        RenderType.BYTES: render.bytes,
        RenderType.BYTES_PER_SECOND: render.iobandwidth,
        RenderType.TIMESPAN: render.timespan,
        RenderType.FLOAT: lambda v: f"{v:.2f}",
        RenderType.INTEGER: lambda v: f"{v:.0f}",
        RenderType.MILLISECONDS: lambda v: f"{v:.2f} ms",
        RenderType.MILLISECONDS_FROM_SECONDS: lambda v: f"{v*1000:.2f} ms",
        RenderType.COUNT: lambda v: f"{v:,.0f}",
        RenderType.UNITS: lambda v: f"{v:.1f} units",
    }
    return render_funcs.get(render_type, lambda v: f"{v}")


@dataclass
class MetricSpec:
    """Specification for a single metric to check.

    Attributes:
        metric_key: The key in metrics_found dict (e.g., "CPUUtilization_Average")
        label: Human-readable label for output (e.g., "CPU Utilization")
        metric_name: Metric name for Checkmk (without prefix, e.g., "cpu_utilization")
        param_key: Key in params dict for threshold levels (e.g., "cpu_levels")
        render_type: How to render the value for display
        levels_type: UPPER, LOWER, or NONE for threshold direction
        value_transform: Optional function to transform value before checking
        always_show: If True, show metric even when value is 0 (default: False for NONE)
    """

    metric_key: str
    label: str
    metric_name: str
    param_key: str = ""
    render_type: RenderType = RenderType.FLOAT
    levels_type: LevelsType = LevelsType.UPPER
    value_transform: Callable[[float], float] | None = None
    always_show: bool = False


@dataclass
class InfoMetricSpec:
    """Specification for an informational metric (no threshold checking).

    Attributes:
        metric_key: The key in metrics_found dict
        label: Human-readable label for output
        metric_name: Metric name for Checkmk (without prefix)
        render_type: How to render the value for display
        state_func: Optional function to determine state from value
        value_transform: Optional function to transform value before display
        details_only: Show the value in the service details only, not in the summary
            (a state other than OK from state_func still reaches the summary)
    """

    metric_key: str
    label: str
    metric_name: str
    render_type: RenderType = RenderType.INTEGER
    state_func: Callable[[float], State] | None = None
    value_transform: Callable[[float], float] | None = None
    details_only: bool = False


@dataclass
class CheckConfig:
    """Configuration for a CloudWatch check plugin.

    Attributes:
        service_key: Service filter key (e.g., SERVICE_EC2)
        service_name: Display name for service (e.g., "EC2")
        resource_type: Resource type for error messages (e.g., "instance")
        metric_prefix: Prefix for metric names (e.g., "ec2")
        metric_specs: List of metrics with threshold checking
        info_metrics: List of informational metrics (optional)
        exclude_filter: Optional service key to exclude
        service_key supports a list to combine multiple service filters
        custom_collector: Optional custom metric collection function
        pre_check_hook: Optional hook called before standard metric processing
        details_hook: Optional hook providing details text without extra summary line
        post_check_hook: Optional hook called after standard metric processing
    """

    service_key: str | list[str]
    service_name: str
    resource_type: str
    metric_prefix: str
    metric_specs: list[MetricSpec] = field(default_factory=list)
    info_metrics: list[InfoMetricSpec] = field(default_factory=list)
    exclude_filter: str | None = None
    custom_collector: Callable[..., dict[str, dict[str, Any]]] | None = None
    pre_check_hook: Callable[..., CheckResult] | None = None
    details_hook: Callable[..., str | None] | None = None
    post_check_hook: Callable[..., CheckResult] | None = None


class MetricProcessor:
    """Processes metrics according to specifications."""

    def __init__(
        self,
        metrics_found: dict[str, dict[str, Any]],
        params: dict[str, Any],
        metric_prefix: str,
    ):
        self.metrics_found = metrics_found
        self.params = params
        self.metric_prefix = metric_prefix

    def process_metric(self, spec: MetricSpec) -> CheckResult:
        """Process a single metric with threshold checking."""
        if spec.metric_key not in self.metrics_found:
            return

        metric = self.metrics_found[spec.metric_key]
        value = metric.get("value", 0)

        # Apply value transformation if specified
        if spec.value_transform:
            value = spec.value_transform(value)

        render_func = get_render_func(spec.render_type)
        full_metric_name = f"{self.metric_prefix}_{spec.metric_name}"

        if spec.levels_type == LevelsType.NONE:
            # Informational only
            if value > 0 or spec.always_show:
                yield Result(state=State.OK, summary=f"{spec.label}: {render_func(value)}")
                yield Metric(full_metric_name, value)
        elif spec.levels_type == LevelsType.UPPER:
            yield from check_levels(
                value,
                levels_upper=self.params.get(spec.param_key) if spec.param_key else None,
                metric_name=full_metric_name,
                label=spec.label,
                render_func=render_func,
            )
        elif spec.levels_type == LevelsType.LOWER:
            # Without a datapoint (stopped instance, no requests) the agent sends 0
            # with timestamp None. That is not a real 0: lower levels must not fire.
            if "timestamp" in metric and metric["timestamp"] is None:
                yield Result(state=State.OK, summary=f"{spec.label}: no data")
                return
            yield from check_levels(
                value,
                levels_lower=self.params.get(spec.param_key) if spec.param_key else None,
                metric_name=full_metric_name,
                label=spec.label,
                render_func=render_func,
            )

    def process_info_metric(self, spec: InfoMetricSpec) -> CheckResult:
        """Process an informational metric."""
        if spec.metric_key not in self.metrics_found:
            return

        metric = self.metrics_found[spec.metric_key]
        value = metric.get("value", 0)
        if spec.value_transform:
            value = spec.value_transform(value)
        render_func = get_render_func(spec.render_type)
        full_metric_name = f"{self.metric_prefix}_{spec.metric_name}"

        state = State.OK
        if spec.state_func:
            state = spec.state_func(value)

        text = f"{spec.label}: {render_func(value)}"
        if spec.details_only:
            yield Result(state=state, notice=text)
        else:
            yield Result(state=state, summary=text)
        yield Metric(full_metric_name, value)

    def process_all(
        self,
        specs: list[MetricSpec],
        info_specs: list[InfoMetricSpec] | None = None,
    ) -> CheckResult:
        """Process all metrics according to specifications."""
        for spec in specs:
            yield from self.process_metric(spec)

        if info_specs:
            for info_spec in info_specs:
                yield from self.process_info_metric(info_spec)


def create_cloudwatch_check(config: CheckConfig) -> CheckPlugin:
    """Factory function to create a CloudWatch check plugin.

    Args:
        config: CheckConfig with all plugin configuration

    Returns:
        Configured CheckPlugin instance
    """
    service_key = config.service_key
    exclude_filter = config.exclude_filter

    def discover(section: dict[str, Any]) -> Generator[Service, None, None]:
        """Discover resources from CloudWatch data."""
        for region, resource_id in discover_cloudwatch_resources(
            section, service_key, exclude_filter=exclude_filter
        ):
            yield Service(item=f"{region} {resource_id}")

    def check(item: str, params: dict[str, Any], section: dict[str, Any]) -> CheckResult:
        """Check resource metrics with configurable thresholds."""
        result = validate_check_input(section, item, config.resource_type)
        if isinstance(result, Result):
            yield result
            return
        target_region, target_resource = result

        # Collect metrics
        if config.custom_collector:
            metrics_found = config.custom_collector(section, target_region, target_resource)
        else:
            # Handle single or multiple service keys
            if isinstance(service_key, list):
                metrics_found: dict[str, dict[str, Any]] = {}
                for svc_key in service_key:
                    svc_metrics = collect_metrics_for_item(
                        section, target_region, target_resource, svc_key, exclude_filter
                    )
                    metrics_found.update(svc_metrics)
            else:
                metrics_found = collect_metrics_for_item(
                    section, target_region, target_resource, service_key, exclude_filter
                )

        if not metrics_found:
            if section.get("CloudWatchAPICounter", {}).get("monitoring_stopped", False):
                yield Result(
                    state=State.OK,
                    summary="Free tier limit reached – monitoring paused",
                )
            else:
                yield Result(
                    state=State.UNKNOWN,
                    summary=f"No metrics found for this {config.resource_type}",
                )
            return

        # Call pre-check hook if defined (shown before metrics)
        if config.pre_check_hook:
            yield from config.pre_check_hook(
                metrics_found,
                params,
                config.metric_prefix,
                item=item,
                section=section,
            )

        extra_details: str | None = None
        if config.details_hook:
            extra_details = config.details_hook(
                metrics_found,
                params,
                config.metric_prefix,
                item=item,
                section=section,
            )

        # Process metrics using MetricProcessor.
        # If details_hook is set, append details to the last Result so it appears
        # at the end of the details list.
        processor = MetricProcessor(metrics_found, params, config.metric_prefix)
        processed_entries = list(
            processor.process_all(config.metric_specs, config.info_metrics)
        )
        if extra_details:
            last_result_idx = next(
                (
                    idx
                    for idx in range(len(processed_entries) - 1, -1, -1)
                    if isinstance(processed_entries[idx], Result)
                ),
                -1,
            )
            if last_result_idx >= 0:
                entry = processed_entries[last_result_idx]
                existing_details = getattr(entry, "details", None)
                merged_details = (
                    f"{existing_details}\n\n{extra_details}"
                    if existing_details
                    else extra_details
                )
                if hasattr(entry, "_replace"):
                    try:
                        entry = entry._replace(details=merged_details)
                    except (AttributeError, TypeError, ValueError):
                        entry = Result(
                            state=getattr(entry, "state", State.OK),
                            summary=getattr(entry, "summary", ""),
                            details=merged_details,
                        )
                else:
                    entry = Result(
                        state=getattr(entry, "state", State.OK),
                        summary=getattr(entry, "summary", ""),
                        details=merged_details,
                    )
                processed_entries[last_result_idx] = entry
        yield from processed_entries

        # Call post-check hook if defined
        if config.post_check_hook:
            yield from config.post_check_hook(
                metrics_found,
                params,
                config.metric_prefix,
                item=item,
                section=section,
            )

    plugin_name = f"aws_cloudwatch_{config.metric_prefix}"

    return CheckPlugin(
        name=plugin_name,
        sections=["aws_cloudwatch"],
        service_name=f"{config.service_name} %s",
        discovery_function=discover,
        check_function=check,
        check_ruleset_name=plugin_name,
        check_default_parameters={},
    )
