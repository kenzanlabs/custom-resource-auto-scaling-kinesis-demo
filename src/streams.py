from uuid import uuid4
import config as cfg
import json
import boto3

kinesis = boto3.client('kinesis')

STATUS_CREATING = 'CREATING'
STATUS_DELETING = 'DELETING'
STATUS_ACTIVE   = 'ACTIVE'
STATUS_UPDATING = 'UPDATING'

def get_current_status_and_shard_count(stream):
    shard_counter = 0
    last_shard    = None
    stream_info   = None
    stream_status = None
    
    while True:
        if last_shard: 
            stream_info = kinesis.describe_stream(
                StreamName            = stream["name"], 
                ExclusiveStartShardId = last_shard)
        else:
            stream_info = kinesis.describe_stream(StreamName = stream["name"])
            stream_status = stream_info['StreamDescription']['StreamStatus']
        num_shards   = len(stream_info['StreamDescription']['Shards'])
        shard_counter = shard_counter + num_shards
        last_shard = stream_info['StreamDescription']['Shards'][num_shards - 1]['ShardId']
        if not stream_info['StreamDescription']['HasMoreShards']:
            break
    return (stream_status, shard_counter)

def update_shard_count(stream, target_shard_count):
    update_response = kinesis.update_shard_count(
        StreamName = stream["name"],
        TargetShardCount = target_shard_count,
        ScalingType='UNIFORM_SCALING'
    )
    # {'StreamName': 'string', 'CurrentShardCount': 123, 'TargetShardCount': 123 }
    return update_response

def put_test_record(stream):
    for i in range(50):
        kinesis.put_record(
            StreamName   = stream["name"],
            Data         = json.dumps({'val':str(uuid4())}),
            PartitionKey = str(uuid4()))