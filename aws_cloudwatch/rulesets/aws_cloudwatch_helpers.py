#!/usr/bin/env python3
"""Shared helper functions for AWS CloudWatch ruleset form specs.

This module provides factory functions for creating common SimpleLevels
form elements to reduce code duplication across ruleset definitions.
"""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DefaultValue,
    DictElement,
    Float,
    LevelDirection,
    SIMagnitude,
    SimpleLevels,
    migrate_to_float_simple_levels,
)


def simple_levels_percent(
    title: str,
    help_text: str,
    direction: LevelDirection = LevelDirection.UPPER,
) -> DictElement:
    """Create a SimpleLevels DictElement for percentage values.

    Args:
        title: The title for the form element.
        help_text: Help text describing the threshold.
        direction: UPPER for max thresholds, LOWER for min thresholds.

    Returns:
        DictElement configured for percentage thresholds.
    """
    return DictElement(
        parameter_form=SimpleLevels(
            title=Title(title),
            help_text=Help(help_text),
            form_spec_template=Float(unit_symbol="%"),
            level_direction=direction,
            prefill_fixed_levels=DefaultValue((0.0, 0.0)),
            migrate=migrate_to_float_simple_levels,
        ),
        required=False,
    )


def simple_levels_float(
    title: str,
    help_text: str,
    unit: str = "",
    direction: LevelDirection = LevelDirection.UPPER,
) -> DictElement:
    """Create a SimpleLevels DictElement for float values.

    Args:
        title: The title for the form element.
        help_text: Help text describing the threshold.
        unit: Optional unit symbol (e.g., "ms", "ops").
        direction: UPPER for max thresholds, LOWER for min thresholds.

    Returns:
        DictElement configured for float thresholds.
    """
    return DictElement(
        parameter_form=SimpleLevels(
            title=Title(title),
            help_text=Help(help_text),
            form_spec_template=Float(unit_symbol=unit) if unit else Float(),
            level_direction=direction,
            prefill_fixed_levels=DefaultValue((0.0, 0.0)),
            migrate=migrate_to_float_simple_levels,
        ),
        required=False,
    )


def simple_levels_milliseconds(
    title: str,
    help_text: str,
    direction: LevelDirection = LevelDirection.UPPER,
) -> DictElement:
    """Create a SimpleLevels DictElement for millisecond values.

    Args:
        title: The title for the form element.
        help_text: Help text describing the threshold.
        direction: UPPER for max thresholds, LOWER for min thresholds.

    Returns:
        DictElement configured for millisecond thresholds.
    """
    return simple_levels_float(title, help_text, "ms", direction)


def simple_levels_datasize(
    title: str,
    help_text: str,
    magnitudes: list[SIMagnitude] | None = None,
    direction: LevelDirection = LevelDirection.UPPER,
) -> DictElement:
    """Create a SimpleLevels DictElement for data size values.

    Args:
        title: The title for the form element.
        help_text: Help text describing the threshold.
        magnitudes: List of magnitudes to display (default: MEGA, GIGA).
        direction: UPPER for max thresholds, LOWER for min thresholds.

    Returns:
        DictElement configured for data size thresholds.
    """
    if magnitudes is None:
        magnitudes = [SIMagnitude.MEGA, SIMagnitude.GIGA]

    return DictElement(
        parameter_form=SimpleLevels(
            title=Title(title),
            help_text=Help(help_text),
            form_spec_template=DataSize(displayed_magnitudes=magnitudes),
            level_direction=direction,
            prefill_fixed_levels=DefaultValue((0.0, 0.0)),
            migrate=migrate_to_float_simple_levels,
        ),
        required=False,
    )


def simple_levels_datasize_large(
    title: str,
    help_text: str,
    direction: LevelDirection = LevelDirection.UPPER,
) -> DictElement:
    """Create a SimpleLevels DictElement for large data size values (GB/TB).

    Args:
        title: The title for the form element.
        help_text: Help text describing the threshold.
        direction: UPPER for max thresholds, LOWER for min thresholds.

    Returns:
        DictElement configured for large data size thresholds.
    """
    return simple_levels_datasize(
        title,
        help_text,
        magnitudes=[SIMagnitude.MEGA, SIMagnitude.GIGA, SIMagnitude.TERA],
        direction=direction,
    )
