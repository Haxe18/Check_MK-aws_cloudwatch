#!/usr/bin/env python3
"""WATO ruleset for AWS CloudWatch CloudFront check parameters."""

from cmk.rulesets.v1 import Help, Label
from cmk.rulesets.v1.form_specs import BooleanChoice, DefaultValue, DictElement

from ..lib.threshold_types import (
    LevelDirection,
    datasize_large_threshold,
    milliseconds_threshold,
    percent_threshold,
)
from .ruleset_generator import generate_rule_spec

# CloudFront threshold definitions
CLOUDFRONT_THRESHOLDS = [
    percent_threshold(
        "total_error_rate_levels",
        "Total Error Rate (%)",
        "Alert when total error rate exceeds these thresholds.",
    ),
    percent_threshold(
        "error_4xx_rate_levels",
        "4xx Error Rate (%)",
        "Alert when 4xx error rate exceeds these thresholds.",
    ),
    percent_threshold(
        "error_5xx_rate_levels",
        "5xx Error Rate (%)",
        "Alert when 5xx error rate exceeds these thresholds. "
        "5xx errors indicate server-side issues.",
    ),
    percent_threshold(
        "cache_hit_rate_levels",
        "Cache Hit Rate (%)",
        "Alert when cache hit rate falls below these thresholds. "
        "Low cache hit rate means more origin requests.",
        direction=LevelDirection.LOWER,
    ),
    milliseconds_threshold(
        "origin_latency_levels",
        "Origin Latency (ms)",
        "Alert when origin latency exceeds these thresholds.",
    ),
    datasize_large_threshold(
        "bytes_downloaded_levels",
        "Bytes Downloaded",
        "Alert when bytes downloaded exceeds these thresholds.",
    ),
    datasize_large_threshold(
        "bytes_uploaded_levels",
        "Bytes Uploaded",
        "Alert when bytes uploaded exceeds these thresholds.",
    ),
]

_CLOUDFRONT_EXTRA_ELEMENTS = {
    "show_description": DictElement(
        parameter_form=BooleanChoice(
            label=Label("Show Comment from AWS as description"),
            help_text=Help(
                "Show the CloudFront distribution's Comment field as description in the service summary."
            ),
            prefill=DefaultValue(False),
        ),
        required=True,
    ),
    "show_url": DictElement(
        parameter_form=BooleanChoice(
            label=Label("Show URL from AWS (alias or CloudFront domain)"),
            help_text=Help(
                "Show the distribution's URL (first alias/CNAME, fallback to CloudFront domain) "
                "as a clickable link in the service summary."
            ),
            prefill=DefaultValue(False),
        ),
        required=True,
    ),
}

rule_spec_aws_cloudwatch_cloudfront = generate_rule_spec(
    "cloudfront",
    "CloudFront",
    CLOUDFRONT_THRESHOLDS,
    help_suffix="Note: CloudFront metrics are only available in us-east-1.",
    extra_elements=_CLOUDFRONT_EXTRA_ELEMENTS,
)
