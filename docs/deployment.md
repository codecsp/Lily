# Deployment Guide

## Prerequisites

1. AWS Account with appropriate permissions
2. Python 3.8 or higher
3. AWS CLI configured with appropriate credentials
4. Docker (for local development)

## Infrastructure Setup

### 1. AWS Resources

The following AWS resources need to be created:

1. **DynamoDB Table**
   ```bash
   aws dynamodb create-table \
       --table-name atlan-lily-metadata \
       --attribute-definitions AttributeName=event_id,AttributeType=S \
       --key-schema AttributeName=event_id,KeyType=HASH \
       --billing-mode PAY_PER_REQUEST
   ```

2. **EventBridge Bus**
   ```bash
   aws events create-event-bus \
       --name atlan-lily-bus
   ```

3. **SQS Queues**
   ```bash
   # Inbound Queue
   aws sqs create-queue \
       --queue-name atlan-lily-inbound \
       --attributes VisibilityTimeout=300

   # Outbound Queue
   aws sqs create-queue \
       --queue-name atlan-lily-outbound \
       --attributes VisibilityTimeout=300
   ```

### 2. Environment Configuration

Create a `.env` file in the project root with the following variables:

```env
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key

# DynamoDB Configuration
DYNAMODB_TABLE_NAME=atlan-lily-metadata
DYNAMODB_ENDPOINT_URL=http://localhost:8000  # For local development

# EventBridge Configuration
EVENT_BUS_NAME=atlan-lily-bus

# SQS Configuration
INBOUND_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/your-account-id/atlan-lily-inbound
OUTBOUND_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/your-account-id/atlan-lily-outbound

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# Security Configuration
JWT_SECRET_KEY=your_jwt_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Monte Carlo Configuration
MONTE_CARLO_API_KEY=your_monte_carlo_api_key
MONTE_CARLO_WEBHOOK_SECRET=your_monte_carlo_webhook_secret

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Application Deployment

### 1. Local Development

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the inbound processor:
   ```bash
   python src/inbound/processor.py
   ```

4. Start the outbound processor:
   ```bash
   python src/outbound/processor.py
   ```

### 2. AWS Deployment

1. Create a deployment package:
   ```bash
   pip install -r requirements.txt -t ./package
   cp -r src/* ./package/
   cd package
   zip -r ../deployment.zip .
   ```

2. Create Lambda functions:
   ```bash
   # Inbound Processor
   aws lambda create-function \
       --function-name atlan-lily-inbound \
       --runtime python3.8 \
       --handler src.inbound.processor.main \
       --zip-file fileb://deployment.zip \
       --role arn:aws:iam::your-account-id:role/atlan-lily-lambda-role

   # Outbound Processor
   aws lambda create-function \
       --function-name atlan-lily-outbound \
       --runtime python3.8 \
       --handler src.outbound.processor.main \
       --zip-file fileb://deployment.zip \
       --role arn:aws:iam::your-account-id:role/atlan-lily-lambda-role
   ```

3. Set up EventBridge rules:
   ```bash
   # Inbound Events
   aws events put-rule \
       --name atlan-lily-inbound-events \
       --event-pattern '{"source":["atlan.lily"],"detail-type":["monte_carlo_incident"]}' \
       --state ENABLED

   aws events put-targets \
       --rule atlan-lily-inbound-events \
       --targets Id=1,Arn=arn:aws:lambda:us-east-1:your-account-id:function:atlan-lily-inbound

   # Outbound Events
   aws events put-rule \
       --name atlan-lily-outbound-events \
       --event-pattern '{"source":["atlan.lily"],"detail-type":["security_rule"]}' \
       --state ENABLED

   aws events put-targets \
       --rule atlan-lily-outbound-events \
       --targets Id=1,Arn=arn:aws:lambda:us-east-1:your-account-id:function:atlan-lily-outbound
   ```

## Monitoring and Maintenance

### 1. CloudWatch Logs

Monitor the application logs in CloudWatch:
- Inbound Processor: `/aws/lambda/atlan-lily-inbound`
- Outbound Processor: `/aws/lambda/atlan-lily-outbound`

### 2. CloudWatch Metrics

Key metrics to monitor:
- Lambda execution duration
- Error rates
- SQS queue depth
- DynamoDB consumed capacity

### 3. Alarms

Set up CloudWatch alarms for:
- High error rates
- Long execution times
- Queue depth thresholds
- DynamoDB throttling

## Security Considerations

1. **IAM Roles**
   - Use least privilege principle
   - Regularly audit permissions
   - Rotate access keys

2. **Encryption**
   - Enable encryption at rest for DynamoDB
   - Use TLS for all API communications
   - Encrypt sensitive environment variables

3. **Network Security**
   - Use VPC endpoints for AWS services
   - Implement proper security groups
   - Enable VPC flow logs

## Scaling Considerations

1. **Lambda**
   - Configure appropriate memory and timeout
   - Use provisioned concurrency for predictable workloads
   - Monitor cold starts

2. **DynamoDB**
   - Use auto-scaling
   - Monitor consumed capacity
   - Implement proper partition key design

3. **SQS**
   - Configure appropriate visibility timeout
   - Set up dead-letter queues
   - Monitor queue depth

## Troubleshooting

1. **Common Issues**
   - Lambda timeouts
   - DynamoDB throttling
   - SQS message visibility
   - EventBridge rule matching

2. **Debugging Steps**
   - Check CloudWatch logs
   - Verify IAM permissions
   - Test event patterns
   - Monitor resource utilization

## Backup and Recovery

1. **DynamoDB**
   - Enable point-in-time recovery
   - Regular backups
   - Cross-region replication

2. **Configuration**
   - Version control for infrastructure
   - Document recovery procedures
   - Regular testing of recovery process 