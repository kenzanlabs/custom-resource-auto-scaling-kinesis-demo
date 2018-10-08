streams = [{'name': 'kinesis-autoscale-test-1', 'maxShards': 10}]

stream_utilization_metric_namespace = 'KENZAN/KinesisMonitor'
stream_utilization_metric_name      = 'StreamUtilization'

shard_max_bytes_per_min             = 2 * 1024 * 1024
shard_max_records_per_min           = 1000

# Note: this should match the ScheduledExpression parameter for the LambdaMonitorScheduledRule cloudformation rule.
monitor_period_in_secs              = 600