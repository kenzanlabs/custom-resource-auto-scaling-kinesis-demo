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

# This operation has the following default limits. By default, you cannot do the following:
#    Scale more than twice per rolling 24-hour period per stream
#    Scale up to more than double your current shard count for a stream
#    Scale down below half your current shard count for a stream
#    Scale up to more than 500 shards in a stream
#    Scale a stream with more than 500 shards down unless the result is less than 500 shards
#    Scale up to more than the shard limit for your account
# See: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/kinesis.html#client    
#
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