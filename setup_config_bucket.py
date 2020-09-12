#!/usr/bin/env python

import boto3
import argparse

if __name__ == '__main__':

    # Setup command line arguments
    parser = argparse.ArgumentParser(description='Link AWS Config configuration recorders to central Logging Account')
    parser.add_argument('--bucket_name', type=str, required=True, help="BucketName for central AWS Config logging")
    parser.add_argument('--enabled_regions', type=str,
                        help="comma separated list of regions to enable AWS Config. If not specified, only us-east-1 region will be enabled")
    args = parser.parse_args()

    # Get current account details
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity().get('Account')

    if args.enabled_regions:
        aws_regions = [str(item) for item in args.enabled_regions.split(',')]
        print("Enabling members in these regions: {}".format(aws_regions))
    else:
        aws_regions = ['us-east-1']

    for region in aws_regions:
        print("Working on region {} on account {}".format(region, account_id))
        config = boto3.client('config', region_name=region)

        # Get & clean configuration recorders
        configuration_recorders = config.describe_configuration_recorders()['ConfigurationRecorders']
        if len(configuration_recorders):
            for configuration_recorder in configuration_recorders:
                print("Deleting configuration recorder: {}...".format(configuration_recorder['name']))
                config.delete_configuration_recorder(ConfigurationRecorderName=configuration_recorder['name'])
        print("Creating new default configuration recorder...")
        config.put_configuration_recorder(ConfigurationRecorder={'name': 'default',
                                                                 'roleARN': 'arn:aws:iam::%s:role/AWSConfigRole' % account_id,
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
