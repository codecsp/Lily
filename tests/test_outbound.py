import json
import pytest
from unittest.mock import Mock, patch
from src.outbound.processor import OutboundProcessor
from src.outbound.security.transformer import SecurityTransformer

@pytest.fixture
def mock_security_transformer():
    with patch('src.outbound.processor.SecurityTransformer') as mock:
        transformer = Mock(spec=SecurityTransformer)
        mock.return_value = transformer
        yield transformer

@pytest.fixture
def mock_storage():
    with patch('src.outbound.processor.DynamoDBStorage') as mock:
        storage = Mock()
        mock.return_value = storage
        yield storage

@pytest.fixture
def mock_sqs():
    with patch('src.outbound.processor.boto3.client') as mock:
        sqs = Mock()
        mock.return_value = sqs
        yield sqs

@pytest.fixture
def mock_eventbridge():
    with patch('src.outbound.processor.boto3.client') as mock:
        eventbridge = Mock()
        mock.return_value = eventbridge
        yield eventbridge

@pytest.fixture
def sample_security_rule():
    return {
        "rule_id": "rule_123",
        "rule_type": "PII",
        "asset_id": "asset_123",
        "asset_type": "table",
        "conditions": [
            {
                "field": "column_name",
                "operator": "contains",
                "value": "email"
            }
        ],
        "actions": [
            {
                "type": "mask",
                "parameters": {
                    "mask_type": "email"
                }
            }
        ]
    }

def test_process_security_event_success(mock_security_transformer, mock_storage, mock_eventbridge):
    # Arrange
    processor = OutboundProcessor()
    event = sample_security_rule()

    mock_security_transformer.transform_security_rule.return_value = event
    mock_security_transformer.validate_rule.return_value = True
    mock_security_transformer.format_for_downstream.return_value = {
        "snowflake": {
            "type": "snowflake_policy",
            "name": "atlan_rule_123",
            "conditions": [
                {
                    "column": "column_name",
                    "operator": "contains",
                    "value": "email"
                }
            ],
            "actions": [
                {
                    "type": "mask",
                    "parameters": {
                        "mask_type": "email"
                    }
                }
            ]
        }
    }
    mock_storage.store_metadata.return_value = "rule_123"

    # Act
    result = processor.process_security_event(event)

    # Assert
    assert result["event_id"] == "rule_123"
    assert result["status"] == "processed"
    assert "downstream_rules" in result
    mock_security_transformer.transform_security_rule.assert_called_once_with(event)
    mock_security_transformer.validate_rule.assert_called_once_with(event)
    mock_storage.store_metadata.assert_called_once()
    mock_eventbridge.put_events.assert_called_once()

def test_process_security_event_invalid_rule(mock_security_transformer):
    # Arrange
    processor = OutboundProcessor()
    event = sample_security_rule()

    mock_security_transformer.transform_security_rule.return_value = event
    mock_security_transformer.validate_rule.return_value = False

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid security rule"):
        processor.process_security_event(event)

def test_process_sqs_message_success(mock_security_transformer, mock_storage, mock_sqs, mock_eventbridge):
    # Arrange
    processor = OutboundProcessor()
    message = {
        "Body": json.dumps(sample_security_rule()),
        "ReceiptHandle": "receipt_handle"
    }

    mock_security_transformer.transform_security_rule.return_value = sample_security_rule()
    mock_security_transformer.validate_rule.return_value = True
    mock_security_transformer.format_for_downstream.return_value = {
        "snowflake": {
            "type": "snowflake_policy",
            "name": "atlan_rule_123",
            "conditions": [
                {
                    "column": "column_name",
                    "operator": "contains",
                    "value": "email"
                }
            ],
            "actions": [
                {
                    "type": "mask",
                    "parameters": {
                        "mask_type": "email"
                    }
                }
            ]
        }
    }
    mock_storage.store_metadata.return_value = "rule_123"

    # Act
    result = processor.process_sqs_message(message)

    # Assert
    assert result["event_id"] == "rule_123"
    assert result["status"] == "processed"
    mock_sqs.delete_message.assert_called_once_with(
        QueueUrl=processor.sqs.QueueUrl,
        ReceiptHandle="receipt_handle"
    )

def test_process_sqs_message_error(mock_security_transformer, mock_sqs):
    # Arrange
    processor = OutboundProcessor()
    message = {
        "Body": "invalid_json",
        "ReceiptHandle": "receipt_handle"
    }

    # Act & Assert
    with pytest.raises(Exception):
        processor.process_sqs_message(message)
    mock_sqs.delete_message.assert_not_called()

def test_format_for_downstream_systems(mock_security_transformer):
    # Arrange
    processor = OutboundProcessor()
    rule = sample_security_rule()

    mock_security_transformer.format_for_downstream.side_effect = [
        {
            "type": "snowflake_policy",
            "name": "atlan_rule_123",
            "conditions": [
                {
                    "column": "column_name",
                    "operator": "contains",
                    "value": "email"
                }
            ],
            "actions": [
                {
                    "type": "mask",
                    "parameters": {
                        "mask_type": "email"
                    }
                }
            ]
        },
        {
            "type": "databricks_policy",
            "name": "atlan_rule_123",
            "conditions": [
                {
                    "column": "column_name",
                    "operator": "contains",
                    "value": "email"
                }
            ],
            "actions": [
                {
                    "type": "mask",
                    "parameters": {
                        "mask_type": "email"
                    }
                }
            ]
        }
    ]

    # Act
    result = processor._format_for_downstream_systems(rule)

    # Assert
    assert "snowflake" in result
    assert "databricks" in result
    assert result["snowflake"]["type"] == "snowflake_policy"
    assert result["databricks"]["type"] == "databricks_policy"
    mock_security_transformer.format_for_downstream.assert_any_call(rule, "snowflake")
    mock_security_transformer.format_for_downstream.assert_any_call(rule, "databricks")

def test_start_processing(mock_security_transformer, mock_storage, mock_sqs, mock_eventbridge):
    # Arrange
    processor = OutboundProcessor()
    messages = [
        {
            "Body": json.dumps(sample_security_rule()),
            "ReceiptHandle": "receipt_handle"
        }
    ]

    mock_sqs.receive_message.return_value = {"Messages": messages}
    mock_security_transformer.transform_security_rule.return_value = sample_security_rule()
    mock_security_transformer.validate_rule.return_value = True
    mock_security_transformer.format_for_downstream.return_value = {
        "snowflake": {
            "type": "snowflake_policy",
            "name": "atlan_rule_123"
        }
    }
    mock_storage.store_metadata.return_value = "rule_123"

    # Act
    processor.start_processing()

    # Assert
    mock_sqs.receive_message.assert_called()
    mock_sqs.delete_message.assert_called_once() 