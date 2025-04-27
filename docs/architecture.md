# Atlan Lily Architecture

## System Overview
Atlan Lily is designed as a real-time metadata ingestion and consumption platform that enables near-real-time metadata flows between Atlan and various external systems. The architecture is built with scalability, reliability, and security as core principles.

![System Architecture](diagrams/architecture.png)

## Architecture Components

### 1. Core Components

#### 1.1 Event Bus (Amazon EventBridge)
- Central event routing system
- Handles event filtering and routing
- Supports custom event patterns
- Enables decoupled communication between components

#### 1.2 Metadata Store (Amazon DynamoDB)
- Primary metadata storage
- Supports high-throughput reads and writes
- Enables efficient querying and filtering
- Implements TTL for data lifecycle management

#### 1.3 Message Queue (Amazon SQS)
- Buffers events during high load
- Ensures message delivery
- Supports dead-letter queues for failed processing
- Enables message batching for efficiency

### 2. Inbound Flow (Monte Carlo Integration)

#### 2.1 Components
- Monte Carlo Webhook Receiver (API Gateway + Lambda)
- Event Transformer (Lambda)
- Metadata Enricher (Lambda)
- Storage Writer (Lambda)

#### 2.2 Flow
![Inbound Flow](diagrams/inbound_flow.png)

1. Monte Carlo sends webhook events to API Gateway
2. Webhook Receiver validates and forwards events to EventBridge
3. Event Transformer normalizes event format
4. Metadata Enricher adds Atlan-specific context
5. Storage Writer persists to DynamoDB

### 3. Outbound Flow (Security & Compliance)

#### 3.1 Components
- Change Detection (DynamoDB Streams)
- Event Router (Lambda)
- Security Transformer (Lambda)
- Downstream Integrator (Lambda)

#### 3.2 Flow
![Outbound Flow](diagrams/outbound_flow.png)

1. DynamoDB Streams captures metadata changes
2. Change Detection identifies relevant changes
3. Event Router determines target systems
4. Security Transformer formats security rules
5. Downstream Integrator pushes to target systems

## Data Models

### 1. Data Model Diagram
![Data Model](diagrams/data_model.png)

### 2. Metadata Event Schema
```json
{
  "event_id": "string",
  "event_type": "string",
  "timestamp": "string",
  "source": "string",
  "tenant_id": "string",
  "payload": {
    "asset_id": "string",
    "asset_type": "string",
    "metadata": {
      "key": "value"
    }
  }
}
```

### 3. Security Rule Schema
```json
{
  "rule_id": "string",
  "asset_id": "string",
  "rule_type": "string",
  "conditions": [
    {
      "field": "string",
      "operator": "string",
      "value": "string"
    }
  ],
  "actions": [
    {
      "type": "string",
      "parameters": {}
    }
  ]
}
```

## Security & Compliance

### 1. Authentication & Authorization
- AWS IAM for service-to-service authentication
- JWT-based authentication for API access
- Role-based access control (RBAC)
- Tenant isolation through IAM policies

### 2. Data Protection
- Encryption at rest (AWS KMS)
- Encryption in transit (TLS 1.2+)
- Data masking for sensitive fields
- Audit logging for all operations

## Scalability & Performance

### 1. Scaling Strategies
- Auto-scaling for Lambda functions
- DynamoDB auto-scaling
- SQS message batching
- EventBridge rule throttling

### 2. Performance Targets
- Event processing latency: < 100ms
- End-to-end latency: < 1s
- Throughput: 1000+ events/second
- 99.9% availability

## Monitoring & Observability

### 1. Metrics
- Event processing latency
- Error rates
- Queue depths
- API response times

### 2. Logging
- Structured logging with correlation IDs
- Log aggregation in CloudWatch
- Error tracking in X-Ray

### 3. Alerts
- Error rate thresholds
- Latency thresholds
- Queue depth thresholds
- API availability

## Cost Considerations

### 1. AWS Services
- Lambda: Pay per execution
- DynamoDB: Pay per request and storage
- EventBridge: Pay per event
- SQS: Pay per message

### 2. Optimization Strategies
- Lambda function optimization
- DynamoDB capacity planning
- Message batching
- Caching strategies

## Deployment

### 1. Infrastructure as Code
- AWS CDK for infrastructure
- Environment-specific configurations
- Automated deployment pipelines

### 2. Multi-tenant Support
- Tenant isolation through IAM
- Resource tagging for cost allocation
- Tenant-specific configurations

## Future Considerations

### 1. Extensibility
- Plugin architecture for new integrations
- Custom transformer support
- API versioning strategy

### 2. Additional Features
- Real-time analytics
- Advanced filtering capabilities
- Custom event routing rules
- Enhanced monitoring dashboards 