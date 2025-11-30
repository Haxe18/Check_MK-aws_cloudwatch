#!/usr/bin/env python3
"""Ruleset generator for AWS CloudWatch check parameters.

This module provides factory functions to generate rulesets from
threshold definitions, reducing code duplication across service rulesets.
"""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary
from cmk.rulesets.v1.form_specs import LevelDirection as CMKLevelDirection
from cmk.rulesets.v1.form_specs import (
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
    migrate_to_float_simple_levels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

from ..lib.threshold_types import LevelDirection, ThresholdDef, ThresholdType
from .aws_cloudwatch_helpers import (
    simple_levels_datasize,
    simple_levels_datasize_large,
    simple_levels_float,
    simple_levels_milliseconds,
    simple_levels_percent,
)


def _get_cmk_direction(direction: LevelDirection) -> CMKLevelDirection:
    """Convert internal direction to CMK LevelDirection."""
    return (
        CMKLevelDirection.UPPER
        if direction == LevelDirection.UPPER
        else CMKLevelDirection.LOWER
    )


def _create_form_element(threshold: ThresholdDef) -> DictElement:
    """Create a form element from a threshold definition."""
    direction = _get_cmk_direction(threshold.direction)

    if threshold.threshold_type == ThresholdType.PERCENT:
        return simple_levels_percent(
            threshold.title,
            threshold.help_text,
            direction=direction,
        )
    if threshold.threshold_type == ThresholdType.MILLISECONDS:
        return simple_levels_milliseconds(
            threshold.title,
            threshold.help_text,
            direction=direction,
        )
    if threshold.threshold_type == ThresholdType.SECONDS:
        # Special case: TimeSpan form for seconds
        return DictElement(
            parameter_form=SimpleLevels(
                title=Title(threshold.title),
                help_text=Help(threshold.help_text),
                form_spec_template=TimeSpan(
                    displayed_magnitudes=[TimeMagnitude.SECOND, TimeMagnitude.MINUTE],
                ),
                level_direction=direction,
                prefill_fixed_levels=DefaultValue((0.0, 0.0)),
                migrate=migrate_to_float_simple_levels,
            ),
            required=False,
        )
    if threshold.threshold_type == ThresholdType.DATASIZE:
        return simple_levels_datasize(
            threshold.title,
            threshold.help_text,
            direction=direction,
        )
    if threshold.threshold_type == ThresholdType.DATASIZE_LARGE:
        return simple_levels_datasize_large(
            threshold.title,
            threshold.help_text,
            direction=direction,
        )
    return simple_levels_float(
        threshold.title,
        threshold.help_text,
        unit=threshold.unit,
        direction=direction,
    )


def generate_parameter_form(
    service_name: str,
    thresholds: list[ThresholdDef],
    help_suffix: str = "",
    extra_elements: dict | None = None,
) -> Dictionary:
    """Generate a parameter form from threshold definitions.

    Args:
        service_name: Display name of the service (e.g., "EC2", "RDS")
        thresholds: List of threshold definitions
        help_suffix: Optional additional help text
        extra_elements: Optional additional DictElement entries to add

    Returns:
        Dictionary form specification
    """
    base_help = (
        f"Configure warning and critical thresholds for {service_name} metrics. "
        "Leave empty to disable threshold checking for that metric."
    )
    if help_suffix:
        base_help = f"{base_help} {help_suffix}"

    elements = {threshold.key: _create_form_element(threshold) for threshold in thresholds}
    if extra_elements:
        elements.update(extra_elements)

    return Dictionary(
        title=Title(f"AWS {service_name} Thresholds"),
        help_text=Help(base_help),
        elements=elements,
    )


def generate_rule_spec(
    service_key: str,
    service_name: str,
    thresholds: list[ThresholdDef],
    help_suffix: str = "",
    extra_elements: dict | None = None,
) -> CheckParameters:
    """Generate a complete rule specification from threshold definitions.

    Args:
        service_key: Service key for the ruleset name (e.g., "ec2", "rds")
        service_name: Display name of the service (e.g., "EC2", "RDS")
        thresholds: List of threshold definitions
        help_suffix: Optional additional help text for the form
        extra_elements: Optional additional DictElement entries to add

    Returns:
        CheckParameters rule specification
    """
    ruleset_name = f"aws_cloudwatch_{service_key}"

    def _parameter_form() -> Dictionary:
        return generate_parameter_form(service_name, thresholds, help_suffix, extra_elements)

    return CheckParameters(
        name=ruleset_name,
        title=Title(f"AWS CloudWatch {service_name}"),
        topic=Topic.CLOUD,
        parameter_form=_parameter_form,
        condition=HostCondition(),
    )
