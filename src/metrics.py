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
        Period     = 120,
        StartTime  = datetime.datetime.utcnow() - datetime.timedelta(seconds=120),
        EndTime    = datetime.datetime.utcnow(),
        MetricName = metric_name,
        Namespace  = 'AWS/Kinesis',
        Statistics = ['Sum',],
        Dimensions = [{'Name':'StreamName', 'Value':stream["name"]}]
    )    
    # {u'Datapoints': [{u'Timestamp': datetime.datetime(2018, 9, 28, 19, 6, tzinfo=tzlocal()), u'Average': 1.0, u'Sum': 4.0, u'Unit': 'Count'}], 'ResponseMetadata': {'RetryAttempts': 0, 'HTTPStatusCode': 200, 'RequestId': 'efc08917-c351-11e8-b767-a1f10b71814b', 'HTTPHeaders': {'x-amzn-requestid': 'efc08917-c351-11e8-b767-a1f10b71814b', 'date': 'Fri, 28 Sep 2018 19:08:51 GMT', 'content-length': '519', 'content-type': 'text/xml'}}, u'Label': 'IncomingRecords'}
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