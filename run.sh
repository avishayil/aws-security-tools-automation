#!/bin/bash

bucket=$(cat config.yml | yaml2json | jq -r '.bucket')
regions_string=$(cat config.yml | yaml2json | jq -r '.regions | join(",")')
master_account=$(cat config.yml | yaml2json | jq -r '.accounts.master')

if [ -z "$bucket" || -z "$regions_string" || -z "$master_account" ]
then
    echo "One of the config variables is not defined. Check the config.yml file"
    exit 1
else
    python setup_config_bucket.py --enabled_regions $regions_string --bucket_name $bucket
    cd amazon-guardduty-multiaccount-scripts
    python enableguardduty.py --master_account $master_account --enabled_regions $regions_string --assume_role ManageGuardDuty ../enable.csv
    cd .. && cd aws-securityhub-multiaccount-scripts 
    python enablesecurityhub.py --master_account $master_account --enabled_regions $regions_string --assume_role ManageSecurityHub ../enable.csv
    cd .. && cd amazon-detective-multiaccount-scripts
    python enabledetective.py --master_account $master_account --enabled_regions $regions_string --assume_role ManageDetective --input_file ../enable.csv
    cd ..
fi