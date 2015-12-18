# lambda-aws-billing-notifications

An Amazon Lambda function that uses [detailed billing reports](http://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/detailed-billing-reports.html) to trigger Slack notifications.

## Usage

First, copy the example configuration file and change the options to your liking:

```bash
$ cp config.json.example config.json
```

The following options are available:

- `debug`: Flag to enable or disable debug mode
- `threshold`: USD threshold to alert on
- `duration_in_days`: Range of days from now to select from
- `payer_account_id`: Parent account ID for consolidated billing
- `linked_account_id`: Linked account ID for consolidated billing
- `slack_webhook_url`: Slack webhook URL to trigger when threshold is surpassed
- `channel`: Slack channel to direct messages to
- `bucket`: Bucket housing raw Amazon billing data

Next, use the supplied `Makefile` to assemble a `lambda-aws-billing-notifications.zip` file for Amazon Lambda:

```bash
$ make package
```
