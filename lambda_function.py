from __future__ import print_function

from math import fsum
from csv import DictReader
from zipfile import ZipFile
from datetime import datetime, timedelta

import os
import json
import logging
import boto3
import requests
import tempfile

BILLING_RECORD_TYPE_HEADER = 'LineItem'
BILLING_USAGE_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

LOG = logging.getLogger(__file__)
LOG.addHandler(logging.StreamHandler())
LOG.setLevel(logging.DEBUG)

TEMP_DIR = tempfile.gettempdir()


def lambda_handler(event, context):
    """Amazon Lambda event handler.

    Arguments:
    event   -- Source event
    context -- Amazon Lambda context object
    """
    with open('config.json') as config_json:
        config = json.load(config_json)

    if config['debug']:
        LOG.setLevel(logging.DEBUG)
        LOG.debug(json.dumps(event))

    estimated_charges = get_estimated_charges(**config)

    LOG.debug('Estimated charges are [%s]', estimated_charges)

    if estimated_charges > config['threshold']:
        requests.post(config['slack_webhook_url'],
                      json={'text': 'Blended costs for account ID {} have exceeded the threshold '
                                    'of ${} with ${:.2f}.'.format(config['linked_account_id'],
                                                                  config['threshold'],
                                                                  estimated_charges),
                            'channel': config['channel']})


def get_estimated_charges(bucket=None, duration_in_days=1,
                          payer_account_id=None, linked_account_id=None,
                          **kwargs):
    """Gather estimated AWS charges from raw Amazon billing data.

    Keyword arguments:
    bucket -- Bucket housing raw Amazon billing data
    duration_in_days -- Number of days collect billing data points
    payer_account_id -- Parent account ID for consolidated billing
    linked_account_id -- Linked account ID for consolidated billing
    """
    LOG.debug('Filtering by [%s] and [%s] in [%s] for [%s] day/s',
              payer_account_id, linked_account_id, bucket, duration_in_days)

    client = boto3.client('s3')
    bucket_listing = client.list_objects(Bucket=bucket, Prefix=payer_account_id)
    now = datetime.utcnow()

    for s3_object in bucket_listing['Contents']:
        object_key = s3_object['Key']

        if object_key.endswith('items-{}-{:02d}.csv.zip'.format(now.year, now.month)):
            archive_file = download_billing_archive(client, bucket, object_key)
            csv_file = extract_billing_archive(archive_file)

            with open(csv_file) as f:
                def linked_account_filter(row):
                    today = datetime(now.year, now.month, now.day)
                    yesterday = today - timedelta(days=duration_in_days)

                    if row['LinkedAccountId'] == linked_account_id and \
                            row['RecordType'] == BILLING_RECORD_TYPE_HEADER:
                        usage_start = datetime.strptime(row['UsageStartDate'],
                                                        BILLING_USAGE_DATETIME_FORMAT)
                        usage_end = datetime.strptime(row['UsageEndDate'],
                                                      BILLING_USAGE_DATETIME_FORMAT)

                        return usage_start >= yesterday and usage_end <= today
                    else:
                        return False

                filtered_by_linked_account = filter(linked_account_filter, DictReader(f))

    return fsum(float(row['BlendedCost']) for row in filtered_by_linked_account)


def download_billing_archive(client, bucket, object_key):
    """Download raw Amazon billing data archive.

    Keyword arguments:
    client -- Boto S3 client
    bucket -- Bucket housing raw Amazon billing data
    object_key -- Amazon S3 object key of archive
    """
    destination = os.path.join(TEMP_DIR, object_key)

    if not os.path.exists(destination):
        LOG.debug('Downloading [%s] to [%s]', object_key, destination)

        client.download_file(bucket, object_key, destination)

    return destination


def extract_billing_archive(archive_file):
    """Extract raw Amazon billing data archive.

    Keyword arguments:
    archive_file -- File systme location of Amazon billing data archive
    """
    csv_file = archive_file[:len(archive_file) - 4]

    if not os.path.exists(csv_file):
        LOG.debug('Extracting [%s] into [%s]', archive_file, TEMP_DIR)

        with ZipFile(archive_file) as z:
            z.extractall(path=TEMP_DIR)

    return csv_file

if __name__ == '__main__':
    lambda_handler(None, None)
