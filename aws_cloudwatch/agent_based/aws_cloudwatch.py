#!/usr/bin/env python3
"""Checkmk agent-based check plugin for AWS CloudWatch Monitoring.

This module provides the shared AgentSection (parse function) and
the API Counter check plugin. Service-specific check plugins are
in separate files (aws_cloudwatch_lambda.py, etc.).
"""

import json
from calendar import monthrange
from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from cmk.agent_based.v2 import AgentSection, CheckPlugin, Metric, Result, Service, State

APIErrorEntry = dict[str, Any]
CloudWatchSection = dict[str, Any]


@dataclass(frozen=True)
class APICounterCalculation:
    """Holds normalized values and derived forecast fields."""

    free_tier_limit: int
    cache_ttl: int
    aws_total: int
    calls_per_check: float
    services_count: int
    force_over_limit: bool
    warn_threshold: int
    crit_threshold: int
    days_remaining: float
    checks_per_hour: float
    calls_per_day: int
    remaining_calls: int
    forecast: int
    forecast_percentage: float
    weighted_calls_per_check_by_service: dict[str, dict[str, float]]
    weighted_calls_per_check_overridden_total: float
    weighted_calls_per_check_default_total: float
    weighted_calls_per_check_overridden_by_service: dict[str, float]
    weighted_calls_per_check_default_by_service: dict[str, float]


def _default_section() -> CloudWatchSection:
    """Builds an empty, normalized CloudWatch section.

    Returns:
        A section dictionary with all expected top-level keys.
    """
    return {
        "CloudWatchMetrics": {},
        "CloudWatchAPICounter": {},
        "CloudWatchAPIConfig": {},
        "CloudWatchErrors": [],
        "CloudWatchEmptyServices": {},
        "CloudWatchResourceMetadata": {},
        "CloudWatchKnownResources": {},
    }


def _as_int(value: Any, default: int = 0) -> int:
    """Converts ``value`` to ``int``.

    Args:
        value: Arbitrary input value.
        default: Fallback used when conversion fails.

    Returns:
        The converted integer or ``default``.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    """Converts ``value`` to ``float``.

    Args:
        value: Arbitrary input value.
        default: Fallback used when conversion fails.

    Returns:
        The converted float or ``default``.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_positive_int(value: Any) -> int | None:
    """Converts ``value`` to a positive integer.

    Args:
        value: Arbitrary input value.

    Returns:
        The converted integer when ``> 0``; otherwise ``None``.
    """
    converted = _as_int(value, default=0)
    return converted if converted > 0 else None


