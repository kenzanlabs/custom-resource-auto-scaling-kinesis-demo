import boto3
import json
import datetime
import config as cfg
import streams
import metrics

def lambda_handler(event, context):
    for stream in cfg.streams:
        # put_test_record(stream)
        stream_utilization = calculate_stream_utilization(stream, cfg.monitor_period_in_secs)
        metrics.put_stream_utilization_metric(stream, stream_utilization)
        print(stream_utilization)
    return {
        "statusCode": 200,
        "body": json.dumps('OK')
    }

def calculate_stream_utilization(stream, period_in_secs):
    status, number_of_shards  = streams.get_current_status_and_shard_count(stream)
    number_of_records         = metrics.get_incoming_records(stream, period_in_secs)
    number_of_bytes           = metrics.get_incoming_bytes(stream, period_in_secs)
    
    records_per_min = (60.0 * number_of_records) / (period_in_secs)
    bytes_per_min   = (60.0 * number_of_bytes)   / (period_in_secs)    
    
    record_utilization_pct   = 100 * ((records_per_min / (1.0 * cfg.shard_max_records_per_min)) / number_of_shards)
    byte_utilization_pct     = 100 * ((bytes_per_min   / (1.0 * cfg.shard_max_bytes_per_min  )) / number_of_shards)
    
    print("Stats for stream %s with %d shards - records_per_min: %10.2f, bytes_per_min: %10.2f, record_pct_capacity: %3.2f, byte_pct_capacity: %3.2f" % (stream["name"], number_of_shards, records_per_min, bytes_per_min, record_utilization_pct, byte_utilization_pct))
    return max(record_utilization_pct, byte_utilization_pct)
