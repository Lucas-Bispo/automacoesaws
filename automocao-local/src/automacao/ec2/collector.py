import boto3
import pandas as pd
import logging
from ..utils.config import get_config

def collect_data():
    aws_region = get_config('AWS_REGION', 'us-east-1')
    ec2_client = boto3.client('ec2', region_name=aws_region)
    paginator = ec2_client.get_paginator('describe_instances')
    
    instances_data = []
    logging.info("Coletando dados de Instâncias EC2...")

    for page in paginator.paginate(Filters=[{'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}]):
        for reservation in page['Reservations']:
            for instance in reservation['Instances']:
                instance_name = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), 'N/A')
                instances_data.append({
                    'Name': instance_name, 'InstanceId': instance.get('InstanceId'),
                    'InstanceType': instance.get('InstanceType'), 'State': instance.get('State', {}).get('Name'),
                    'PrivateIpAddress': instance.get('PrivateIpAddress'), 'PublicIpAddress': instance.get('PublicIpAddress', 'N/A'),
                    'VpcId': instance.get('VpcId'), 'LaunchTime': instance.get('LaunchTime')
                })
    return {'EC2_Instances': pd.DataFrame(instances_data)}