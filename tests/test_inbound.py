import json
import pytest
from unittest.mock import Mock, patch
from src.inbound.processor import InboundProcessor
from src.inbound.monte_carlo.client import MonteCarloClient

@pytest.fixture
def mock_monte_carlo_client():
    with patch('src.inbound.processor.MonteCarloClient') as mock:
        client = Mock(spec=MonteCarloClient)
        mock.return_value = client
        yield client

@pytest.fixture
def mock_storage():
    with patch('src.inbound.processor.DynamoDBStorage') as mock:
        storage = Mock()
        mock.return_value = storage
        yield storage

@pytest.fixture
def mock_sqs():
    with patch('src.inbound.processor.boto3.client') as mock:
        sqs = Mock()
        mock.return_value = sqs
        yield sqs

@pytest.fixture
def mock_eventbridge():
    with patch('src.inbound.processor.boto3.client') as mock:
        eventbridge = Mock()
        mock.return_value = eventbridge
        yield eventbridge

@pytest.fixture
def sample_webhook_payload():
    return {
        "id": "inc_123",
        "type": "incident_created",
        "timestamp": "2024-03-15T10:00:00Z",
        "data": {
            "incident_id": "inc_123",
            "severity": "high",
            "status": "active",
            "description": "Data quality issue detected"
        }
    }

def test_process_webhook_success(mock_monte_carlo_client, mock_storage, mock_eventbridge):
    # Arrange
    processor = InboundProcessor()
    payload = json.dumps(sample_webhook_payload()).encode()
    signature = "valid_signature"

    mock_monte_carlo_client.verify_webhook_signature.return_value = True
    mock_monte_carlo_client.parse_webhook_event.return_value = {
        "event_id": "inc_123",
        "event_type": "incident_created",
        "timestamp": "2024-03-15T10:00:00Z",
        "source": "monte_carlo",
        "payload": sample_webhook_payload()["data"]
    }
    mock_monte_carlo_client.enrich_incident_data.return_value = {
        **sample_webhook_payload()["data"],
        "details": {"additional": "info"},
        "affected_assets": ["asset1", "asset2"]
    }
    mock_storage.store_metadata.return_value = "inc_123"

    # Act
    result = processor.process_webhook(payload, signature)

    # Assert
    assert result["event_id"] == "inc_123"
    assert result["status"] == "processed"
    mock_monte_carlo_client.verify_webhook_signature.assert_called_once_with(payload, signature)
    mock_monte_carlo_client.parse_webhook_event.assert_called_once()
    mock_monte_carlo_client.enrich_incident_data.assert_called_once()
    mock_storage.store_metadata.assert_called_once()
    mock_eventbridge.put_events.assert_called_once()

def test_process_webhook_invalid_signature(mock_monte_carlo_client):
    # Arrange
    processor = InboundProcessor()
    payload = json.dumps(sample_webhook_payload()).encode()
    signature = "invalid_signature"

    mock_monte_carlo_client.verify_webhook_signature.return_value = False

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid webhook signature"):
        processor.process_webhook(payload, signature)

def test_process_sqs_message_success(mock_monte_carlo_client, mock_storage, mock_sqs, mock_eventbridge):
    # Arrange
    processor = InboundProcessor()
    message = {
        "Body": json.dumps(sample_webhook_payload()),
        "MessageAttributes": {
            "Signature": {
                "StringValue": "valid_signature"
            }
        },
        "ReceiptHandle": "receipt_handle"
    }

    mock_monte_carlo_client.verify_webhook_signature.return_value = True
    mock_monte_carlo_client.parse_webhook_event.return_value = {
        "event_id": "inc_123",
        "event_type": "incident_created",
        "timestamp": "2024-03-15T10:00:00Z",
        "source": "monte_carlo",
        "payload": sample_webhook_payload()["data"]
    }
    mock_monte_carlo_client.enrich_incident_data.return_value = {
        **sample_webhook_payload()["data"],
        "details": {"additional": "info"},
        "affected_assets": ["asset1", "asset2"]
    }
    mock_storage.store_metadata.return_value = "inc_123"

    # Act
    result = processor.process_sqs_message(message)

    # Assert
    assert result["event_id"] == "inc_123"
    assert result["status"] == "processed"
    mock_sqs.delete_message.assert_called_once_with(
        QueueUrl=processor.sqs.QueueUrl,
        ReceiptHandle="receipt_handle"
    )

def test_process_sqs_message_error(mock_monte_carlo_client, mock_sqs):
    # Arrange
    processor = InboundProcessor()
    message = {
        "Body": "invalid_json",
        "MessageAttributes": {
            "Signature": {
                "StringValue": "valid_signature"
            }
        },
        "ReceiptHandle": "receipt_handle"
    }

    # Act & Assert
    with pytest.raises(Exception):
        processor.process_sqs_message(message)
    mock_sqs.delete_message.assert_not_called()

def test_start_processing(mock_monte_carlo_client, mock_storage, mock_sqs, mock_eventbridge):
    # Arrange
    processor = InboundProcessor()
    messages = [
        {
            "Body": json.dumps(sample_webhook_payload()),
            "MessageAttributes": {
                "Signature": {
                    "StringValue": "valid_signature"
                }
            },
            "ReceiptHandle": "receipt_handle"
        }
    ]

    mock_sqs.receive_message.return_value = {"Messages": messages}
    mock_monte_carlo_client.verify_webhook_signature.return_value = True
    mock_monte_carlo_client.parse_webhook_event.return_value = {
        "event_id": "inc_123",
        "event_type": "incident_created",
        "timestamp": "2024-03-15T10:00:00Z",
        "source": "monte_carlo",
        "payload": sample_webhook_payload()["data"]
    }
    mock_monte_carlo_client.enrich_incident_data.return_value = {
        **sample_webhook_payload()["data"],
        "details": {"additional": "info"},
        "affected_assets": ["asset1", "asset2"]
    }
    mock_storage.store_metadata.return_value = "inc_123"

    # Act
    processor.start_processing()

    # Assert
    mock_sqs.receive_message.assert_called()
    mock_sqs.delete_message.assert_called_once() 