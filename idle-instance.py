import argparse
import boto3
import datetime
from dateutil.tz import tzutc
import logging

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


DEFAULT_REGION = 'us-west-2'
DEFAULT_TAG_KEY = 'instance-purpose'
DEFAULT_TAG_VALUES = 'test'
DEFAULT_IDLE_SECS = 86400
DEFAULT_MIN_CPU = 0.03


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

'''
Invoke as
python idle-instance.py  --region=us-west-2 --tag-values='test,ephemeral' \
        --minimum-utilization=0.03 --tag-key=instance-purpose \
        --idle-period-secs=3600
'''
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", required=True,
                        dest='region', default=DEFAULT_REGION)
    parser.add_argument("--tag-key", required=False,
                        dest='tag_key', default=DEFAULT_TAG_KEY)
    parser.add_argument("--tag-values", required=False,
                        dest='tag_values', default=DEFAULT_TAG_VALUES)
    parser.add_argument("--idle-period-secs", required=False,
                        dest='idle_period_secs', type=int,
                        default=DEFAULT_IDLE_SECS)
    parser.add_argument("--minimum-utilization", required=False,
                        dest='minimum', type=float, default=DEFAULT_MIN_CPU)

    result = parser.parse_args()
    stop_idle_instances(region=result.region,
                        tag_key=result.tag_key,
                        tag_values=result.tag_values,
                        idle_period_secs=result.idle_period_secs,
                        minimum=result.minimum)
