#!/usr/bin/env python3
"""Graphing definitions for AWS CloudWatch Monitoring.

This module defines metrics, perfometers, and graphs for visualizing
AWS CloudWatch monitoring data in Checkmk.

Categories:
    - CloudWatch API Metrics: API request counter and percentage
    - CloudWatch Service Metrics: Service-specific metrics for
      CloudFront, RDS, Lambda, DynamoDB, EC2, etc.

All metrics defined here are automatically matched with performance
data from the check plugins by metric name.
"""

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.metrics import (
    Color,
    DecimalNotation,
    IECNotation,
    Metric,
    TimeNotation,
    Unit,
)
from cmk.graphing.v1.perfometers import Closed, FocusRange, Perfometer

# ===== Units =====
#: Percentage unit for usage and error rate metrics.
UNIT_PERCENTAGE = Unit(DecimalNotation("%"))

#: Generic number unit for counts and counters.
UNIT_NUMBER = Unit(DecimalNotation(""))

#: Bytes unit with IEC notation (KiB, MiB, GiB).
UNIT_BYTES = Unit(IECNotation("B"))

#: Time unit with automatic scaling (seconds, minutes, hours).
UNIT_TIME = Unit(TimeNotation())

#: Milliseconds unit for latency metrics.
UNIT_TIME_MS = Unit(DecimalNotation("ms"))

# ===== CloudWatch API Counter Metrics =====
#: These metrics track CloudWatch API usage against the 1M free tier limit.
#: Used by the aws_cloudwatch_api_counter check plugin.

#: Forecasted API usage at end of month.
metric_forecast_usage = Metric(
    name="aws_cw_api_forecast_usage",
    title=Title("Forecasted API Usage"),
    unit=UNIT_NUMBER,
    color=Color.DARK_PURPLE,
)

#: Free tier limit value (1M requests/month).
metric_limit_usage = Metric(
    name="aws_cw_api_limit_usage",
    title=Title("Free Tier Limit"),
    unit=UNIT_NUMBER,
    color=Color.RED,
)

#: Forecasted API usage as percentage of free tier limit.
metric_forecast_percent = Metric(
    name="aws_cw_api_forecast_percent",
    title=Title("Forecasted API Usage (%)"),
    unit=UNIT_PERCENTAGE,
    color=Color.ORANGE,
)

#: Perfometer showing forecasted API usage percentage (0-100%).
perfometer_cloudwatch_api_usage = Perfometer(
    name="aws_cw_api_forecast_percent",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["aws_cw_api_forecast_percent"],
)

#: Absolute CloudWatch API forecast graph with free tier limit line.
graph_cloudwatch_api_forecast = Graph(
    name="cloudwatch_api_forecast",
    title=Title("CloudWatch API Forecast"),
    compound_lines=["aws_cw_api_forecast_usage"],
    simple_lines=["aws_cw_api_limit_usage"],
)

#: Percentage graph for CloudWatch API forecast with 0-100% range.
graph_cloudwatch_api_forecast_percentage = Graph(
    name="cloudwatch_api_forecast_percentage",
    title=Title("CloudWatch API Forecast (%)"),
    compound_lines=["aws_cw_api_forecast_percent"],
    minimal_range=MinimalRange(0, 100),
)

# ===== CloudWatch Service Metrics =====
#: These metrics are populated by the aws_cloudwatch_metrics check plugin.
#: Each AWS service has its own set of metrics matching the CloudWatch API.

# ----- CloudFront Distribution Metrics -----
#: Metrics for CloudFront CDN monitoring.
#: All CloudFront metrics must be queried from us-east-1.

#: Total HTTP/HTTPS requests received by CloudFront.
metric_cloudfront_requests = Metric(
    name="cloudfront_requests",
    title=Title("CloudFront Requests"),
    unit=UNIT_NUMBER,
    color=Color.BLUE,
)

#: Data transferred from CloudFront edge to viewers.
metric_cloudfront_bytes_downloaded = Metric(
    name="cloudfront_bytes_downloaded",
    title=Title("CloudFront Bytes Downloaded"),
    unit=UNIT_BYTES,
    color=Color.GREEN,
)

#: Data transferred from viewers to CloudFront origin.
metric_cloudfront_bytes_uploaded = Metric(
    name="cloudfront_bytes_uploaded",
    title=Title("CloudFront Bytes Uploaded"),
    unit=UNIT_BYTES,
    color=Color.PURPLE,
)

