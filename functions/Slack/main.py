from __future__ import print_function

from math import fsum
from csv import DictReader
from zipfile import ZipFile
from datetime import datetime, timedelta

import os
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


def handle(event, context):
    """Amazon Lambda event handler.

    Arguments:
    event   -- Source event
    context -- Amazon Lambda context object
    """
    if os.environ.get('AWS_BILLING_DEBUG', False):
        LOG.setLevel(logging.DEBUG)

    estimated_charges = get_estimated_charges()

    LOG.debug('Estimated charges are [%s]', estimated_charges)

    if estimated_charges > float(os.environ['AWS_BILLING_THRESHOLD']):
        requests.post(os.environ['AWS_BILLING_SLACK_WEBHOOK_URL'],
                      json={'text': 'Blended costs for {} have exceeded the threshold '
                                    'of ${} with ${:.2f}.'.format(
                                        os.environ.get('AWS_BILLING_LINKED_ACCOUNT_ALIAS',
                                                       os.environ['AWS_BILLING_LINKED_ACCOUNT_ID']),
                                        os.environ['AWS_BILLING_THRESHOLD'],
                                        estimated_charges),
                            'channel': os.environ['AWS_BILLING_SLACK_CHANNEL']})


def get_estimated_charges():
    """Gather estimated AWS charges from raw Amazon billing data."""
    bucket = os.environ['AWS_BILLING_BUCKET']
    duration_in_days = os.environ.get('AWS_BILLING_DURATION_IN_DAYS', 1)
    payer_account_id = os.environ['AWS_BILLING_PAYER_ACCOUNT_ID']
    linked_account_id = os.environ['AWS_BILLING_LINKED_ACCOUNT_ID']

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
                    yesterday = today - timedelta(days=int(duration_in_days))

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
    handle(None, None)
