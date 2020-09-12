#!/usr/bin/env python

import boto3
import argparse
import re

from collections import OrderedDict
from botocore.exceptions import ClientError

def assume_role(aws_account_number, role_name):
    """
    Assumes the provided role in each account and returns a GuardDuty client
    :param aws_account_number: AWS Account Number
    :param role_name: Role to assume in target account
    :param aws_region: AWS Region for the Client call, not required for IAM calls
    :return: GuardDuty client in the specified AWS Account and Region
    """

    # Beginning the assume role process for account
    sts_client = boto3.client('sts')

    # Get the current partition
    partition = sts_client.get_caller_identity()['Arn'].split(":")[1]

    response = sts_client.assume_role(
        RoleArn='arn:{}:iam::{}:role/{}'.format(
            partition,
            aws_account_number,
            role_name
        ),
        RoleSessionName='EnableConfig'
    )

    # Storing STS credentials
    session = boto3.Session(
        aws_access_key_id=response['Credentials']['AccessKeyId'],
        aws_secret_access_key=response['Credentials']['SecretAccessKey'],
        aws_session_token=response['Credentials']['SessionToken']
    )

    print("Assumed session for {}.".format(
        aws_account_number
    ))

    return session


if __name__ == '__main__':

    # Setup command line arguments
    parser = argparse.ArgumentParser(description='Link AWS Config configuration recorders to central Logging Account')
    parser.add_argument('--bucket_name', type=str, required=True, help="BucketName for central AWS Config logging")
    parser.add_argument('--master_account', type=str, required=True, help="AccountId for Central AWS Account")
    parser.add_argument('input_file', type=argparse.FileType('r'), help='Path to CSV file containing the list of account IDs and Email addresses')
    parser.add_argument('--assume_role', type=str, required=True, help="Role Name to assume in each account")
    parser.add_argument('--enabled_regions', type=str,
                        help="comma separated list of regions to enable AWS Config. If not specified, only us-east-1 region will be enabled")
    args = parser.parse_args()

    # Validate master accountId
    if not re.match(r'[0-9]{12}', args.master_account):
        raise ValueError("Master AccountId is not valid")

    # Generate dict with account & email information
    aws_account_dict = OrderedDict()

    # Add master account to dict
    aws_account_dict[args.master_account] = 'test@account.com'

    for acct in args.input_file.readlines():
        split_line = acct.rstrip().split(",")
        if len(split_line) < 2:
            print("Unable to process line: {}".format(acct))
            continue

        if not re.match(r'[0-9]{12}', str(split_line[0])):
            print("Invalid account number {}, skipping".format(split_line[0]))
            continue

        aws_account_dict[split_line[0]] = split_line[1]

    if args.enabled_regions:
        aws_regions = [str(item) for item in args.enabled_regions.split(',')]
        print("Enabling members in these regions: {}".format(aws_regions))
    else:
        aws_regions = ['us-east-1']

    for account in aws_account_dict.keys():
        try:
            session = assume_role(account, args.assume_role)

            for aws_region in aws_regions:
                print("Working on region {} on account {}".format(aws_region, account))
                config = session.client('config', region_name=aws_region)

                # Get & clean configuration recorders
                configuration_recorders = config.describe_configuration_recorders()['ConfigurationRecorders']
                if len(configuration_recorders):
                    for configuration_recorder in configuration_recorders:
                        print("Deleting configuration recorder: {}...".format(configuration_recorder['name']))
                        config.delete_configuration_recorder(ConfigurationRecorderName=configuration_recorder['name'])
                print("Creating new default configuration recorder...")
                config.put_configuration_recorder(ConfigurationRecorder={'name': 'default',
                                                                        'roleARN': 'arn:aws:iam::%s:role/AWSConfigRole' % account,
                                                                        'recordingGroup': {'allSupported': True,
                                                                                            'includeGlobalResourceTypes': True}})
                # Get & clean delivery channels
                delivery_channels = config.describe_delivery_channels()['DeliveryChannels']
                if len(delivery_channels):
                    for delivery_channel in delivery_channels:
                        print("Deleting delivery channel: {}...".format(delivery_channel['name']))
                        config.delete_delivery_channel(DeliveryChannelName=delivery_channel['name'])
                print("Creating new default delivery channel...")
                config.put_delivery_channel(DeliveryChannel={
                    'name': 'default',
                    's3BucketName': args.bucket_name,
                    'configSnapshotDeliveryProperties': {'deliveryFrequency': 'TwentyFour_Hours'}
                })
                print("Starting configuration recorder...")
                config.start_configuration_recorder(ConfigurationRecorderName=config.describe_configuration_recorder_status()[
                    'ConfigurationRecordersStatus'][0]['name'])

        except ClientError as err:
            if err.response['ResponseMetadata']['HTTPStatusCode'] == 403:
                print("Failed due to an authentication error: ", err)
            else:
                print("Error: ", err)
