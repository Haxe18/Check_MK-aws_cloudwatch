# CheckMK AWS CloudWatch Monitoring

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)

Monitors CloudWatch metrics using the cost-free GetMetricStatistics API (1M requests/month free).

## Features

- **100% Free Tier**: Uses only GetMetricStatistics API (1M requests/month free) - no costs
- **Data Collection Only**: No default thresholds - all services report OK by default
- **Optional Alerting**: Configure warning/critical levels per service type via WATO rules
- **Multi-Region Support**: Monitor resources across multiple AWS regions simultaneously
- **11 AWS Services**: CloudFront, RDS, EBS, ELB, ALB, NLB, Lambda, Lambda Insights, EC2, S3, DynamoDB
- **API Usage Tracking**: Monthly forecast with per-service breakdown; Free Tier API failure surfaced as visible warning
- **Automatic Discovery**: Discovers resources automatically via list_metrics()
- **Smart Filtering**: Automatically filters out deleted resources (Lambda, Lambda@Edge, EC2, RDS, CloudFront Functions) to save API calls
- **Error Reporting**: Aggregates and displays API errors with IAM permission hints
- **Smart Caching**: Config-aware cache invalidation when settings change

## Supported Services

All metrics are collected using the **free** GetMetricStatistics API.

| Service | Metrics | Region |
|---------|---------|--------|
| **CloudFront** | Requests, BytesDownloaded, ErrorRates, CacheHitRate | us-east-1 only |
| **CloudFront Functions** | Invocations, ComputeUtilization, Errors | us-east-1 only |
| **Lambda** | Invocations, Errors, Duration, Throttles, ConcurrentExecutions | Any region |
| **Lambda Insights** | MemoryUtilization, CPUTime, NetworkIO, ColdStarts | Any region |
| **DynamoDB** | ReadCapacity, WriteCapacity, Throttles, Latency | Any region |
| **RDS** | CPU, Connections, FreeableMemory, FreeStorageSpace, ReplicaLag | Any region |
| **EC2** | CPU, Network, Disk, StatusChecks, CPUCreditBalance | Any region |
| **EBS** | ReadOps, WriteOps, Throughput, QueueLength, BurstBalance | Any region |
| **ELB Classic** | Latency, HealthyHosts, UnHealthyHosts | Any region |
| **ALB** | ResponseTime, ActiveConnections, HealthyTargets | Any region |
| **NLB** | ActiveFlows, ProcessedBytes, HealthyTargets | Any region |
| **S3** | BucketSizeBytes, NumberOfObjects | Any region |

## Alerting / Thresholds

By default, this plugin **only collects metrics** - no alerts are triggered.

### Default Behavior
- All services report **OK** status
- Metrics are collected and graphed in Checkmk
- No warning or critical thresholds are applied

### Configuring Alerts
To enable alerting, configure thresholds via WATO rules:

1. Go to **Setup → Services → Service monitoring rules**
2. Search for "AWS CloudWatch" rules:
   - AWS CloudWatch EC2
   - AWS CloudWatch RDS
   - AWS CloudWatch Lambda
   - AWS CloudWatch DynamoDB
   - AWS CloudWatch EBS
   - AWS CloudWatch S3
   - AWS CloudWatch ELB Classic
   - AWS CloudWatch ALB
   - AWS CloudWatch NLB
   - AWS CloudWatch CloudFront
   - AWS CloudWatch CloudFront Functions
3. Create a rule and configure warning/critical levels for the metrics you want to alert on

**Example**: Alert when RDS CPU > 80% (warn) / 90% (crit):
- Create rule for "AWS CloudWatch RDS"
- Set "CPU Utilization (%)" → Warning at 80, Critical at 90