#: Percentage of all HTTP error responses (4xx + 5xx).
metric_cloudfront_total_error_rate = Metric(
    name="cloudfront_total_error_rate",
    title=Title("CloudFront Total Error Rate"),
    unit=UNIT_PERCENTAGE,
    color=Color.RED,
)

#: Client error rate (4xx status codes).
metric_cloudfront_4xx_error_rate = Metric(
    name="cloudfront_4xx_error_rate",
    title=Title("CloudFront 4xx Error Rate"),
    unit=UNIT_PERCENTAGE,
    color=Color.ORANGE,
)

#: Server error rate (5xx status codes).
metric_cloudfront_5xx_error_rate = Metric(
    name="cloudfront_5xx_error_rate",
    title=Title("CloudFront 5xx Error Rate"),
    unit=UNIT_PERCENTAGE,
    color=Color.DARK_RED,
)

# ----- RDS Database Instance Metrics -----
#: Metrics for RDS database monitoring.

#: RDS instance CPU utilization percentage.
metric_rds_cpu_utilization = Metric(
    name="rds_cpu_utilization",
    title=Title("RDS CPU Utilization"),
    unit=UNIT_PERCENTAGE,
    color=Color.BLUE,
)

#: Number of active database connections.
metric_rds_connections = Metric(
    name="rds_connections",
    title=Title("RDS Database Connections"),
    unit=UNIT_NUMBER,
    color=Color.CYAN,
)

# ----- Lambda Function Metrics -----
#: Metrics for Lambda function monitoring.
#: Also used for Lambda@Edge functions.

#: Total Lambda function invocations.
metric_lambda_invocations = Metric(
    name="lambda_invocations",
    title=Title("Lambda Invocations"),
    unit=UNIT_NUMBER,
    color=Color.ORANGE,
)

#: Lambda function invocation errors.
metric_lambda_errors = Metric(
    name="lambda_errors",
    title=Title("Lambda Errors"),
    unit=UNIT_NUMBER,
    color=Color.RED,
)

#: Average Lambda function execution duration in milliseconds.
metric_lambda_duration_average = Metric(
    name="lambda_duration_average",
    title=Title("Lambda Duration (Average)"),
    unit=UNIT_TIME_MS,
    color=Color.PURPLE,
)

#: Maximum Lambda function execution duration in milliseconds.
metric_lambda_duration_maximum = Metric(
    name="lambda_duration_maximum",
    title=Title("Lambda Duration (Maximum)"),
    unit=UNIT_TIME_MS,
    color=Color.DARK_PURPLE,
)

# ----- CloudFront Functions Metrics -----
#: Metrics for CloudFront Functions (lightweight JS functions at edge).
#: For Lambda@Edge (real Lambda functions), use Lambda metrics instead.

#: CloudFront Function invocation count.
metric_cloudfront_functions_invocations = Metric(
    name="cloudfront_functions_invocations",
    title=Title("CloudFront Function Invocations"),
    unit=UNIT_NUMBER,
    color=Color.BLUE,
)

#: Compute time utilization as percentage of allowed maximum.
metric_cloudfront_functions_compute_utilization = Metric(
    name="cloudfront_functions_compute_utilization",
    title=Title("CloudFront Function Compute Utilization"),
    unit=UNIT_PERCENTAGE,
    color=Color.GREEN,
)

#: Runtime execution errors during function invocation.
metric_cloudfront_functions_execution_errors = Metric(
    name="cloudfront_functions_execution_errors",
    title=Title("CloudFront Function Execution Errors"),
    unit=UNIT_NUMBER,
    color=Color.RED,
)

#: Input validation errors (malformed request/response).
metric_cloudfront_functions_validation_errors = Metric(
    name="cloudfront_functions_validation_errors",
    title=Title("CloudFront Function Validation Errors"),
    unit=UNIT_NUMBER,
    color=Color.DARK_RED,
)

# ----- EC2 Instance Metrics -----
#: Metrics for EC2 instance monitoring.

#: EC2 instance CPU utilization percentage.
metric_ec2_cpu_utilization = Metric(
    name="ec2_cpu_utilization",
    title=Title("EC2 CPU Utilization"),
    unit=UNIT_PERCENTAGE,
    color=Color.BLUE,
)

