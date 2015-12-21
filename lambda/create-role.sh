#!/bin/bash
set -x

ROLE_NAME=idle-instance-lambda-role1
POLICY_NAME=idle-instance-stop-policy1

role_arn=$(aws iam create-role --role-name=$ROLE_NAME \
                               --assume-role-policy-document=file://lambda-role.json \
                               --output text \
                               --query 'Role.Arn')

policy_arn=$(aws iam create-policy --policy-name=$POLICY_NAME \
                                   --policy-document=file://idle-instance-stop-policy.json \
                                   --output text \
                                   --query 'Policy.Arn')

aws iam attach-role-policy --role-name=$ROLE_NAME --policy-arn=$policy_arn

