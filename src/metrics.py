import config as cfg
import datetime
import boto3

cloudwatch = boto3.client('cloudwatch')

def get_incoming_records(stream, period_in_secs):
    return get_metric_sum(stream, period_in_secs, 'IncomingRecords')

def get_incoming_bytes(stream, period_in_secs):
    return get_metric_sum(stream, period_in_secs, 'IncomingBytes')

def get_metric_sum(stream, period_in_secs, metric_name):
    data_points = cloudwatch.get_metric_statistics(
        Period     = period_in_secs,
        StartTime  = datetime.datetime.utcnow() - datetime.timedelta(seconds=period_in_secs),
        EndTime    = datetime.datetime.utcnow(),
        MetricName = metric_name,
        Namespace  = 'AWS/Kinesis',
        Statistics = ['Sum',],
        Dimensions = [{'Name':'StreamName', 'Value':stream["name"]}]
    )    
    if data_points["Datapoints"] and len(data_points["Datapoints"]) > 0:
        return data_points["Datapoints"][0]["Sum"]
    else:
        return 0

def put_stream_utilization_metric(stream, utilization_pct):
    cloudwatch.put_metric_data(
        Namespace  = cfg.stream_utilization_metric_namespace,
        MetricData = [{
            'MetricName' : cfg.stream_utilization_metric_name,
            'Dimensions' : [{'Name': 'StreamName', 'Value': stream["name"]}],
            'Timestamp'  : datetime.datetime.utcnow(),
            'Value'      : utilization_pct,
            'Unit'       : 'Percent',
            'StorageResolution': 60
        }]
    )