#: Bytes received on all network interfaces.
metric_ec2_network_in = Metric(
    name="ec2_network_in",
    title=Title("EC2 Network In"),
    unit=UNIT_BYTES,
    color=Color.GREEN,
)

#: Bytes sent on all network interfaces.
metric_ec2_network_out = Metric(
    name="ec2_network_out",
    title=Title("EC2 Network Out"),
    unit=UNIT_BYTES,
    color=Color.CYAN,
)

# ----- DynamoDB Table Metrics -----
#: Metrics for DynamoDB table monitoring.

#: Read capacity units consumed by table operations.
metric_dynamodb_consumed_read_capacity = Metric(
    name="dynamodb_consumed_read_capacity",
    title=Title("DynamoDB Consumed Read Capacity"),
    unit=UNIT_NUMBER,
    color=Color.BLUE,
)

#: Write capacity units consumed by table operations.
metric_dynamodb_consumed_write_capacity = Metric(
    name="dynamodb_consumed_write_capacity",
    title=Title("DynamoDB Consumed Write Capacity"),
    unit=UNIT_NUMBER,
    color=Color.GREEN,
)

#: Requests failed due to user/client errors.
metric_dynamodb_user_errors = Metric(
    name="dynamodb_user_errors",
    title=Title("DynamoDB User Errors"),
    unit=UNIT_NUMBER,
    color=Color.ORANGE,
)

#: Requests failed due to DynamoDB system errors.
metric_dynamodb_system_errors = Metric(
    name="dynamodb_system_errors",
    title=Title("DynamoDB System Errors"),
    unit=UNIT_NUMBER,
    color=Color.RED,
)

#: Requests rejected due to exceeding provisioned throughput.
metric_dynamodb_throttledrequests = Metric(
    name="dynamodb_throttledrequests",
    title=Title("DynamoDB Throttled Requests"),
    unit=UNIT_NUMBER,
    color=Color.DARK_RED,
)

#: Average latency for successful DynamoDB requests in milliseconds.
metric_dynamodb_request_latency = Metric(
    name="dynamodb_request_latency",
    title=Title("DynamoDB Request Latency"),
    unit=UNIT_TIME_MS,
    color=Color.PURPLE,
)

# ----- Extended RDS Metrics -----
#: RDS read latency in seconds.
metric_rds_read_latency = Metric(
    name="rds_read_latency",
    title=Title("RDS Read Latency"),
    unit=UNIT_TIME,
    color=Color.BLUE,
)

#: RDS write latency in seconds.
metric_rds_write_latency = Metric(
    name="rds_write_latency",
    title=Title("RDS Write Latency"),
    unit=UNIT_TIME,
    color=Color.GREEN,
)

#: RDS replica lag in seconds.
metric_rds_replica_lag = Metric(
    name="rds_replica_lag",
    title=Title("RDS Replica Lag"),
    unit=UNIT_TIME,
    color=Color.ORANGE,
)

#: RDS burst balance percentage.
metric_rds_burstbalance = Metric(
    name="rds_burstbalance",
    title=Title("RDS Burst Balance"),
    unit=UNIT_PERCENTAGE,
    color=Color.PURPLE,
)

#: RDS disk queue depth.
metric_rds_diskqueuedepth = Metric(
    name="rds_diskqueuedepth",
    title=Title("RDS Disk Queue Depth"),
    unit=UNIT_NUMBER,
    color=Color.CYAN,
)

#: RDS freeable memory in bytes.
metric_rds_freeable_memory = Metric(
    name="rds_freeable_memory",
    title=Title("RDS Freeable Memory"),
    unit=UNIT_BYTES,
    color=Color.DARK_BLUE,
)

#: RDS free storage space in bytes.
metric_rds_free_storage = Metric(
    name="rds_free_storage",
    title=Title("RDS Free Storage Space"),
    unit=UNIT_BYTES,
    color=Color.DARK_GREEN,
)

#: RDS read IOPS.
metric_rds_read_iops = Metric(
    name="rds_read_iops",
    title=Title("RDS Read IOPS"),
    unit=UNIT_NUMBER,
    color=Color.LIGHT_BLUE,
)

#: RDS write IOPS.
metric_rds_write_iops = Metric(
    name="rds_write_iops",
    title=Title("RDS Write IOPS"),
    unit=UNIT_NUMBER,
    color=Color.LIGHT_GREEN,
)

