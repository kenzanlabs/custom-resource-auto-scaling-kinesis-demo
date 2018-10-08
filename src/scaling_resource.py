import boto3
import json
import datetime
import config as cfg
import streams
import metrics

STATUS_PENDING     = "Pending"    # scaling action has not yet begun
STATUS_IN_PROGRESS = "InProgress" # scaling action is in progress
STATUS_SUCCESSFUL  = "Successful" # last scaling action was successful
STATUS_FAILED      = "Failed"     # last scaling action has failed

def lambda_handler(event, context):
    operations = {
        'GET': get,
        'PATCH': patch
    }
    operation = event['httpMethod']
    error = None
    response = None
    
    if operation in operations:
        stream = scalable_target_dimension_id_to_stream(event['pathParameters']['scalableTargetDimensionId'])
        if stream is None:
            return respond('Unknown stream "{}"'.format(event['pathParameters']['scalableTargetDimensionId']))
        if operation == 'GET':
            error, response = get(stream)
        else:  # PATCH
            scalable_target_dimension_update = json.loads(event['body'])
            error, response = patch(stream, scalable_target_dimension_update)
        return respond(error, response)
    else:
        return respond('Unsupported HTTP method "{}"'.format(operation))

def scalable_target_dimension_id_to_stream(scalable_target_dimension_id):
    matching_streams = filter(lambda stream: stream['name'] == scalable_target_dimension_id, cfg.streams)
    if len(matching_streams) == 0:
        return None
    else:
        return matching_streams[0]

def respond(error, response=None):
    print("res=%s, err=%s" % (str(response), str(error)))
    return {
        'statusCode': 400   if error else 200,
        'body'      : error if error else response,
        'headers'   : {
            'Content-Type': 'application/json',
        },
    }

def patch(stream, scalable_target_dimension_update):
    desired_capacity = scalable_target_dimension_update["desiredCapacity"]
    stream_status, shard_count = streams.get_current_status_and_shard_count(stream)
    if stream_status == streams.UPDATING:
        # Update already in progress
        return (None,json.dumps({'scalableTargetDimensionId':stream["name"], 'scalingStatus':STATUS_IN_PROGRESS,'actualCapacity':shard_count,'desiredCapacity':desired_capacity, 'version':'1.0'}))
    elif stream_status != streams.STATUS_ACTIVE:
        # Creating | Deleting
        return ('Error: stream not in scalable state: {}.'.format(stream_status), None)
    # Stream in ACTIVE state, attempt to update shard count...
    if desired_capacity < shard_count:
        # Downscaling not supported.
        return (None,json.dumps({'scalableTargetDimensionId':stream["name"], 'scalingStatus':STATUS_FAILED,'actualCapacity':shard_count,'desiredCapacity':desired_capacity, 'version':'1.0'}))
    if desired_capacity > stream["maxShards"]:
        # Stream already at maximum allowed number of shards.
        return (None,json.dumps({'scalableTargetDimensionId':stream["name"], 'scalingStatus':STATUS_FAILED,'actualCapacity':shard_count,'desiredCapacity':desired_capacity, 'version':'1.0'}))
    print("streams.update_shard_count(%s, %d)" % (stream["name"], int(desired_capacity)))
    streams.update_shard_count(stream, int(desired_capacity))
    return (None,json.dumps({'scalableTargetDimensionId':stream["name"], 'scalingStatus':STATUS_IN_PROGRESS,'actualCapacity':shard_count,'desiredCapacity':desired_capacity, 'version':'1.0'}))

def get(stream):
    stream_status, shard_count = streams.get_current_status_and_shard_count(stream)
    scaling_status = None
    if stream_status == streams.STATUS_ACTIVE:
        scaling_status = STATUS_SUCCESSFUL
    elif stream_status == streams.STATUS_UPDATING or stream_status == streams.STATUS_CREATING:
        scaling_status = STATUS_IN_PROGRESS
    elif stream_status == streams.STATUS_DELETING:
        scaling_status = STATUS_FAILED
    return (None, json.dumps({'scalableTargetDimensionId':stream["name"], 'scalingStatus':scaling_status,'actualCapacity':shard_count,'desiredCapacity':shard_count, 'version':'1.0'}))