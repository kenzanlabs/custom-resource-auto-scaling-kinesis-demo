# custom-resource-auto-scaling-kinesis-demo

### Overview

This sample code is intended to demonstrate AWS's new [Custom Resource Scaling](https://aws.amazon.com/about-aws/whats-new/2018/07/add-scaling-to-services-you-build-on-aws/) feature, by building on the mock resource stack found in [https://github.com/aws/aws-auto-scaling-custom-resource](https://github.com/aws/aws-auto-scaling-custom-resource) to dynamically increase the shard count of a kinesis stream in response to sustained heavy utilization.

### Setup:

#### Resources Created:
1. Two lambda functions:
   * A function for monitoring the utilization of a configured set of kinesis streams as a function of current shard count, incoming bytes, and incoming messages and writing those values to a custom cloudwatch metric.
   * A function for scaling a heavily utilized stream by increasing it's shard count.
2. An API Gateway resource to expose the scaling lambda to the AWS Auto-Scaling component
3. IAM roles allowing the lambdas access to cloudwatch & kinesis.

### Steps:
1. Create one or more kinesis stream to monitor & scale.
2. Enter the name of the stream in [config.py](src/config.py) configuration file.
   * Out-of-the-box the configuration file is setup to look for a test stream, kinesis-autoscale-test-1.
3. Zip up the python code under the [src](src/) directory & upload to an S3 bucket.
4. Use the aws cli to create the stack (command shown below wth region "us-east-1"):

    ```
    aws cloudformation create-stack --stack-name CustomResourceKinesisScalerStack --template-body file://./custom-resource-kinesis-scaler-stack.yaml --region us-east-1 --capabilities CAPABILITY_NAMED_IAM CAPABILITY_IAM
    ```
    
5. The creation should only take a few minutes. When complete the command below should return with "StackStatus": "CREATE_COMPLETE":

    ```
    aws cloudformation describe-stacks --region us-east-1 --stack-name CustomResourceKinesisScalerStack
    
    {
        "Stacks": [
            {
                "StackId": "arn:aws:cloudformation:us-east-1:{ACCT_ID}:stack/CustomResourceKinesisScalerStack/44c001f0-c8b5-11e8-b575-50faeaabf0d1",
                "StackName": "CustomResourceKinesisScalerStack",
                "Description": "....",
                "StackStatus": "CREATE_COMPLETE",
                "Outputs": [
                    {
                        "OutputKey": "ProdResourceIdPrefix",
                        "OutputValue": "https://{EXAMPLE-ID}.execute-api.us-east-1.amazonaws.com/prod/scalableTargetDimensions/",
                        "Description": "Application Auto Scaling Resource ID prefix for Prod."
                    },
                    {
                        "OutputKey": "S3BucketName",
                        "OutputValue": "customresourcekinesisscalerstack-s3bucket-{EXAMPLE-ID}",
                        "Description": "The location of the CloudTrail logs for API-related event history."
                    }
                ],
            }
        ]
    }    
    ```

6. Note the "OutputValue" response attribute which is the URL of your new custom resource endpoint:

   ```
   "OutputValue": "https://{EXAMPLE-ID}.execute-api.us-east-1.amazonaws.com/prod/scalableTargetDimensions/",
   ```
   
7. At this point you can submit a sample *GET* request to the resource using e.g. Postman & AWS4 requesting signing (configured in the authentication tab).  Be sure to append the name of your test kinesis stream to the URL (e.g. kinesis-autoscale-test-1):

   ```
   https://{EXAMPLE-ID}.execute-api.us-east-1.amazonaws.com/prod/scalableTargetDimensions/kinesis-autoscale-test-1
   ```

8. If successful the response should look like:

   ```
   {"scalingStatus": "Successful", "actualCapacity": 1, "version": "1.0", "scalableTargetDimensionId": "kinesis-autoscale-test-1", "desiredCapacity": 1}
   ```
   
9. Next we register the custom resource URL with the AWS application-autoscaling component:

   ```
   echo -n "https://8f1nvfnarc.execute-api.us-east-1.amazonaws.com/prod/scalableTargetDimensions/kinesis-autoscale-test-1" > ~/custom-resource-id.txt
   ```
   
   ```
   aws application-autoscaling register-scalable-target --service-namespace custom-resource --scalable-dimension custom-resource:ResourceType:Property --resource-id file://~/custom-resource-id.txt --min-capacity 1 --max-capacity 5 
   ```
   
10. Finally, we need to create a scaling policy which ties our custom resource endpoint to a cloudwatch alarm.  Our policy is defined in [custom_metric_spec.json] (custom_metric_spec.json), which instructs the scaler to target a value of 75% utilization for our target stream.  The MetricName (StreamUtilization) & Namespace (KENZAN/KinesisMonitor) match the metric written in the monitoring lambda:
 
    ```
    cat ~/custom_metric_spec.json

    {
       "TargetValue" : 75,
       "CustomizedMetricSpecification" : {
          "MetricName"  : "StreamUtilization",
          "Namespace"   : "KENZAN/KinesisMonitor",
          "Dimensions"  : [
             {
                "Name"  : "StreamName",
                "Value" : "kinesis-autoscale-test-1"
             }
          ],
          "Statistic" : "Average",
          "Unit"      : "Percent"
       }
    }
    ```
    
11. Execute the following command to create the policy:

    ```
    aws application-autoscaling put-scaling-policy --policy-name custom-tt-scaling-policy --policy-type TargetTrackingScaling --service-namespace custom-resource --scalable-dimension custom-resource:ResourceType:Property --resource-id file://~/custom-resource-id.txt --target-tracking-scaling-policy-configuration file://./custom_metric_spec.json
    ```
    
### Testing

1. We can run a batch process to put records on the target stream (a test method is included in [streams.py](src/streams.py) and allow the monitoring process to observe & record the load, or alternatively can execute:

    ```
    aws cloudwatch put-metric-data --metric-name StreamUtilization --namespace "KENZAN/KinesisMonitor" --value 80 --unit Percent --dimensions StreamName=kinesis-autoscale-test-1 
    ```
    
2. In response to the metric crossing the 75% average utilization threshold we should see the following output in response to a describe-scaling command after a few moments have passed:

    ```
    aws application-autoscaling describe-scaling-activities --service-namespace custom-resource --resource-id file://~/custom-resource-id.txt --max-results 5
    ```
    
    ```
    {
        "ScalingActivities": [
            {
                "ScalableDimension": "custom-resource:ResourceType:Property", 
                "Description": "Setting desired capacity to 2.", 
                "ResourceId": "https://{EXAMPLE-ID}.execute-api.us-east-1.amazonaws.com/prod/scalableTargetDimensions/kinesis-autoscale-test-1", 
                "Cause": "monitor alarm TargetTracking-https://{EXAMPLE-ID}.execute-api.us-east-1.amazonaws.com/prod/scalableTargetDimensions/kinesis-autoscale-test-1-AlarmHigh-d202dad6-d819-4c2e-8b7c-df184e16c47b in state ALARM triggered policy custom-tt-scaling-policy", 
                ...
            }
        ]
    }
    ```
 