# ----- Extended EC2 Metrics -----
#: EC2 CPU credit usage.
metric_ec2_cpucreditusage = Metric(
    name="ec2_cpucreditusage",
    title=Title("EC2 CPU Credit Usage"),
    unit=UNIT_NUMBER,
    color=Color.ORANGE,
)

#: EC2 CPU credit balance.
metric_ec2_cpu_credit_balance = Metric(
    name="ec2_cpu_credit_balance",
    title=Title("EC2 CPU Credit Balance"),
    unit=UNIT_NUMBER,
    color=Color.DARK_ORANGE,
)

#: EC2 status check failed.
metric_ec2_status_check_failed = Metric(
    name="ec2_status_check_failed",
    title=Title("EC2 Status Check Failed"),
    unit=UNIT_NUMBER,
    color=Color.RED,
)

#: EC2 disk read bytes.
metric_ec2_disk_read_bytes = Metric(
    name="ec2_disk_read_bytes",
    title=Title("EC2 Disk Read Bytes"),
    unit=UNIT_BYTES,
    color=Color.PURPLE,
)

#: EC2 disk write bytes.
metric_ec2_disk_write_bytes = Metric(
    name="ec2_disk_write_bytes",
    title=Title("EC2 Disk Write Bytes"),
    unit=UNIT_BYTES,
    color=Color.DARK_PURPLE,
)

# ----- EBS Volume Metrics -----
#: EBS volume read ops.
metric_ebs_read_ops = Metric(
    name="ebs_read_ops",
    title=Title("EBS Volume Read Ops"),
    unit=UNIT_NUMBER,
    color=Color.BLUE,
)

#: EBS volume write ops.
metric_ebs_write_ops = Metric(
    name="ebs_write_ops",
    title=Title("EBS Volume Write Ops"),
    unit=UNIT_NUMBER,
    color=Color.GREEN,
)

#: EBS volume read bytes.
metric_ebs_read_bytes = Metric(
    name="ebs_read_bytes",
    title=Title("EBS Volume Read Bytes"),
    unit=UNIT_BYTES,
    color=Color.CYAN,
)

#: EBS volume write bytes.
metric_ebs_write_bytes = Metric(
    name="ebs_write_bytes",
    title=Title("EBS Volume Write Bytes"),
    unit=UNIT_BYTES,
    color=Color.PURPLE,
)

#: EBS burst balance percentage.
metric_ebs_burst_balance = Metric(
    name="ebs_burst_balance",
    title=Title("EBS Burst Balance"),
    unit=UNIT_PERCENTAGE,
    color=Color.ORANGE,
)

# ----- S3 Bucket Metrics -----
#: S3 bucket size in bytes.
metric_s3_bucket_size = Metric(
    name="s3_bucket_size",
    title=Title("S3 Bucket Size"),
    unit=UNIT_BYTES,
    color=Color.BLUE,
)

#: S3 number of objects.
metric_s3_object_count = Metric(
    name="s3_object_count",
    title=Title("S3 Number of Objects"),
    unit=UNIT_NUMBER,
    color=Color.GREEN,
)

# ----- Classic ELB Metrics -----
#: ELB request count.
metric_elb_request_count = Metric(
    name="elb_request_count",
    title=Title("ELB Request Count"),
    unit=UNIT_NUMBER,
    color=Color.BLUE,
)

#: ELB healthy host count.
metric_elb_healthy_hosts = Metric(
    name="elb_healthy_hosts",
    title=Title("ELB Healthy Hosts"),
    unit=UNIT_NUMBER,
    color=Color.GREEN,
)

#: ELB unhealthy host count.
metric_elb_unhealthy_hosts = Metric(
    name="elb_unhealthy_hosts",
    title=Title("ELB Unhealthy Hosts"),
    unit=UNIT_NUMBER,
    color=Color.RED,
)

#: ELB latency.
metric_elb_latency = Metric(
    name="elb_latency",
    title=Title("ELB Latency"),
    unit=UNIT_TIME,
    color=Color.PURPLE,
)

# ----- Application Load Balancer (ALB) Metrics -----
#: ALB request count.
metric_alb_request_count = Metric(
    name="alb_request_count",
    title=Title("ALB Request Count"),
    unit=UNIT_NUMBER,
    color=Color.BLUE,
)

#: ALB target response time.
metric_alb_response_time = Metric(
    name="alb_response_time",
    title=Title("ALB Target Response Time"),
    unit=UNIT_TIME,
    color=Color.PURPLE,
)