## Required IAM Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "CloudWatchMonitoring",
            "Effect": "Allow",
            "Action": [
                "cloudwatch:GetMetricStatistics",
                "cloudwatch:ListMetrics",
                "freetier:GetFreeTierUsage",
                "lambda:ListFunctions",
                "cloudfront:ListFunctions",
                "ec2:DescribeInstances",
                "rds:DescribeDBInstances"
            ],
            "Resource": "*"
        },
        {
            "Sid": "DenyCostlyCloudWatch",
            "Effect": "Deny",
            "Action": ["cloudwatch:GetMetricData"],
            "Resource": "*"
        }
    ]
}
```

| Permission | Purpose |
|---|---|
| `cloudwatch:GetMetricStatistics` | Fetch metrics (free tier API) |
| `cloudwatch:ListMetrics` | Discover resources |
| `freetier:GetFreeTierUsage` | Show actual AWS API usage in the "CloudWatch API Status" check |
| `lambda:ListFunctions` | Smart Filtering – remove deleted Lambda & Lambda@Edge functions |
| `cloudfront:ListFunctions` | Smart Filtering – remove deleted CloudFront Functions |
| `ec2:DescribeInstances` | Smart Filtering – remove terminated EC2 instances |
| `rds:DescribeDBInstances` | Smart Filtering – remove deleted RDS instances |
| `cloudwatch:GetMetricData` (Deny) | Block the expensive paid API (not used by this plugin) |

**Note**: Smart Filtering permissions (`lambda:ListFunctions`, `cloudfront:ListFunctions`, `ec2:DescribeInstances`, `rds:DescribeDBInstances`) are optional – without them the plugin still works but deleted resources may remain visible until the discovery cache expires. Missing permissions are reported as WARN in the "CloudWatch API Status" check with the required permission name.

## Configuration

1. Go to **Setup → Agents → VM, Cloud, Container → Amazon CloudWatch Monitoring**
2. Configure:
   - AWS Access Key ID
   - AWS Secret Access Key
   - **Regions**: Add multiple regions, each with its own service selection
   - Cache TTL (default: 300s per region)
     - Note: S3 metrics are forced to 24h interval (independent of this global TTL)
   - API Warning Threshold (default: 80%)
   - API Critical Threshold (default: 90%)
   - **Free Tier Limit (1M requests/month)**: Stop or continue when limit reached
     - When stopped, service checks show OK "monitoring paused" instead of UNKNOWN
   - Parallel Threads (range 1–10): How many region/service pairs are fetched at the same time; 1 = one after another. If not set: min(4, 2 × CPUs of the machine running the agent)

## Services Discovered

- **CloudWatch {region} {SERVICE} {resource} - {metric}**: One per CloudWatch metric
- **CloudWatch API Status**: Monthly API forecast with calculation details, including weighted calls/check breakdown per service and TTL group totals with service names

## Installation

### From GitHub Releases
1. Download the MKP file from [Releases](https://github.com/Haxe18/Check_MK-aws_cloudwatch/releases)
2. Upload via **Setup → Extension Packages → Upload package**

### Via Command Line
```bash
mkp install aws_cloudwatch-1.0.0.mkp
```

## Build & Release

### Local Build
```bash
./build_aws_cloudwatch.sh [version]
```

### GitHub Release
```bash
git tag v1.0.0
git push origin v1.0.0
```

## Free Tier Protection

By default, monitoring **stops automatically** when the 1M free tier limit is reached to prevent AWS costs.

### Limit Behavior Options

| Option | Behavior |
|--------|----------|
| **Stop monitoring at 1M free tier limit** (default) | No API calls when limit reached - minimize costs |
| **Continue monitoring beyond free tier** | Accept AWS costs ($0.01/1000 requests), API forecast thresholds disabled |

When monitoring is stopped:
- All services report OK with "Free tier limit reached – monitoring paused"
- Services stay discovered: the agent reports the last known resources from its metrics cache (stored in `~/var/check_mk/agent_aws_cloudwatch/`, so it survives site restarts and reboots)
- "CloudWatch API Status" shows CRIT with "Monitoring stopped"
- No new API calls are made until next month

When "Continue monitoring" is active:
- API forecast shows `Monthly forecast: X API calls` (no percentage, no WARN/CRIT)
- Monitoring continues regardless of usage

When the Free Tier API is unavailable (e.g. missing `freetier:GetFreeTierUsage` permission), a visible WARN is shown in the "CloudWatch API Status" check with the required IAM permission hint. This prevents silent limit protection failure.

To enable force mode:
1. Edit the AWS CloudWatch rule
2. Set "Free Tier Limit (1M requests/month)" to "Continue monitoring beyond free tier"

## Cost Analysis

| API | Free Tier | Cost After | This Plugin |
|-----|-----------|------------|-------------|
| **GetMetricData** (Check_MK upstream) | None | $0.01/1000 | Not used |
| **GetMetricStatistics** (this plugin) | 1M/month | $0.01/1000 | **$0.00** |

### Example: 5 CloudFront + 3 DynamoDB tables (5-min intervals)
```
CloudFront:  ~259,200 API calls/month
DynamoDB:    ~155,520 API calls/month
ListMetrics:   ~1,440 API calls/month
─────────────────────────────────────
Total:       ~416,160 API calls/month (41.6% of free tier)
Cost:        $0.00
```

## Architecture

```
┌────────────────────────────────────────────────────────┐
│ aws_cloudwatch Plugin                                  │
│                                                        │
│  WATO Rule → libexec/agent_aws_cloudwatch              │
│      ↓                                                 │
│  Multi-Region CloudWatch API (cached 300s per region)  │
│    - S3 metrics forced to 24h TTL for API optimization │
│      ├─→ list_metrics() - Discover resources           │
│      └─→ get_metric_statistics() - Fetch metrics       │
│      ↓                                                 │
│  <<<aws_cloudwatch>>> JSON                             │
│      ↓                                                 │
│  agent_based/aws_cloudwatch.py → Services + Metrics    │
└────────────────────────────────────────────────────────┘
```

## Project Structure

```
aws_cloudwatch/
├── libexec/agent_aws_cloudwatch          # Special agent executable
├── agent_based/                          # Check plugins
│   ├── aws_cloudwatch.py                 # Main parser + API counter check
│   ├── aws_cloudwatch_helpers.py         # Factory pattern + shared helpers
│   ├── aws_cloudwatch_ec2.py             # EC2 checks (uses factory)
│   ├── aws_cloudwatch_rds.py             # RDS checks (uses factory)
│   └── aws_cloudwatch_*.py               # Other service checks (10 total)
├── rulesets/                             # WATO configuration forms
│   ├── aws_cloudwatch.py                 # Main agent rule
│   ├── aws_cloudwatch_helpers.py         # Form spec helpers
│   ├── ruleset_generator.py              # Factory for generating rulesets
│   └── aws_cloudwatch_*.py               # Service threshold rules (10 total)
├── lib/                                  # Core library modules
│   ├── base.py                           # Abstract base section class
│   ├── client.py                         # AWS API client wrappers
│   ├── cache.py                          # Caching + API counter
│   ├── errors.py                         # Error collection utilities
│   ├── iam_hints.py                      # IAM permission hints for errors
│   ├── logger.py                         # Logging configuration
│   ├── orchestrator.py                   # Multi-region coordinator
│   ├── threshold_types.py                # Threshold definitions for rulesets
│   ├── types.py                          # Data types
│   └── services/                         # Service section implementations
│       ├── cloudfront.py
│       ├── compute.py                    # EC2
│       ├── database.py                   # RDS
│       └── ...
├── graphing/aws_cloudwatch.py            # Metrics/graphs definitions
├── server_side_calls/special_agent_...   # WATO → CLI mapping
└── checkman/aws_cloudwatch               # Service documentation
```

## Testing

```bash
./aws_cloudwatch/libexec/agent_aws_cloudwatch \
  --access-key AKIA... \
  --secret-key wJal... \
  --cloudwatch-regions-map '{"us-east-1": ["cloudfront"], "eu-central-1": ["dynamodb"]}'
