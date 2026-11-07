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

#: Bytes per second unit with IEC notation.
UNIT_BYTES_PER_SECOND = Unit(IECNotation("B/s"))

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

#: Requests failed due to DynamoDB system errors.
metric_dynamodb_system_errors = Metric(
    name="dynamodb_system_errors",
    title=Title("DynamoDB System Errors"),
    unit=UNIT_NUMBER,
    color=Color.RED,
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
metric_rds_burst_balance = Metric(
    name="rds_burst_balance",
    title=Title("RDS Burst Balance"),
    unit=UNIT_PERCENTAGE,
    color=Color.PURPLE,
)

#: RDS disk queue depth.
metric_rds_disk_queue_depth = Metric(
    name="rds_disk_queue_depth",
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
metric_ec2_cpu_credit_usage = Metric(
    name="ec2_cpu_credit_usage",
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
    unit=UNIT_TIME_MS,
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
    unit=UNIT_TIME_MS,
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
metric_alb_new_connections = Metric(
    name="alb_new_connections",
    title=Title("ALB New Connections"),
    unit=UNIT_NUMBER,
    color=Color.GREEN,
)

#: ALB processed bytes.
metric_alb_processed_bytes = Metric(
    name="alb_processed_bytes",
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

# ----- CloudFront: further metrics -----
metric_cloudfront_cache_hit_rate = Metric(
    name="cloudfront_cache_hit_rate",
    title=Title("CloudFront Cache Hit Rate"),
    unit=UNIT_PERCENTAGE,
    color=Color.BLUE,
)

metric_cloudfront_origin_latency = Metric(
    name="cloudfront_origin_latency",
    title=Title("CloudFront Origin Latency"),
    unit=UNIT_TIME_MS,
    color=Color.GREEN,
)


# ----- ALB: further metrics -----
metric_alb_rejected_connections = Metric(
    name="alb_rejected_connections",
    title=Title("ALB Rejected Connections"),
    unit=UNIT_NUMBER,
    color=Color.BLUE,
)

metric_alb_client_tls_errors = Metric(
    name="alb_client_tls_errors",
    title=Title("ALB Client TLS Errors"),
    unit=UNIT_NUMBER,
    color=Color.GREEN,
)

metric_alb_target_tls_errors = Metric(
    name="alb_target_tls_errors",
    title=Title("ALB Target TLS Errors"),
    unit=UNIT_NUMBER,
    color=Color.ORANGE,
)

metric_alb_target_connection_errors = Metric(
    name="alb_target_connection_errors",
    title=Title("ALB Target Connection Errors"),
    unit=UNIT_NUMBER,
    color=Color.PURPLE,
)

metric_alb_httpcode_elb_3xx_count = Metric(
    name="alb_httpcode_elb_3xx_count",
    title=Title("ALB 3XX"),
    unit=UNIT_NUMBER,
    color=Color.CYAN,
)

metric_alb_httpcode_elb_500_count = Metric(
    name="alb_httpcode_elb_500_count",
    title=Title("ALB 500"),
    unit=UNIT_NUMBER,
    color=Color.RED,
)

metric_alb_httpcode_elb_502_count = Metric(
    name="alb_httpcode_elb_502_count",
    title=Title("ALB 502"),
    unit=UNIT_NUMBER,
    color=Color.DARK_BLUE,
)

metric_alb_httpcode_elb_503_count = Metric(
    name="alb_httpcode_elb_503_count",
    title=Title("ALB 503"),
    unit=UNIT_NUMBER,
    color=Color.DARK_GREEN,
)

metric_alb_httpcode_elb_504_count = Metric(
    name="alb_httpcode_elb_504_count",
    title=Title("ALB 504"),
    unit=UNIT_NUMBER,
    color=Color.DARK_ORANGE,
)

metric_alb_unhealthy_targets_pct = Metric(
    name="alb_unhealthy_targets_pct",
    title=Title("ALB Unhealthy Targets (%)"),
    unit=UNIT_PERCENTAGE,
    color=Color.DARK_PURPLE,
)

metric_alb_httpcode_elb_4xx_count = Metric(
    name="alb_httpcode_elb_4xx_count",
    title=Title("ALB 4XX"),
    unit=UNIT_NUMBER,
    color=Color.DARK_RED,
)

metric_alb_httpcode_elb_5xx_count = Metric(
    name="alb_httpcode_elb_5xx_count",
    title=Title("ALB 5XX"),
    unit=UNIT_NUMBER,
    color=Color.LIGHT_BLUE,
)

metric_alb_httpcode_target_3xx_count = Metric(
    name="alb_httpcode_target_3xx_count",
    title=Title("ALB Target 3XX"),
    unit=UNIT_NUMBER,
    color=Color.LIGHT_GREEN,
)


# ----- NLB: further metrics -----
metric_nlb_active_flows_tcp = Metric(
    name="nlb_active_flows_tcp",
    title=Title("NLB Active Flows TCP"),
    unit=UNIT_NUMBER,
    color=Color.BLUE,
)

metric_nlb_active_flows_udp = Metric(
    name="nlb_active_flows_udp",
    title=Title("NLB Active Flows UDP"),
    unit=UNIT_NUMBER,
    color=Color.GREEN,
)

metric_nlb_active_flows_tls = Metric(
    name="nlb_active_flows_tls",
    title=Title("NLB Active Flows TLS"),
    unit=UNIT_NUMBER,
    color=Color.ORANGE,
)

metric_nlb_new_flows_tcp = Metric(
    name="nlb_new_flows_tcp",
    title=Title("NLB New Flows TCP"),
    unit=UNIT_NUMBER,
    color=Color.PURPLE,
)

metric_nlb_new_flows_udp = Metric(
    name="nlb_new_flows_udp",
    title=Title("NLB New Flows UDP"),
    unit=UNIT_NUMBER,
    color=Color.CYAN,
)

metric_nlb_new_flows_tls = Metric(
    name="nlb_new_flows_tls",
    title=Title("NLB New Flows TLS"),
    unit=UNIT_NUMBER,
    color=Color.RED,
)

metric_nlb_processed_bytes_tcp = Metric(
    name="nlb_processed_bytes_tcp",
    title=Title("NLB Processed Bytes TCP"),
    unit=UNIT_BYTES,
    color=Color.DARK_BLUE,
)

metric_nlb_processed_bytes_udp = Metric(
    name="nlb_processed_bytes_udp",
    title=Title("NLB Processed Bytes UDP"),
    unit=UNIT_BYTES,
    color=Color.DARK_GREEN,
)

metric_nlb_processed_bytes_tls = Metric(
    name="nlb_processed_bytes_tls",
    title=Title("NLB Processed Bytes TLS"),
    unit=UNIT_BYTES,
    color=Color.DARK_ORANGE,
)

metric_nlb_processed_packets = Metric(
    name="nlb_processed_packets",
    title=Title("NLB Processed Packets"),
    unit=UNIT_NUMBER,
    color=Color.DARK_PURPLE,
)

metric_nlb_consumed_lcus = Metric(
    name="nlb_consumed_lcus",
    title=Title("NLB Consumed LCUs"),
    unit=UNIT_NUMBER,
    color=Color.DARK_RED,
)

metric_nlb_client_tls_errors = Metric(
    name="nlb_client_tls_errors",
    title=Title("NLB Client TLS Errors"),
    unit=UNIT_NUMBER,
    color=Color.LIGHT_BLUE,
)

metric_nlb_target_tls_errors = Metric(
    name="nlb_target_tls_errors",
    title=Title("NLB Target TLS Errors"),
    unit=UNIT_NUMBER,
    color=Color.LIGHT_GREEN,
)

metric_nlb_unhealthy_targets_pct = Metric(
    name="nlb_unhealthy_targets_pct",
    title=Title("NLB Unhealthy Targets (%)"),
    unit=UNIT_PERCENTAGE,
    color=Color.BLUE,
)

metric_nlb_tcp_elb_reset_count = Metric(
    name="nlb_tcp_elb_reset_count",
    title=Title("NLB Resets"),
    unit=UNIT_NUMBER,
    color=Color.GREEN,
)


# ----- ELB: further metrics -----
metric_elb_spillover_count = Metric(
    name="elb_spillover_count",
    title=Title("ELB Spillover"),
    unit=UNIT_NUMBER,
    color=Color.BLUE,
)

metric_elb_surge_queue_length = Metric(
    name="elb_surge_queue_length",
    title=Title("ELB Surge Queue Length"),
    unit=UNIT_NUMBER,
    color=Color.GREEN,
)

metric_elb_unhealthy_hosts_pct = Metric(
    name="elb_unhealthy_hosts_pct",
    title=Title("ELB Unhealthy Hosts (%)"),
    unit=UNIT_PERCENTAGE,
    color=Color.ORANGE,
)

metric_elb_httpcode_elb_4xx = Metric(
    name="elb_httpcode_elb_4xx",
    title=Title("ELB 4XX"),
    unit=UNIT_NUMBER,
    color=Color.PURPLE,
)

metric_elb_httpcode_elb_5xx = Metric(
    name="elb_httpcode_elb_5xx",
    title=Title("ELB 5XX"),
    unit=UNIT_NUMBER,
    color=Color.CYAN,
)

metric_elb_httpcode_backend_4xx = Metric(
    name="elb_httpcode_backend_4xx",
    title=Title("ELB Backend 4XX"),
    unit=UNIT_NUMBER,
    color=Color.RED,
)

metric_elb_httpcode_backend_5xx = Metric(
    name="elb_httpcode_backend_5xx",
    title=Title("ELB Backend 5XX"),
    unit=UNIT_NUMBER,
    color=Color.DARK_BLUE,
)

metric_elb_httpcode_backend_2xx = Metric(
    name="elb_httpcode_backend_2xx",
    title=Title("ELB Backend 2XX"),
    unit=UNIT_NUMBER,
    color=Color.DARK_GREEN,
)

metric_elb_httpcode_backend_3xx = Metric(
    name="elb_httpcode_backend_3xx",
    title=Title("ELB Backend 3XX"),
    unit=UNIT_NUMBER,
    color=Color.DARK_ORANGE,
)


# ----- DynamoDB: further metrics -----
metric_dynamodb_provisioned_read = Metric(
    name="dynamodb_provisioned_read",
    title=Title("DynamoDB Provisioned Read"),
    unit=UNIT_NUMBER,
    color=Color.BLUE,
)

metric_dynamodb_provisioned_write = Metric(
    name="dynamodb_provisioned_write",
    title=Title("DynamoDB Provisioned Write"),
    unit=UNIT_NUMBER,
    color=Color.GREEN,
)

metric_dynamodb_conditional_check_failed = Metric(
    name="dynamodb_conditional_check_failed",
    title=Title("DynamoDB Conditional Check Failed"),
    unit=UNIT_NUMBER,
    color=Color.ORANGE,
)

metric_dynamodb_transaction_conflicts = Metric(
    name="dynamodb_transaction_conflicts",
    title=Title("DynamoDB Transaction Conflicts"),
    unit=UNIT_NUMBER,
    color=Color.PURPLE,
)

metric_dynamodb_read_throttle_events = Metric(
    name="dynamodb_read_throttle_events",
    title=Title("DynamoDB Read Throttle Events"),
    unit=UNIT_NUMBER,
    color=Color.CYAN,
)

metric_dynamodb_write_throttle_events = Metric(
    name="dynamodb_write_throttle_events",
    title=Title("DynamoDB Write Throttle Events"),
    unit=UNIT_NUMBER,
    color=Color.RED,
)


# ----- EBS: further metrics -----
metric_ebs_queue_length = Metric(
    name="ebs_queue_length",
    title=Title("EBS Queue Length"),
    unit=UNIT_NUMBER,
    color=Color.BLUE,
)

metric_ebs_idle_time = Metric(
    name="ebs_idle_time",
    title=Title("EBS Idle Time"),
    unit=UNIT_TIME,
    color=Color.GREEN,
)

metric_ebs_throughput_percentage = Metric(
    name="ebs_throughput_percentage",
    title=Title("EBS Throughput Percentage"),
    unit=UNIT_PERCENTAGE,
    color=Color.ORANGE,
)

metric_ebs_consumed_read_write_ops = Metric(
    name="ebs_consumed_read_write_ops",
    title=Title("EBS Consumed Read/Write Ops"),
    unit=UNIT_NUMBER,
    color=Color.PURPLE,
)

metric_ebs_read_latency = Metric(
    name="ebs_read_latency",
    title=Title("EBS Read Latency"),
    unit=UNIT_TIME_MS,
    color=Color.CYAN,
)

metric_ebs_write_latency = Metric(
    name="ebs_write_latency",
    title=Title("EBS Write Latency"),
    unit=UNIT_TIME_MS,
    color=Color.RED,
)


# ----- EC2: further metrics -----
metric_ec2_disk_read_ops = Metric(
    name="ec2_disk_read_ops",
    title=Title("EC2 Disk Read Ops"),
    unit=UNIT_NUMBER,
    color=Color.BLUE,
)

metric_ec2_disk_write_ops = Metric(
    name="ec2_disk_write_ops",
    title=Title("EC2 Disk Write Ops"),
    unit=UNIT_NUMBER,
    color=Color.GREEN,
)

metric_ec2_network_packets_in = Metric(
    name="ec2_network_packets_in",
    title=Title("EC2 Network Packets In"),
    unit=UNIT_NUMBER,
    color=Color.ORANGE,
)

metric_ec2_network_packets_out = Metric(
    name="ec2_network_packets_out",
    title=Title("EC2 Network Packets Out"),
    unit=UNIT_NUMBER,
    color=Color.PURPLE,
)

metric_ec2_ebs_read_ops = Metric(
    name="ec2_ebs_read_ops",
    title=Title("EC2 EBS Read Ops"),
    unit=UNIT_NUMBER,
    color=Color.CYAN,
)

metric_ec2_ebs_write_ops = Metric(
    name="ec2_ebs_write_ops",
    title=Title("EC2 EBS Write Ops"),
    unit=UNIT_NUMBER,
    color=Color.RED,
)

metric_ec2_ebs_read_bytes = Metric(
    name="ec2_ebs_read_bytes",
    title=Title("EC2 EBS Read"),
    unit=UNIT_BYTES,
    color=Color.DARK_BLUE,
)

metric_ec2_ebs_write_bytes = Metric(
    name="ec2_ebs_write_bytes",
    title=Title("EC2 EBS Write"),
    unit=UNIT_BYTES,
    color=Color.DARK_GREEN,
)

metric_ec2_status_check_failed_instance = Metric(
    name="ec2_status_check_failed_instance",
    title=Title("EC2 Instance Status Check Failed"),
    unit=UNIT_NUMBER,
    color=Color.DARK_ORANGE,
)

metric_ec2_status_check_failed_system = Metric(
    name="ec2_status_check_failed_system",
    title=Title("EC2 System Status Check Failed"),
    unit=UNIT_NUMBER,
    color=Color.DARK_PURPLE,
)


# ----- Lambda: further metrics -----
metric_lambda_duration_minimum = Metric(
    name="lambda_duration_minimum",
    title=Title("Lambda Duration (Minimum)"),
    unit=UNIT_TIME_MS,
    color=Color.BLUE,
)

metric_lambda_iterator_age = Metric(
    name="lambda_iterator_age",
    title=Title("Lambda Iterator Age"),
    unit=UNIT_TIME_MS,
    color=Color.GREEN,
)

metric_lambda_dead_letter_errors = Metric(
    name="lambda_dead_letter_errors",
    title=Title("Lambda Dead Letter Errors"),
    unit=UNIT_NUMBER,
    color=Color.ORANGE,
)

metric_lambda_destination_delivery_failures = Metric(
    name="lambda_destination_delivery_failures",
    title=Title("Lambda Destination Delivery Failures"),
    unit=UNIT_NUMBER,
    color=Color.PURPLE,
)

metric_lambda_async_events_received = Metric(
    name="lambda_async_events_received",
    title=Title("Lambda Async Events Received"),
    unit=UNIT_NUMBER,
    color=Color.CYAN,
)

metric_lambda_async_event_age = Metric(
    name="lambda_async_event_age",
    title=Title("Lambda Async Event Age"),
    unit=UNIT_TIME_MS,
    color=Color.RED,
)

metric_lambda_async_events_dropped = Metric(
    name="lambda_async_events_dropped",
    title=Title("Lambda Async Events Dropped"),
    unit=UNIT_NUMBER,
    color=Color.DARK_BLUE,
)

metric_lambda_unreserved_concurrent_executions = Metric(
    name="lambda_unreserved_concurrent_executions",
    title=Title("Lambda Unreserved Concurrent Executions"),
    unit=UNIT_NUMBER,
    color=Color.DARK_GREEN,
)

metric_lambda_provisioned_concurrent_executions = Metric(
    name="lambda_provisioned_concurrent_executions",
    title=Title("Lambda Provisioned Concurrent Executions"),
    unit=UNIT_NUMBER,
    color=Color.DARK_ORANGE,
)

metric_lambda_provisioned_concurrency_invocations = Metric(
    name="lambda_provisioned_concurrency_invocations",
    title=Title("Lambda Provisioned Concurrency Invocations"),
    unit=UNIT_NUMBER,
    color=Color.DARK_PURPLE,
)

metric_lambda_provisioned_concurrency_spillover = Metric(
    name="lambda_provisioned_concurrency_spillover",
    title=Title("Lambda Provisioned Concurrency Spillover"),
    unit=UNIT_NUMBER,
    color=Color.DARK_RED,
)

metric_lambda_provisioned_concurrency_utilization = Metric(
    name="lambda_provisioned_concurrency_utilization",
    title=Title("Lambda Provisioned Concurrency Utilization"),
    unit=UNIT_PERCENTAGE,
    color=Color.LIGHT_BLUE,
)

metric_lambda_memory_utilization = Metric(
    name="lambda_memory_utilization",
    title=Title("Lambda Memory Utilization"),
    unit=UNIT_PERCENTAGE,
    color=Color.LIGHT_GREEN,
)

metric_lambda_total_memory = Metric(
    name="lambda_total_memory",
    title=Title("Lambda Total Memory"),
    unit=UNIT_BYTES,
    color=Color.BLUE,
)

metric_lambda_used_memory_max = Metric(
    name="lambda_used_memory_max",
    title=Title("Lambda Used Memory (Maximum)"),
    unit=UNIT_BYTES,
    color=Color.GREEN,
)

metric_lambda_cpu_total_time = Metric(
    name="lambda_cpu_total_time",
    title=Title("Lambda CPU Time"),
    unit=UNIT_TIME_MS,
    color=Color.ORANGE,
)

metric_lambda_tx_bytes = Metric(
    name="lambda_tx_bytes",
    title=Title("Lambda Network Sent"),
    unit=UNIT_BYTES,
    color=Color.PURPLE,
)

metric_lambda_rx_bytes = Metric(
    name="lambda_rx_bytes",
    title=Title("Lambda Network Received"),
    unit=UNIT_BYTES,
    color=Color.CYAN,
)

metric_lambda_init_duration = Metric(
    name="lambda_init_duration",
    title=Title("Lambda Init Duration"),
    unit=UNIT_TIME_MS,
    color=Color.RED,
)

metric_lambda_cold_starts = Metric(
    name="lambda_cold_starts",
    title=Title("Lambda Cold Starts"),
    unit=UNIT_NUMBER,
    color=Color.DARK_BLUE,
)

metric_lambda_tmp_used = Metric(
    name="lambda_tmp_used",
    title=Title("Lambda Temp Space Used"),
    unit=UNIT_BYTES,
    color=Color.DARK_GREEN,
)

metric_lambda_tmp_max = Metric(
    name="lambda_tmp_max",
    title=Title("Lambda Temp Space Available"),
    unit=UNIT_BYTES,
    color=Color.DARK_ORANGE,
)


# ----- RDS: further metrics -----
metric_rds_cpu_credit_usage = Metric(
    name="rds_cpu_credit_usage",
    title=Title("RDS CPU Credit Usage"),
    unit=UNIT_NUMBER,
    color=Color.BLUE,
)

metric_rds_cpu_credit_balance = Metric(
    name="rds_cpu_credit_balance",
    title=Title("RDS CPU Credit Balance"),
    unit=UNIT_NUMBER,
    color=Color.GREEN,
)

metric_rds_swap_usage = Metric(
    name="rds_swap_usage",
    title=Title("RDS Swap Usage"),
    unit=UNIT_BYTES,
    color=Color.ORANGE,
)

metric_rds_free_local_storage = Metric(
    name="rds_free_local_storage",
    title=Title("RDS Free Local Storage"),
    unit=UNIT_BYTES,
    color=Color.PURPLE,
)

metric_rds_read_throughput = Metric(
    name="rds_read_throughput",
    title=Title("RDS Read Throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=Color.CYAN,
)

metric_rds_write_throughput = Metric(
    name="rds_write_throughput",
    title=Title("RDS Write Throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=Color.RED,
)

metric_rds_network_receive_throughput = Metric(
    name="rds_network_receive_throughput",
    title=Title("RDS Network Receive"),
    unit=UNIT_BYTES_PER_SECOND,
    color=Color.DARK_BLUE,
)

metric_rds_network_transmit_throughput = Metric(
    name="rds_network_transmit_throughput",
    title=Title("RDS Network Transmit"),
    unit=UNIT_BYTES_PER_SECOND,
    color=Color.DARK_GREEN,
)

metric_rds_ebs_io_balance = Metric(
    name="rds_ebs_io_balance",
    title=Title("RDS EBS IO Balance"),
    unit=UNIT_PERCENTAGE,
    color=Color.DARK_ORANGE,
)

metric_rds_ebs_byte_balance = Metric(
    name="rds_ebs_byte_balance",
    title=Title("RDS EBS Byte Balance"),
    unit=UNIT_PERCENTAGE,
    color=Color.DARK_PURPLE,
)

metric_rds_replication_slot_disk_usage = Metric(
    name="rds_replication_slot_disk_usage",
    title=Title("RDS Replication Slot Disk Usage"),
    unit=UNIT_BYTES,
    color=Color.DARK_RED,
)

metric_rds_commit_latency = Metric(
    name="rds_commit_latency",
    title=Title("RDS Commit Latency"),
    unit=UNIT_TIME_MS,
    color=Color.LIGHT_BLUE,
)

metric_rds_commit_throughput = Metric(
    name="rds_commit_throughput",
    title=Title("RDS Commits per Second"),
    unit=UNIT_NUMBER,
    color=Color.LIGHT_GREEN,
)

metric_rds_aurora_binlog_replica_lag = Metric(
    name="rds_aurora_binlog_replica_lag",
    title=Title("RDS Aurora Binlog Replica Lag"),
    unit=UNIT_TIME,
    color=Color.BLUE,
)

metric_rds_aurora_replica_lag = Metric(
    name="rds_aurora_replica_lag",
    title=Title("RDS Aurora Replica Lag"),
    unit=UNIT_TIME_MS,
    color=Color.GREEN,
)
