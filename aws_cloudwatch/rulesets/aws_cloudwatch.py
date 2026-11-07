#!/usr/bin/env python3
"""WATO ruleset for AWS CloudWatch Monitoring special agent configuration.

This module defines the web UI configuration form for the special agent.
It allows users to configure:
    - AWS credentials (Access Key, Secret Key)
    - CloudWatch monitoring with multi-region support
    - Per-region service selection
    - API usage thresholds

The configuration is stored in Checkmk's WATO system and used to
generate command-line arguments for the special agent.
"""

#: AWS region choices imported from Checkmk's built-in constants.
#: Provides all 31 AWS regions with human-readable names.
from cmk.plugins.aws.constants import (
    AWSRegions,  # pylint: disable=cmk-module-layer-violation
)
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    List,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    String,
    migrate_to_password,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic

from ..lib.threshold_types import CLOUDWATCH_FREE_TIER_LIMIT


def format_limit(limit_value: int) -> str:
    if limit_value >= 1_000_000:
        return f"{limit_value // 1_000_000}M"
    if limit_value >= 1_000:
        return f"{limit_value // 1_000}K"
    return str(limit_value)


_FREE_TIER = format_limit(CLOUDWATCH_FREE_TIER_LIMIT)


def _validate_multiple_of_60(value: int) -> None:
    """Validate that Cache TTL is a multiple of 60 seconds.

    AWS CloudWatch API requires the Period parameter to be a multiple of 60.
    This validator ensures users don't enter invalid values in the WATO form.

    Args:
        value: The cache TTL value in seconds

    Raises:
        validators.ValidationError: If value is not a multiple of 60
    """
    if value % 60 != 0:
        suggested = ((value + 59) // 60) * 60
        raise validators.ValidationError(
            Message(
                "Value must be a multiple of 60 seconds (AWS CloudWatch API requirement). "
                "Got %s, try %s instead."
            )
            % (str(value), str(suggested))
        )


def _valuespec_special_agents_aws_cloudwatch() -> Dictionary:
    """Create the form specification for the special agent configuration.

    Builds a Dictionary form with all configuration options
    for AWS CloudWatch monitoring.

    Returns:
        Dictionary: Form specification with elements for:
            - aws_access_key_id: AWS Access Key
            - aws_secret_access_key: AWS Secret Key (encrypted)
            - cloudwatch_regions: Multi-region service configuration
            - cloudwatch_cache_ttl: Cache duration for API responses
            - cloudwatch_api_warn: Warning threshold for API usage
            - cloudwatch_api_crit: Critical threshold for API usage
    """
    return Dictionary(
        title=Title("AWS CloudWatch Monitoring Configuration"),
        elements={
            "aws_access_key_id": DictElement(
                parameter_form=String(
                    title=Title("AWS Access Key ID"),
                ),
                required=True,
            ),
            "aws_secret_access_key": DictElement(
                parameter_form=Password(
                    title=Title("AWS Secret Access Key"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    migrate=migrate_to_password,
                ),
                required=True,
            ),
            "cloudwatch_regions": DictElement(
                parameter_form=List(
                    title=Title("CloudWatch Regions Configuration"),
                    help_text=Help(
                        "Configure multiple AWS regions to monitor. Each region can monitor different services. "
                        "Note: CloudFront and CloudFront Functions MUST use us-east-1 (AWS requirement). "
                        "Lambda@Edge metrics appear in the region where the function was created."
                    ),
                    element_template=Dictionary(
                        elements={
                            "region_name": DictElement(
                                parameter_form=CascadingSingleChoice(
                                    title=Title("AWS Region"),
                                    elements=[
                                        CascadingSingleChoiceElement(
                                            name=region_id.replace("-", "_"),
                                            title=Title(f"{region_name} - {region_id}"),
                                            parameter_form=FixedValue(value=region_id),
                                        )
                                        for region_id, region_name in AWSRegions
                                    ],
                                    prefill=DefaultValue("us_east_1"),
                                ),
                                required=True,
                            ),
                            "services": DictElement(
                                parameter_form=MultipleChoice(
                                    title=Title("Services to Monitor in This Region"),
                                    help_text=Help(
                                        "Select which services to monitor in this region. "
                                        "CloudFront and CloudFront Functions are only available in us-east-1."
                                    ),
                                    elements=[
                                        # CloudFront (us-east-1 only)
                                        MultipleChoiceElement(
                                            name="cloudfront",
                                            title=Title(
                                                "CloudFront (Requests, Bytes, Error Rates) - us-east-1 only"
                                            ),
                                        ),
                                        MultipleChoiceElement(
                                            name="cloudfront_functions",
                                            title=Title(
                                                "CloudFront Functions (Lightweight JS) - us-east-1 only"
                                            ),
                                        ),
                                        # Compute
                                        MultipleChoiceElement(
                                            name="ec2",
                                            title=Title(
                                                "EC2 (CPU, Network, Disk, Status Checks)"
                                            ),
                                        ),
                                        # Serverless
                                        MultipleChoiceElement(
                                            name="aws_lambda",
                                            title=Title(
                                                "Lambda (Invocations, Errors, Duration) - includes Lambda@Edge"
                                            ),
                                        ),
                                        MultipleChoiceElement(
                                            name="lambda_insights",
                                            title=Title(
                                                "Lambda Insights (Memory, CPU Time, Network) - "
                                                "needs the Lambda Insights extension"
                                            ),
                                        ),
                                        # Database
                                        MultipleChoiceElement(
                                            name="rds",
                                            title=Title(
                                                "RDS (CPU, Connections, Storage, IOPS, Latency, Replica Lag)"
                                            ),
                                        ),
                                        MultipleChoiceElement(
                                            name="dynamodb",
                                            title=Title(
                                                "DynamoDB (Read/Write Capacity, Throttles, Latency)"
                                            ),
                                        ),
                                        # Storage
                                        MultipleChoiceElement(
                                            name="ebs",
                                            title=Title(
                                                "EBS (Volume Ops, Throughput, Burst Balance)"
                                            ),
                                        ),
                                        MultipleChoiceElement(
                                            name="s3",
                                            title=Title("S3 (Bucket Size, Object Count)"),
                                        ),
                                        # Networking
                                        MultipleChoiceElement(
                                            name="elb",
                                            title=Title(
                                                "ELB Classic (Requests, Health, Latency)"
                                            ),
                                        ),
                                        MultipleChoiceElement(
                                            name="elbv2_application",
                                            title=Title(
                                                "Application Load Balancer (ALB) - Requests, Response Time, HTTP Codes"
                                            ),
                                        ),
                                        MultipleChoiceElement(
                                            name="elbv2_network",
                                            title=Title(
                                                "Network Load Balancer (NLB) - Flows, Connections, TCP Resets"
                                            ),
                                        ),
                                    ],
                                    prefill=DefaultValue([]),
                                ),
                                required=True,
                            ),
                        },
                    ),
                    add_element_label=Label("Add Region"),
                    remove_element_label=Label("Remove Region"),
                ),
                required=True,
            ),
            "cloudwatch_cache_ttl": DictElement(
                parameter_form=Integer(
                    title=Title("Metrics Cache TTL"),
                    help_text=Help(
                        "Time in seconds to cache CloudWatch metric data per region (default: 300 = 5 minutes). "
                        "Must be a multiple of 60 seconds (AWS CloudWatch API requirement)."
                    ),
                    custom_validate=(
                        validators.NumberInRange(min_value=60),
                        _validate_multiple_of_60,
                    ),
                    prefill=DefaultValue(300),
                ),
                required=False,
            ),
            "cloudwatch_discovery_ttl": DictElement(
                parameter_form=Integer(
                    title=Title("Resource Discovery Cache TTL"),
                    help_text=Help(
                        "Time in seconds to cache resource discovery results (list_metrics API) per region. "
                        "Longer TTL = fewer API calls, but slower detection of new resources. "
                        "Default: 3600 seconds (1 hour). Must be a multiple of 60 and >= Metrics Cache TTL. "
                        "New resources will be detected within this interval."
                    ),
                    custom_validate=(
                        validators.NumberInRange(min_value=60),
                        _validate_multiple_of_60,
                    ),
                    prefill=DefaultValue(3600),
                ),
                required=False,
            ),
            "cloudwatch_api_warn": DictElement(
                parameter_form=Integer(
                    title=Title("CloudWatch API Warning Threshold (%)"),
                    help_text=Help(
                        "Warning threshold for CloudWatch API usage percentage of 1M free tier limit (default: 80%). "
                        "This is aggregated across all regions."
                    ),
                    custom_validate=(validators.NumberInRange(min_value=0, max_value=100),),
                    prefill=DefaultValue(80),
                ),
                required=False,
            ),
            "cloudwatch_api_crit": DictElement(
                parameter_form=Integer(
                    title=Title("CloudWatch API Critical Threshold (%)"),
                    help_text=Help(
                        "Critical threshold for CloudWatch API usage percentage of 1M free tier limit (default: 90%). "
                        "This is aggregated across all regions."
                    ),
                    custom_validate=(validators.NumberInRange(min_value=0, max_value=100),),
                    prefill=DefaultValue(90),
                ),
                required=False,
            ),
            "cloudwatch_max_workers": DictElement(
                parameter_form=Integer(
                    title=Title("Parallel Threads (max-workers)"),
                    help_text=Help(
                        "Maximum number of parallel threads for resource discovery and metric collection "
                        "across regions and services. "
                        "If not set, the agent uses min(4, 2 x CPUs of the machine it runs on), "
                        "e.g. 2 threads on a single-CPU instance. "
                        "A value set here is used as is. Set to 1 to disable parallelism. "
                        "Allowed range: 1 to 10; 10 matches the default connection pool of a boto3 "
                        "client, which all threads of one region share."
                    ),
                    custom_validate=(validators.NumberInRange(min_value=1, max_value=10),),
                    prefill=DefaultValue(4),
                ),
                required=False,
            ),
            "cloudwatch_stop_at_limit": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title(f"Free Tier Limit ({_FREE_TIER} requests/month)"),
                    help_text=Help(
                        f"Control what happens when the AWS CloudWatch free tier limit "
                        f"of {_FREE_TIER} API requests/month is reached. "
                        f"Default: Stop monitoring to avoid AWS costs."
                    ),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="stop",
                            title=Title(
                                f"Stop monitoring at {_FREE_TIER} free tier limit (minimize costs)"
                            ),
                            parameter_form=FixedValue(value="stop"),
                        ),
                        CascadingSingleChoiceElement(
                            name="force",
                            title=Title(
                                "Continue monitoring beyond free tier (AWS costs: $0.01/1000 requests)"
                            ),
                            parameter_form=FixedValue(value="force"),
                        ),
                    ],
                    prefill=DefaultValue("stop"),
                ),
                required=False,
            ),
            "cloudwatch_lambda_filter_deleted": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Lambda: Hide deleted functions immediately"),
                    label=Label("Check discovered Lambda functions against the Lambda API"),
                    help_text=Help(
                        "Off by default. Without this option, a deleted Lambda function disappears "
                        "once CloudWatch stops listing its metrics (up to 2 weeks after its last "
                        "data point); until then its services stay visible and show 0 values. "
                        "When enabled, discovered functions (including Lambda@Edge) are checked "
                        "against the Lambda API and deleted ones are hidden right away. "
                        "This requires the IAM permission lambda:ListFunctions. "
                        "WARNING: AWS returns the environment variables of all Lambda functions "
                        "in clear text with this call (e.g. database connection strings, API "
                        "tokens). Anyone holding the monitoring key can read them. The plugin "
                        "itself only uses the function names and does not store anything else."
                    ),
                    prefill=DefaultValue(False),
                ),
                required=True,
            ),
            "cloudwatch_cloudfront_metadata": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("CloudFront: Fetch description and URL"),
                    label=Label("Fetch comment, domain and aliases of CloudFront distributions"),
                    help_text=Help(
                        "Off by default. Needed for the 'Show Comment' and 'Show URL' options "
                        "of the CloudFront service rule; without it the service details show a "
                        "note instead of comment and URL. "
                        "Requires the IAM permission cloudfront:ListDistributions. "
                        "WARNING: AWS returns the full origin configuration with this call, "
                        "including origin custom headers in clear text. If you protect your "
                        "origins with a secret header (e.g. X-Origin-Verify), anyone holding the "
                        "monitoring key can read it. The plugin itself only keeps comment, "
                        "domain and aliases."
                    ),
                    prefill=DefaultValue(False),
                ),
                required=True,
            ),
        },
    )


#: Rule specification for the AWS CloudWatch Monitoring special agent.
#:
#: Registers the special agent configuration in Checkmk's WATO system
#: under the Cloud topic. Users can create rules to assign this
#: agent to hosts.
rule_spec_aws_cloudwatch = SpecialAgent(
    name="aws_cloudwatch",
    title=Title("Amazon Web Services (AWS) CloudWatch"),
    topic=Topic.CLOUD,
    parameter_form=_valuespec_special_agents_aws_cloudwatch,
)
