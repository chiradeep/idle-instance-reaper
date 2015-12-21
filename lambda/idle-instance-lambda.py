from __future__ import print_function
import argparse
import boto3
import datetime
from dateutil.tz import tzutc
import logging

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

print('Loading function')

REGIONS=['us-west-2', 'us-west-1', 'us-east-1', 'eu-west-1', 'eu-central-1', 'ap-southeast-1']
TAGKEY='instance-purpose'
TAG_VALUES='test,ephemeral'
IDLE_PERIOD_SECS=86400
MIN_CPU_UTIL=0.03

def is_in_autoscale_group(region, instance_id):
    asg = boto3.client('autoscaling', region_name=region)
    instances = \
        asg.describe_auto_scaling_instances(InstanceIds=[instance_id])
    inst_status = instances['AutoScalingInstances']
    if inst_status:
        logger.info("Instance %s is in autoscale group %s"
                    % (instance_id, inst_status[0]['AutoScalingGroupName']))
        return True
    return False


def stop_idle_instances(region, tag_key, tag_values,
                        idle_period_secs, minimum):
    ec2 = boto3.client('ec2', region_name=region)
    ec2res = boto3.resource('ec2', region_name=region)
    c = boto3.client('cloudwatch', region_name=region)
    values = tag_values.split(",")
    filters = []
    if tag_key:
        f0 = {}
        f0['Name'] = "tag:{}".format(tag_key)
        f0['Values'] = values
        filters.append(f0)

    f1 = {}
    f1['Name'] = 'instance-state-name'
    f1['Values'] = ['running']
    filters.append(f1)
    # print filters
    rs = ec2.describe_instances(Filters=filters)
    now = datetime.datetime.now(tzutc())
    lookback = datetime.timedelta(seconds=idle_period_secs)
    time_start = now - lookback
    # print rs['Reservations']
    for r in rs['Reservations']:
        for i in r['Instances']:
            launch_time = i['LaunchTime']
            if is_in_autoscale_group(region, i['InstanceId']):
                continue
            age = now - launch_time
            if age < datetime.timedelta(seconds=idle_period_secs):
                logger.info("Age of instance %s = %s, less than %s" %
                            (i['InstanceId'], str(age), str(lookback)))
                continue
            dim = [{'Name': 'InstanceId', 'Value': i['InstanceId']}]
            period = idle_period_secs - (idle_period_secs % 60)
            if period < 60:
                period = 60
            metric = c.get_metric_statistics(Period=period,
                                             StartTime=time_start,
                                             EndTime=now,
                                             MetricName='CPUUtilization',
                                             Namespace='AWS/EC2',
                                             Statistics=['Average'],
                                             Dimensions=dim)
            # print metric
            if metric['Datapoints']:
                average = metric['Datapoints'][0]['Average']
                logger.info("Average for %s is %f. Minimum is %f"
                            % (i['InstanceId'], average, minimum))
                if average < minimum:
                    logger.info("About to stop instance %s" % i['InstanceId'])
                    inst = ec2res.Instance(i['InstanceId'])
                    inst.stop()



def lambda_handler(event, context):
    for region in REGIONS:
        stop_idle_instances(region=region,
                            tag_key=TAGKEY,
                            tag_values=TAG_VALUES,
                            idle_period_secs=IDLE_PERIOD_SECS,
                            minimum=MIN_CPU_UTIL)