```

## Debug Logging

By default, the agent only outputs warnings and errors to stderr. To enable detailed debug output, set the environment variable:

```bash
AWS_CLOUDWATCH_DEBUG=1 ./aws_cloudwatch/libexec/agent_aws_cloudwatch \
  --access-key AKIA... \
  --secret-key ... \
  --cloudwatch-regions-map '{"us-east-1": ["cloudfront"]}' 2>&1 | tee debug.log
```

Accepted values: `1`, `true`, `yes` (case-insensitive).

| Logger | File | Content |
|--------|------|---------|
| `aws_cloudwatch.orchestrator` | orchestrator.py | Region/service coordination, caching |
| `aws_cloudwatch.base` | base.py | API calls, discovery, metrics |
| `aws_cloudwatch.cache` | cache.py | Cache hits/misses, invalidation |
| `aws_cloudwatch.client` | client.py | FreeTier API errors |
| `aws_cloudwatch.compute` | services/compute.py | EC2 filtering |
| `aws_cloudwatch.database` | services/database.py | RDS filtering |
| `aws_cloudwatch.serverless` | services/serverless.py | Lambda filtering |
| `aws_cloudwatch.cloudfront` | services/cloudfront.py | CloudFront filtering |

## Troubleshooting

### No Services Discovered
- Check IAM permissions
- Verify AWS credentials are correct
- Check at least one region has services selected

### CloudFront Not Working
- CloudFront and CloudFront Functions **must** use us-east-1 (AWS requirement)
- Smart Filtering for CloudFront Functions requires `cloudfront:ListFunctions` IAM permission – without it, deleted functions remain visible

### Lambda@Edge Not Showing
- Lambda@Edge metrics appear in the **creation region** (e.g., eu-central-1), not us-east-1
- Use `aws_lambda` service (not cloudfront_functions)

### API Usage Too High
- Increase cache TTL (300s → 600s)
- Monitor fewer services/regions
- Check "CloudWatch API Status" service for monthly forecast details
- Use the "Weighted calls/check breakdown" in details to see per-service impact and overridden/default TTL totals with service names
- Review per-service breakdown in agent output to identify high-cost services

### S3 Shows Delayed Updates
- S3 storage metrics are published daily by AWS
- S3 metric TTL is set to 24h to match AWS daily publication cadence
- Bucket Size is calculated as the sum across bucket storage classes
- NumberOfObjects is read using `AllStorageTypes`

### Errors Displayed in Check Output
- Errors are aggregated and shown as WARN status
- **IAM permission hints** are shown automatically for access errors (e.g., "Required: cloudwatch:ListMetrics")
- Check the details for specific service/region that failed
- Common causes: IAM permissions, throttling, network issues

### Services Without Resources
- Shown as informational message (OK status) with human-readable service names
- Usually indicates no resources exist for that service in the region
- If unexpected, verify IAM permissions allow `cloudwatch:ListMetrics`
- Access errors will show the required permission in the error message

## License

WTFPL (Do What The Fuck You Want To Public License)

## Contributing

Pull requests welcome! Please ensure code follows existing style and includes documentation.
