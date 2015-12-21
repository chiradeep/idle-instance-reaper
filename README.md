# idle-instance-reaper
Save money on your cloud bill by turning off idle instances

## Theory of operation
1. Periodically, query AWS for a list of instances matching a [tag](http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_Tags.html). This should help avoid turning off production instances
2. For each instance, obtain CPU utilization over a period of time.
3. If utilization is below threshold, turn it off.

## Pre-requisites
1. Checkout this code

    ```
    git clone https://github.com/chiradeep/idle-instance-reaper.git
    ```
2. AWS account
3. AWS CLI, configured with credentials

## Command line
There is a command line option:

```
python idle-instance.py  --region=us-west-2 --tag-values='test,ephemeral' \
        --minimum-utilization=0.03 --tag-key=instance-purpose \
        --idle-period-secs=3600
```

This will fetch instances tagged with either 'instance-purpose:test' or 'instance-purpose:ephemeral' and check if their utilization over the past 3600 seconds is less than 0.03. If so, these instances will be stopped. Note that you will continue to incur usage charges for the EBS volumes if their root volume is EBS-based.

Try running this as a [cron job](https://en.wikipedia.org/wiki/Cron) on a server or laptop that is on all the time.

## Lambda
You can have [AWS Lambda](https://aws.amazon.com/lambda/) do the periodic checking for you as well:

```
cd lambda
./create-role-func.sh
```

This will create a lambda function called `idle-instance-lambda`. To schedule it, you have to login to your AWS Lambda console and create a [ScheduledEvent ](http://docs.aws.amazon.com/lambda/latest/dg/with-scheduled-events.html) trigger for it (currently there is no way of creating this trigger using the API /CLI)


### More
Enhancements that are easily made by tweaking the code:

1. get a more precise match of the machines you want to turn off. For example, perhaps you want machines that are not tagged at all, or machines owned by a particular user. Or machines of a particular class. Etc.
2. always turn off before the weekend starts, regardless of CPU utilization
3. send an email / sms instead of turning off.