#: ALB active connection count.
metric_alb_active_connections = Metric(
    name="alb_active_connections",
    title=Title("ALB Active Connections"),
    unit=UNIT_NUMBER,
    color=Color.CYAN,
)

#: ALB new connection count.
metric_elbv2_application_newconnectioncount = Metric(
    name="elbv2_application_newconnectioncount",
    title=Title("ALB New Connections"),
    unit=UNIT_NUMBER,
    color=Color.GREEN,
)

#: ALB processed bytes.
metric_elbv2_application_processedbytes = Metric(
    name="elbv2_application_processedbytes",
    title=Title("ALB Processed Bytes"),
    unit=UNIT_BYTES,
    color=Color.DARK_BLUE,
)

#: ALB HTTP 2xx responses.
metric_alb_httpcode_target_2xx_count = Metric(
    name="alb_httpcode_target_2xx_count",
    title=Title("ALB Target 2xx"),
    unit=UNIT_NUMBER,
    color=Color.GREEN,
)

#: ALB HTTP 4xx responses.
metric_alb_httpcode_target_4xx_count = Metric(
    name="alb_httpcode_target_4xx_count",
    title=Title("ALB Target 4xx"),
    unit=UNIT_NUMBER,
    color=Color.ORANGE,
)

#: ALB HTTP 5xx responses.
metric_alb_httpcode_target_5xx_count = Metric(
    name="alb_httpcode_target_5xx_count",
    title=Title("ALB Target 5xx"),
    unit=UNIT_NUMBER,
    color=Color.RED,
)

#: ALB healthy hosts.
metric_alb_healthy_targets = Metric(
    name="alb_healthy_targets",
    title=Title("ALB Healthy Hosts"),
    unit=UNIT_NUMBER,
    color=Color.DARK_GREEN,
)

#: ALB unhealthy hosts.
metric_alb_unhealthy_targets = Metric(
    name="alb_unhealthy_targets",
    title=Title("ALB Unhealthy Hosts"),
    unit=UNIT_NUMBER,
    color=Color.DARK_RED,
)

# ----- Network Load Balancer (NLB) Metrics -----
#: NLB active flow count.
metric_nlb_active_flows = Metric(
    name="nlb_active_flows",
    title=Title("NLB Active Flows"),
    unit=UNIT_NUMBER,
    color=Color.BLUE,
)

#: NLB new flow count.
metric_nlb_new_flows = Metric(
    name="nlb_new_flows",
    title=Title("NLB New Flows"),
    unit=UNIT_NUMBER,
    color=Color.GREEN,
)

#: NLB processed bytes.
metric_nlb_processed_bytes = Metric(
    name="nlb_processed_bytes",
    title=Title("NLB Processed Bytes"),
    unit=UNIT_BYTES,
    color=Color.CYAN,
)

#: NLB TCP client reset count.
metric_nlb_tcp_client_reset_count = Metric(
    name="nlb_tcp_client_reset_count",
    title=Title("NLB TCP Client Resets"),
    unit=UNIT_NUMBER,
    color=Color.ORANGE,
)

#: NLB TCP target reset count.
metric_nlb_tcp_target_reset_count = Metric(
    name="nlb_tcp_target_reset_count",
    title=Title("NLB TCP Target Resets"),
    unit=UNIT_NUMBER,
    color=Color.RED,
)

#: NLB healthy hosts.
metric_nlb_healthy_targets = Metric(
    name="nlb_healthy_targets",
    title=Title("NLB Healthy Hosts"),
    unit=UNIT_NUMBER,
    color=Color.DARK_GREEN,
)

#: NLB unhealthy hosts.
metric_nlb_unhealthy_targets = Metric(
    name="nlb_unhealthy_targets",
    title=Title("NLB Unhealthy Hosts"),
    unit=UNIT_NUMBER,
    color=Color.DARK_RED,
)

# ----- Extended Lambda Metrics -----
#: Lambda throttles.
metric_lambda_throttles = Metric(
    name="lambda_throttles",
    title=Title("Lambda Throttles"),
    unit=UNIT_NUMBER,
    color=Color.ORANGE,
)

#: Lambda concurrent executions.
metric_lambda_concurrent_executions = Metric(
    name="lambda_concurrent_executions",
    title=Title("Lambda Concurrent Executions"),
    unit=UNIT_NUMBER,
    color=Color.CYAN,
)
