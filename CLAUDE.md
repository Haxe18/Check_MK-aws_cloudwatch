# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Checkmk plugin for monitoring AWS CloudWatch metrics using the free GetMetricStatistics API (1M requests/month). Monitors CloudFront, RDS, EBS, ELB, Lambda, EC2, S3, DynamoDB across multiple AWS regions.

## Build Commands

```bash
# Build MKP package (requires the Check_MK-plugin_mpk_action repo next to this one)
../Check_MK-plugin_mpk_action/scripts/build_plugin.sh \
  --plugin-name aws_cloudwatch \
  --title "AWS CloudWatch Monitoring" \
  --description "Checkmk plugin for monitoring AWS CloudWatch metrics" \
  --version 1.0.0 \
  --usable-until 3.0.0   # same as usable_until in .github/workflows/release_aws_cloudwatch.yml

# Test agent locally (as site user: needs boto3, setproctitle and cmk from the site)
./aws_cloudwatch/libexec/agent_aws_cloudwatch \
  --access-key AKIA... \
  --secret-key ... \
  --cloudwatch-regions-map '{"us-east-1": ["cloudfront"], "eu-central-1": ["dynamodb"]}'

# GitHub release (triggers workflow)
git tag v1.0.0
git push origin v1.0.0
```

## Debug Logging

`AWS_CLOUDWATCH_DEBUG=1` enables detailed logging on stderr (values: `1|true|yes`).
Loggers centrally configured in `aws_cloudwatch/lib/logger.py` (`aws_cloudwatch.*` hierarchy).
Debug lines show `[region:service]` (thread name set per task in `CloudWatchOrchestrator._run_service_task()`).

## Architecture

This is a Checkmk 2.4+ special agent plugin with these components:

```
aws_cloudwatch/
├── libexec/agent_aws_cloudwatch          # Special agent executable (boto3)
├── agent_based/
│   ├── aws_cloudwatch.py                 # Main parser + API counter check
│   ├── aws_cloudwatch_helpers.py         # Factory pattern + shared helpers
│   └── aws_cloudwatch_*.py               # Service-specific checks (11 files)
├── rulesets/
│   ├── aws_cloudwatch.py                 # Main agent WATO config
│   ├── aws_cloudwatch_helpers.py         # Form spec helpers
│   ├── ruleset_generator.py              # Factory for generating rulesets
│   └── aws_cloudwatch_*.py               # Service threshold rules (11 files)
├── lib/
│   ├── base.py                           # Abstract base: name, title, namespace, metrics
│   ├── threshold_types.py                # ThresholdDef, ThresholdType
│   └── services/                         # Service section implementations (each has name + title)
├── server_side_calls/special_agent_...   # WATO -> CLI argument mapping
└── graphing/aws_cloudwatch.py            # Metrics/graphs definition
```

**Data Flow:**
1. WATO rule (`rulesets/`) -> `server_side_calls/` transforms config to CLI args
2. `libexec/agent_aws_cloudwatch` fetches metrics via boto3, outputs `<<<aws_cloudwatch:sep(0)>>>` JSON
3. `agent_based/` parses JSON, discovers services, checks values

