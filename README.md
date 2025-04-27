# Atlan Lily - Real-time Metadata Ingestion and Consumption Platform

## Overview
Atlan Lily is a real-time metadata ingestion and consumption platform designed to handle near-real-time metadata flows for the Atlan platform. This project implements a scalable architecture to support both inbound and outbound metadata flows with a focus on reliability, scalability, and security.

## Problem Statements Addressed
1. **Inbound Use Case**: Monte Carlo Data Observability Integration
   - Real-time ingestion of data quality issues from Monte Carlo
   - Metadata enrichment and storage in Atlan
   - Near-real-time updates to affected assets

2. **Outbound Use Case**: Data Access Security and Compliance
   - Real-time propagation of PII/GDPR annotations
   - Integration with downstream data tools
   - Automated access control enforcement

## Project Structure
```
atlan-lily/
├── docs/
│   ├── architecture.md
│   ├── swagger.yaml
│   └── deployment.md
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── common/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── utils.py
│   ├── inbound/
│   │   ├── __init__.py
│   │   ├── monte_carlo/
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   └── transformer.py
│   │   └── processor.py
│   ├── outbound/
│   │   ├── __init__.py
│   │   ├── security/
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   └── transformer.py
│   │   └── processor.py
│   └── storage/
│       ├── __init__.py
│       └── dynamodb.py
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_inbound.py
│   └── test_outbound.py
├── requirements.txt
├── setup.py
└── README.md
```

## Features

### 1. Real-time Metadata Ingestion
- Webhook-based ingestion from Monte Carlo
- Event validation and enrichment
- Metadata storage in DynamoDB
- Event publishing to EventBridge

### 2. Security Rule Management
- PII/GDPR rule creation and management
- Rule validation and transformation
- Downstream system integration (Snowflake, Databricks)
- Real-time rule propagation

### 3. API Layer
- RESTful API with FastAPI
- Swagger/OpenAPI documentation
- JWT authentication
- Webhook security
- Rate limiting

### 4. Monitoring and Observability
- CloudWatch integration
- Structured logging
- Metrics collection
- Alerting setup

## Setup Instructions

### Prerequisites
- Python 3.8+
- AWS Account with appropriate permissions
- Docker (for local development)

### Installation
1. Clone the repository:
```bash
git clone https://github.com/your-org/atlan-lily.git
cd atlan-lily
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up AWS credentials:
```bash
aws configure
```

### Configuration
1. Copy the example configuration file:
```bash
cp src/common/config.example.py src/common/config.py
```

2. Update the configuration with your AWS credentials and other settings.

### Running the Application
1. Start the API server:
```bash
python src/api/main.py
```

2. Start the inbound processor:
```bash
python src/inbound/processor.py
```

3. Start the outbound processor:
```bash
python src/outbound/processor.py
```

## API Documentation

The API documentation is available in Swagger format. After starting the API server, visit:
```
http://localhost:8000/docs
```

Key API endpoints:
- `POST /webhooks/monte-carlo`: Handle Monte Carlo webhooks
- `GET /events/{event_id}`: Get event details
- `POST /security/rules`: Create security rules
- `PUT /security/rules/{rule_id}`: Update security rules
- `DELETE /security/rules/{rule_id}`: Delete security rules
- `GET /events`: Query events
- `GET /security/rules`: Query security rules

## Architecture
The detailed architecture documentation can be found in [docs/architecture.md](docs/architecture.md). It includes:
- System overview
- Component diagrams
- Data flow diagrams
- Security considerations
- Scaling strategies

## Deployment
Deployment instructions and considerations can be found in [docs/deployment.md](docs/deployment.md). It covers:
- AWS resource setup
- Environment configuration
- Application deployment
- Monitoring setup
- Security considerations

## Testing
Run the test suite:
```bash
pytest tests/
```

The test suite includes:
- API endpoint tests
- Processor tests
- Integration tests
- Mock implementations

## Monitoring

### CloudWatch Metrics
- Event processing latency
- Error rates
- Queue depths
- API response times

### Alerts
- High error rates
- Long execution times
- Queue depth thresholds
- API availability

## Security

### Authentication
- JWT-based authentication
- Webhook signature verification
- IAM role-based access

### Data Protection
- Encryption at rest
- Encryption in transit
- Data masking
- Audit logging