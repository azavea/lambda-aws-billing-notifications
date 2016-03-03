# lambda-aws-billing-notifications

A collection of Amazon Lambda functions that use [detailed billing reports](http://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/detailed-billing-reports.html) to trigger notifications.

## Usage

First, set the following environment variables:

- `AWS_BILLING_DEBUG`: Flag to enable or disable debug mode
- `AWS_BILLING_THRESHOLD`: USD threshold to alert on
- `AWS_BILLING_DURATION_IN_DAYS`: Range of days from now to select from
- `AWS_BILLING_PAYER_ACCOUNT_ID`: Parent account ID for consolidated billing
- `AWS_BILLING_LINKED_ACCOUNT_ID`: Linked account ID for consolidated billing
- `AWS_BILLING_LINKED_ACCOUNT_ALIAS`: Linked account alias for consolidated billing
- `AWS_BILLING_SLACK_WEBHOOK_URL`: Slack webhook URL to trigger when threshold is surpassed
- `AWS_BILLING_SLACK_CHANNEL`: Slack channel to direct messages to
- `AWS_BILLING_BUCKET`: Bucket housing raw Amazon billing data

Then, execute the Slack function locally:

```bash
python functions/Slack/main.py
```

## Deployment

First, install the [Apex](http://apex.run/) Amazon Lambda function manager. Then, use it to list the available functions:

```bash
$ apex list

  Slack
    description: Triggers billing report Slack notifications.
    runtime: python2.7
    memory: 256mb
    timeout: 60s
    role: arn:aws:iam::715496170458:role/lambda_basic_execution
    handler: main.handle
```

Lastly, deploy the `Slack` function:

```bash
$ apex deploy Slack \
    -e AWS_BILLING_THRESHOLD=100 \
    -e AWS_BILLING_SLACK_WEBHOOK_URL="https://hooks.slack.com..." \
    -e AWS_BILLING_LINKED_ACCOUNT_ALIAS="Personal" \
    -e AWS_BILLING_LINKED_ACCOUNT_ID="..." \
    -e AWS_BILLING_PAYER_ACCOUNT_ID="..." \
    -e AWS_BILLING_SLACK_CHANNEL="#general" \
    -e AWS_BILLING_BUCKET="billing-bucket" \
    -e AWS_BILLING_DURATION_IN_DAYS=1
```