**Key Design:**
- Multi-region support: regions_services_map = `{"region": ["service1", "service2"]}`
- Per-region caching in `var_dir/agent_aws_cloudwatch/` (`$OMD_ROOT/var/check_mk/...`, survives site restarts, unlike the tmpfs `tmp_dir`)
- Parallel collection (`lib/orchestrator.py`, `ServiceTask`): one thread pool over all region/service pairs (`--max-workers`, 1–10 in WATO; if unset, the agent uses min(4, 2 × CPUs); 1 = sequential); each task has its own `APICounter`/`ErrorCollector`, merged in config order afterwards so output is deterministic
- Service definitions in `lib/services/` with `SECTION_REGISTRY` dict and region constraints
- API counter tracks usage against 1M free tier via AWS FreeTier API (with per-service breakdown); Free Tier API failures surfaced as visible WARN via ErrorCollector
- Config-key based cache invalidation, per service (`CloudWatchOrchestrator._service_config_key()`: `CACHE_FORMAT_VERSION` + service name + its enabled opt-in options; bump `CACHE_FORMAT_VERSION` when cached data changes shape); other services in the region do not affect a service's cache
- **Smart Filtering:** Validates discovered resources against AWS APIs (CloudFront Functions, EC2, RDS) to remove deleted items
- **Per-service opt-in options:** `CloudWatchOrchestrator._section_options` maps service name -> constructor kwargs of its section; enabled options are appended to the cache config_key and reported as `CloudWatchAPIConfig.section_options` (the CloudFront check uses it to explain missing description/URL)
- **CloudFront metadata is opt-in** (`--cloudfront-metadata`, WATO `cloudwatch_cloudfront_metadata`, default off): `ListDistributions` also returns origin custom headers in clear text (`CloudFrontSection.fetch_metadata`); the check-level "Show Comment/URL" options depend on it
- **Lambda filtering is opt-in** (`--lambda-filter-deleted`, WATO `cloudwatch_lambda_filter_deleted`, default off): `lambda:ListFunctions` returns all function env vars in clear text, so the Lambda API is not called unless enabled (`LambdaSection.filter_deleted`). Never add AWS calls whose response carries secrets without making them opt-in
- **Idle skipping:** metrics with `MetricDefinition.skip_idle` (all Lambda and Lambda Insights metrics, DynamoDB latency, ALB/NLB target health) count as 0 without an API call when they had no data in the past 3 hours. `CloudWatchSection.fetch_all_metrics()` calls ListMetrics with `RecentlyActive=PT3H` once per refresh (`_list_active_combos()`, keyed by resource, metric and extra-dimension value), `_is_idle()` decides per call. On error, or when the lookback (metrics cache TTL) exceeds 3h, it fetches everything; S3 is never skipped (it publishes daily and would look idle). Not for metrics that report only now and then and must alert (DynamoDB SystemErrors): ListMetrics lists new data with a delay
- **Metrics with a second dimension:** `MetricDefinition.extra_dimension` (e.g. `TargetGroup` for ALB/NLB health, `Operation` for DynamoDB latency/system errors, `StorageType` for S3). Discovery stores the values seen in ListMetrics in `Resource.metric_dimensions`; `CloudWatchSection._fetch_combined_metric()` fetches once per value and merges (`combine`: sum or max); the single values go along as `MetricResult.parts` (the ALB/NLB check applies its unhealthy levels to the worst target group, `_worst_target_group()` in `agent_based/aws_cloudwatch_helpers.py`). Querying such a metric with the primary dimension alone returns no data. Idle combinations are skipped as described above. The values are learned at discovery, so new ones are fetched only after the next discovery
- **Metrics refresh shortly before the TTL ends:** the agent runs at fixed intervals, so a cache that expires only after the TTL would still be valid at the run one TTL later and the refresh would slip one run, while the query window stays one TTL long (time in between never queried). The metrics cache therefore counts from the start of the fetch (`window_end`) and is refreshed `METRICS_REFRESH_GRACE_SECONDS` before the TTL ends. The API forecast uses the measured time between two fetches (`CloudWatchOrchestrator._refresh_interval()`, `refresh_interval` in the metrics cache) when the agent interval does not divide the TTL
- **Every fetched metric is checked:** a metric added to a section in `lib/services/` needs a spec in its check, else it costs API calls for nothing. Secondary metrics are `InfoMetricSpec(details_only=True)` (service details and graph, no thresholds)
- Metrics fetches with errors are cached with their errors (`metrics_errors`) and retried after `METRICS_ERROR_RETRY_SECONDS` (1h, at least the cache TTL) instead of the service TTL; the API forecast then uses that interval
- Error collection via `lib/errors.py` (ErrorCollector class)
- IAM permission hints via `lib/iam_hints.py` (shows required permissions on access errors)

**Check Plugin Factory Pattern (`agent_based/aws_cloudwatch_helpers.py`):**
- `MetricSpec` / `InfoMetricSpec`: Declarative metric definitions
- `CheckConfig`: Plugin configuration (service_key, metrics, hooks)
- `create_cloudwatch_check()`: Factory that generates CheckPlugin instances
- Reduces per-service boilerplate from ~150 to ~50 lines

**Ruleset Factory Pattern (`rulesets/ruleset_generator.py`):**
- `ThresholdDef`: Declarative threshold definitions (key, title, type, direction)
- `generate_rule_spec()`: Factory that generates CheckParameters from definitions
- Threshold types: PERCENT, FLOAT, MILLISECONDS, SECONDS, DATASIZE, DATASIZE_LARGE

## AWS Service Constraints

- CloudFront and CloudFront Functions: **us-east-1 only** (AWS requirement)
- Lambda@Edge: metrics in creation region, not us-east-1
- All other services: any region

## Key Constants

- `CLOUDWATCH_FREE_TIER_LIMIT = 1_000_000` in `lib/threshold_types.py` (single source of truth; used in orchestrator, WATO ruleset texts, and check plugin)
- `region_constraints` property in service section classes (`lib/services/`)
- Service sections have `name` (internal key) and `title` (human-readable) properties
- Default cache TTL: 300s
- `force_over_limit` config: disables forecast percentage display and WARN/CRIT thresholds in API counter check

## Checkmk Plugin Patterns

- Use `cmk.rulesets.v1` for WATO forms
- Use `cmk.agent_based.v2` for check plugins
- Use `cmk.server_side_calls.v1` for parameter mapping
- Password fields require `migrate_to_password`; pass the `Secret` itself (not `.unsafe()`) so Checkmk hands over `<password id>:<password store file>` instead of the secret, and read it in the agent with `cmk.utils.password_store.lookup()` (`read_secret_key()` in `libexec/agent_aws_cloudwatch`). `--secret-key` with the plain key stays for manual tests