def _as_bool(value: Any) -> bool:
    """Converts input to ``bool`` with permissive string handling.

    Args:
        value: Arbitrary input value.

    Returns:
        ``True`` or ``False``.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def parse_aws_cloudwatch(string_table: list[list[str]]) -> CloudWatchSection:
    """Parses special-agent output into a normalized section structure.

    Args:
        string_table: Raw Checkmk string table.

    Returns:
        A normalized ``CloudWatchSection`` dictionary.
    """
    raw = "".join(line for sublist in string_table for line in sublist)

    if not raw.strip():
        return _default_section()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        fallback = _default_section()
        fallback["CloudWatchAPICounter"] = {"error": f"JSON decode error: {error}"}
        return fallback

    if not isinstance(parsed, dict):
        fallback = _default_section()
        fallback["CloudWatchAPICounter"] = {"error": "Parsed JSON payload is not an object"}
        return fallback

    section = _default_section()
    metrics = parsed.get("CloudWatchMetrics")
    api_counter = parsed.get("CloudWatchAPICounter")
    api_config = parsed.get("CloudWatchAPIConfig")
    errors = parsed.get("CloudWatchErrors")
    empty_services = parsed.get("CloudWatchEmptyServices")
    metadata = parsed.get("CloudWatchResourceMetadata")
    known_resources = parsed.get("CloudWatchKnownResources")

    if isinstance(metrics, dict):
        section["CloudWatchMetrics"] = metrics
    if isinstance(api_counter, dict):
        section["CloudWatchAPICounter"] = api_counter
    if isinstance(api_config, dict):
        section["CloudWatchAPIConfig"] = api_config
    if isinstance(errors, list):
        section["CloudWatchErrors"] = [e for e in errors if isinstance(e, dict)]
    if isinstance(empty_services, dict):
        section["CloudWatchEmptyServices"] = {
            str(region): [str(service) for service in services]
            for region, services in empty_services.items()
            if isinstance(services, list)
        }
    if isinstance(metadata, dict):
        section["CloudWatchResourceMetadata"] = metadata
    if isinstance(known_resources, dict):
        section["CloudWatchKnownResources"] = {
            str(service_key): [str(resource_id) for resource_id in resource_ids]
            for service_key, resource_ids in known_resources.items()
            if isinstance(resource_ids, list)
        }

    return section


# ===== CloudWatch API Counter Discovery & Check =====


def discover_aws_cloudwatch_api_counter(
    section: CloudWatchSection,
) -> Generator[Service, None, None]:
    """Discovers the CloudWatch API counter service.

    Args:
        section: Parsed CloudWatch section.

    Yields:
        A single itemless service when counter payload exists.
    """
    if not section or "CloudWatchAPICounter" not in section:
        return

    counter_data = section["CloudWatchAPICounter"]

    # Always discover if any counter payload exists so agent-side errors
    # are visible as a check result instead of being silently hidden.
    if counter_data:
        yield Service()


def _fmt(number: int) -> str:
    """Formats integers with thousands separators.

    Args:
        number: Integer value to format.

    Returns:
        Human-readable number string using dot as separator.
    """
    return f"{number:,}".replace(",", ".")


def _build_counter_calculation(
    section: dict[str, Any],
) -> APICounterCalculation | Result:
    """Validates API counter payload and computes forecast values.

    Args:
        section: Parsed section mapping.

    Returns:
        A populated ``APICounterCalculation`` on success,
        otherwise an UNKNOWN/CRIT ``Result`` describing the error.
    """
    counter_data = section.get("CloudWatchAPICounter")
    if not isinstance(counter_data, dict):
        return Result(state=State.UNKNOWN, summary="No CloudWatch API counter data available")

    config = section.get("CloudWatchAPIConfig")
    if not isinstance(config, dict):
        config = {}

    if "error" in counter_data:
        return Result(state=State.CRIT, summary=f"Error: {counter_data['error']}")

    free_tier_limit = _as_positive_int(counter_data.get("free_tier_limit"))
    if free_tier_limit is None:
        return Result(
            state=State.UNKNOWN,
            summary="Missing or invalid 'free_tier_limit' in agent output",
        )

    cache_ttl = _as_positive_int(config.get("cache_ttl"))
    if cache_ttl is None:
        return Result(
            state=State.UNKNOWN,
            summary="Missing or invalid 'cache_ttl' in agent output",
        )

    aws_total = max(0, _as_int(counter_data.get("aws_monthly_total"), default=0))
    calls_per_check = max(0.0, _as_float(config.get("calls_per_check"), default=0.0))
    services_count = max(0, _as_int(config.get("services_count"), default=0))
    force_over_limit = _as_bool(config.get("force_over_limit", False))
    warn_threshold = max(0, min(100, _as_int(config.get("warning_threshold", 80), default=80)))
    crit_threshold = max(
        0, min(100, _as_int(config.get("critical_threshold", 90), default=90))
    )
    weighted_by_service_raw = config.get("weighted_calls_per_check_by_service", {})
    weighted_by_service: dict[str, dict[str, float]] = {}
    if isinstance(weighted_by_service_raw, dict):
        for service_name, entry in weighted_by_service_raw.items():
            if not isinstance(service_name, str) or not isinstance(entry, dict):
                continue
            weighted_by_service[service_name] = {
                "refresh_ttl": max(1.0, _as_float(entry.get("refresh_ttl"), default=0.0)),
                "refresh_ratio": max(
                    0.0,
                    min(1.0, _as_float(entry.get("refresh_ratio"), default=0.0)),
                ),
                "last_refresh_api_calls": max(
                    0.0,
                    _as_float(entry.get("last_refresh_api_calls"), default=0.0),
                ),
                "weighted_calls_per_check": max(
                    0.0,
                    _as_float(entry.get("weighted_calls_per_check"), default=0.0),
                ),
            }
    weighted_overridden_total = max(
        0.0,
        _as_float(config.get("weighted_calls_per_check_overridden_total"), default=0.0),
    )
    weighted_default_total = max(
        0.0,
        _as_float(config.get("weighted_calls_per_check_default_total"), default=0.0),
    )
    overridden_by_service_raw = config.get(
        "weighted_calls_per_check_overridden_by_service", {}
    )
    overridden_by_service: dict[str, float] = {}
    if isinstance(overridden_by_service_raw, dict):
        for service_name, value in overridden_by_service_raw.items():
            if isinstance(service_name, str):
                overridden_by_service[service_name] = max(
                    0.0,
                    _as_float(value, default=0.0),
                )
    default_by_service_raw = config.get("weighted_calls_per_check_default_by_service", {})
    default_by_service: dict[str, float] = {}
    if isinstance(default_by_service_raw, dict):
        for service_name, value in default_by_service_raw.items():
            if isinstance(service_name, str):
                default_by_service[service_name] = max(
                    0.0,
                    _as_float(value, default=0.0),
                )

    # Calculate remaining days in month, including the rest of today
    now = datetime.now(timezone.utc)
    days_in_month = monthrange(now.year, now.month)[1]
    month_end = datetime(now.year, now.month, days_in_month, tzinfo=timezone.utc) + timedelta(
        days=1
    )
    days_remaining = (month_end - now).total_seconds() / 86400

    # Calculate daily API calls
    checks_per_hour = 3600.0 / cache_ttl
    calls_per_day = int(round(calls_per_check * checks_per_hour * 24))
    remaining_calls = int(round(days_remaining * calls_per_day))
    forecast = aws_total + remaining_calls
    forecast_percentage = (forecast / free_tier_limit) * 100

    return APICounterCalculation(
        free_tier_limit=free_tier_limit,
        cache_ttl=cache_ttl,
        aws_total=aws_total,
        calls_per_check=calls_per_check,
        services_count=services_count,
        force_over_limit=force_over_limit,
        warn_threshold=warn_threshold,
        crit_threshold=crit_threshold,
        days_remaining=days_remaining,
        checks_per_hour=checks_per_hour,
        calls_per_day=calls_per_day,
        remaining_calls=remaining_calls,
        forecast=forecast,
        forecast_percentage=forecast_percentage,
        weighted_calls_per_check_by_service=weighted_by_service,
        weighted_calls_per_check_overridden_total=weighted_overridden_total,
        weighted_calls_per_check_default_total=weighted_default_total,
        weighted_calls_per_check_overridden_by_service=overridden_by_service,
        weighted_calls_per_check_default_by_service=default_by_service,
    )


def _counter_state(calc: APICounterCalculation) -> State:
    """Determines state from thresholds and forecast percentage.

    Args:
        calc: Calculated API counter values.

    Returns:
        Checkmk state for the main API forecast result.
    """
    if calc.force_over_limit:
        return State.OK
    if calc.forecast_percentage >= calc.crit_threshold:
        return State.CRIT
    if calc.forecast_percentage >= calc.warn_threshold:
        return State.WARN
    return State.OK


def _build_counter_result(calc: APICounterCalculation) -> Result:
    """Builds the main check result for API forecast usage.

    Args:
        calc: Calculated API counter values.

    Returns:
        Main check result with summary and detailed formula output.
    """
    metrics_per_service = (
        calc.calls_per_check / calc.services_count if calc.services_count > 0 else 0
    )
    calls_per_check_display = str(round(calc.calls_per_check))
    metrics_per_service_display = str(round(metrics_per_service))
    checks_per_hour_display = f"{calc.checks_per_hour:.3f}".rstrip("0").rstrip(".")

    if calc.force_over_limit:
        summary = f"Monthly forecast: {_fmt(calc.forecast)} API calls"
    else:
        summary = (
            f"Monthly forecast: {_fmt(calc.forecast)} API calls "
            f"({calc.forecast_percentage:.1f}% of free tier)"
        )
    summary += f" | {calc.services_count} services, TTL {calc.cache_ttl}s"

    details = "Calculation:\n"
    details += f"  Currently consumed:     {_fmt(calc.aws_total)} (from AWS)\n"
    details += f"  Remaining days:         {calc.days_remaining:.1f}\n"
    details += (
        f"  Weighted calls/check:   {calls_per_check_display} "
        f"({calc.services_count} services x {metrics_per_service_display} metrics)\n"
    )
    breakdown_items = sorted(
        calc.weighted_calls_per_check_by_service.items(),
        key=lambda item: item[1].get("weighted_calls_per_check", 0.0),
        reverse=True,
    )

    def _format_service_totals(service_totals: dict[str, float]) -> str:
        if not service_totals:
            return "0"
        parts = [
            f"{service}={round(value)}"
            for service, value in sorted(
                service_totals.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]
        return ", ".join(parts)

    if breakdown_items:
        details += "  Weighted calls/check breakdown:\n"
        for service_name, entry in breakdown_items:
            weighted = str(round(entry.get("weighted_calls_per_check", 0.0)))
            base_calls = str(round(entry.get("last_refresh_api_calls", 0.0)))
            ratio = f"{entry.get('refresh_ratio', 0.0):.5f}".rstrip("0").rstrip(".")
            ttl_value = int(entry.get("refresh_ttl", calc.cache_ttl))
            details += (
                f"    - {service_name}: {weighted} "
                f"(interval={ttl_value}s, factor={ratio}, base_calls={base_calls})\n"
            )
        overridden_total_display = str(round(calc.weighted_calls_per_check_overridden_total))
        default_total_display = str(round(calc.weighted_calls_per_check_default_total))
        details += (
            "  Overridden TTL total:  "
            f"{overridden_total_display} "
            f"({_format_service_totals(calc.weighted_calls_per_check_overridden_by_service)})\n"
        )
        details += (
            "  Default TTL total:     "
            f"{default_total_display} "
            f"({_format_service_totals(calc.weighted_calls_per_check_default_by_service)})\n"
        )
    details += (
        f"  Checks per hour:        {checks_per_hour_display} "
        f"(3600 / {calc.cache_ttl}s TTL)\n"
    )
    details += (
        f"  Calls per day:          {calls_per_check_display} x {checks_per_hour_display} "
        f"x 24 = {_fmt(calc.calls_per_day)}\n"
    )
    details += (
        f"  Expected remaining:     {calc.days_remaining:.1f} x {_fmt(calc.calls_per_day)} "
        f"= {_fmt(calc.remaining_calls)}\n"
    )
    details += "  ─────────────────────────────────────────────\n"
    if calc.force_over_limit:
        details += (
            f"  Forecast end of month:  {_fmt(calc.aws_total)} + "
            f"{_fmt(calc.remaining_calls)} = {_fmt(calc.forecast)}"
        )
    else:
        details += (
            f"  Forecast end of month:  {_fmt(calc.aws_total)} + "
            f"{_fmt(calc.remaining_calls)} = {_fmt(calc.forecast)} "
            f"({calc.forecast_percentage:.1f}% of free tier)"
        )

    return Result(state=_counter_state(calc), summary=summary, details=details)


def _emit_error_result(errors: Any) -> Generator[Result, None, None]:
    """Emits a warning result for collected service errors.

    Args:
        errors: Raw ``CloudWatchErrors`` payload.

    Yields:
        One WARN result if valid error entries are present.
    """
    if not isinstance(errors, list):
        return

    valid_errors = [error for error in errors if isinstance(error, dict)]
    if not valid_errors:
        return

    def _summary_line(error_entry: APIErrorEntry) -> str:
        base = (
            f"{error_entry.get('service', 'unknown')}/{error_entry.get('region', 'unknown')}"
        )
        hint = error_entry.get("hint")
        return f"{base} (Required: {hint})" if hint else base

    def _detail_line(error_entry: APIErrorEntry) -> str:
        base = (
            f"  [{error_entry.get('category', '?')}] "
            f"{error_entry.get('service', '?')}/{error_entry.get('region', '?')}: "
            f"{error_entry.get('message', '?')}"
        )
        hint = error_entry.get("hint")
        return f"{base}\n    -> Required IAM permission: {hint}" if hint else base

    error_services = ", ".join(_summary_line(error_entry) for error_entry in valid_errors[:3])
    error_details = "\n".join(_detail_line(error_entry) for error_entry in valid_errors)
    yield Result(
        state=State.WARN,
        summary=f"{len(valid_errors)} errors: {error_services}"
        + (" ..." if len(valid_errors) > 3 else ""),
        details=f"Errors:\n{error_details}",
    )


def _emit_empty_services_result(
    empty_services: Any,
) -> Generator[Result, None, None]:
    """Emits an informational result for services without resources.

    Args:
        empty_services: Raw ``CloudWatchEmptyServices`` payload.

    Yields:
        One OK result with per-region service list.
    """
    if not isinstance(empty_services, dict) or not empty_services:
        return

    normalized = {
        str(region): [str(service) for service in services]
        for region, services in empty_services.items()
        if isinstance(services, list)
    }
    if not normalized:
        return

    total_empty = sum(len(services) for services in normalized.values())
    empty_details = "\n".join(
        f"  {region}: {', '.join(services)}" for region, services in normalized.items()
    )
    yield Result(
        state=State.OK,
        summary="{} services without resources (check IAM permissions if unexpected)".format(
            total_empty
        ),
        details=f"Empty services by region:\n{empty_details}",
    )


def check_aws_cloudwatch_api_counter(
    section: CloudWatchSection,
) -> Generator[Result | Metric, None, None]:
    """Checks CloudWatch API forecast and emits related metrics.

    Args:
        _params: Ruleset parameters (unused; thresholds come from agent payload).
        section: Parsed CloudWatch section.

    Yields:
        Error summary result (if present), main forecast result, and forecast metrics.
    """
    calculation = _build_counter_calculation(section)
    if isinstance(calculation, Result):
        yield calculation
        return

    counter_data = section.get("CloudWatchAPICounter", {})
    if isinstance(counter_data, dict) and _as_bool(
        counter_data.get("monitoring_stopped", False)
    ):
        yield Result(
            state=State.CRIT,
            summary="Monitoring stopped: free tier limit reached, no API calls until next month",
        )

    yield from _emit_error_result(section.get("CloudWatchErrors", []))
    yield _build_counter_result(calculation)
    yield Metric(
        "aws_cw_api_forecast_usage",
        calculation.forecast,
        boundaries=(0, calculation.free_tier_limit),
    )
    yield Metric("aws_cw_api_limit_usage", calculation.free_tier_limit)
    yield Metric(
        "aws_cw_api_forecast_percent",
        calculation.forecast_percentage,
        boundaries=(0, 100),
    )
    yield from _emit_empty_services_result(section.get("CloudWatchEmptyServices", {}))


# ===== CMK Plugin Definitions =====

agent_section_aws_cloudwatch = AgentSection(
    name="aws_cloudwatch",
    parse_function=parse_aws_cloudwatch,
)

check_plugin_aws_cloudwatch_api_counter = CheckPlugin(
    name="aws_cloudwatch_api_counter",
    sections=["aws_cloudwatch"],
    service_name="CloudWatch API Status",
    discovery_function=discover_aws_cloudwatch_api_counter,
    check_function=check_aws_cloudwatch_api_counter,
)
