import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from unittest.mock import Mock, patch
import json

client = TestClient(app)

@pytest.fixture
def mock_monte_carlo_client():
    with patch('src.api.main.monte_carlo_client') as mock:
        client = Mock()
        mock.verify_webhook_signature.return_value = True
        mock.process_webhook.return_value = {
            "event_id": "inc_123",
            "status": "processed"
        }
        yield client

@pytest.fixture
def mock_security_transformer():
    with patch('src.api.main.security_transformer') as mock:
        transformer = Mock()
        mock.transform_security_rule.return_value = {
            "rule_id": "rule_123",
            "rule_type": "PII",
            "asset_id": "asset_123",
            "asset_type": "table",
            "conditions": [],
            "actions": [],
            "metadata": {
                "created_at": "2024-03-15T10:00:00Z",
                "updated_at": "2024-03-15T10:00:00Z"
            }
        }
        mock.validate_rule.return_value = True
        mock.format_for_downstream.return_value = {
            "snowflake": {
                "type": "snowflake_policy",
                "name": "atlan_rule_123"
            }
        }
        yield transformer

@pytest.fixture
def mock_storage():
    with patch('src.api.main.storage') as mock:
        storage = Mock()
        mock.get_metadata.return_value = {
            "event_id": "rule_123",
            "event_type": "security_rule",
            "timestamp": "2024-03-15T10:00:00Z",
            "source": "atlan",
            "payload": {
                "rule_id": "rule_123",
                "rule_type": "PII",
                "asset_id": "asset_123",
                "asset_type": "table",
                "conditions": [],
                "actions": []
            }
        }
        mock.store_metadata.return_value = "rule_123"
        mock.update_metadata.return_value = True
        mock.delete_metadata.return_value = True
        mock.query_metadata.return_value = [
            {
                "event_id": "rule_123",
                "event_type": "security_rule",
                "timestamp": "2024-03-15T10:00:00Z",
                "source": "atlan",
                "payload": {
                    "rule_id": "rule_123",
                    "rule_type": "PII",
                    "asset_id": "asset_123",
                    "asset_type": "table",
                    "conditions": [],
                    "actions": []
                }
            }
        ]
        yield storage

def test_monte_carlo_webhook_success(mock_monte_carlo_client):
    response = client.post(
        "/webhooks/monte-carlo",
        json={
            "id": "inc_123",
            "type": "incident_created",
            "timestamp": "2024-03-15T10:00:00Z",
            "data": {
                "incident_id": "inc_123",
                "severity": "high",
                "status": "active",
                "description": "Data quality issue detected"
            }
        },
        headers={
            "X-Monte-Carlo-Signature": "valid_signature"
        }
    )
    assert response.status_code == 200
    assert response.json() == {
        "event_id": "inc_123",
        "status": "processed"
    }

def test_monte_carlo_webhook_invalid_signature(mock_monte_carlo_client):
    mock_monte_carlo_client.verify_webhook_signature.return_value = False
    response = client.post(
        "/webhooks/monte-carlo",
        json={
            "id": "inc_123",
            "type": "incident_created",
            "timestamp": "2024-03-15T10:00:00Z",
            "data": {
                "incident_id": "inc_123",
                "severity": "high",
                "status": "active",
                "description": "Data quality issue detected"
            }
        },
        headers={
            "X-Monte-Carlo-Signature": "invalid_signature"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid signature"

def test_get_event_success(mock_storage):
    response = client.get(
        "/events/rule_123",
        headers={
            "Authorization": "Bearer valid_token"
        }
    )
    assert response.status_code == 200
    assert response.json()["event_id"] == "rule_123"

def test_get_event_not_found(mock_storage):
    mock_storage.get_metadata.return_value = None
    response = client.get(
        "/events/nonexistent",
        headers={
            "Authorization": "Bearer valid_token"
        }
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"

def test_create_security_rule_success(mock_security_transformer, mock_storage):
    response = client.post(
        "/security/rules",
        json={
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
        },
        headers={
            "Authorization": "Bearer valid_token"
        }
    )
    assert response.status_code == 201
    assert response.json()["rule_id"] == "rule_123"
    assert response.json()["status"] == "created"
    assert "downstream_rules" in response.json()

def test_create_security_rule_invalid(mock_security_transformer, mock_storage):
    mock_security_transformer.validate_rule.return_value = False
    response = client.post(
        "/security/rules",
        json={
            "rule_type": "INVALID",
            "asset_id": "asset_123",
            "asset_type": "table"
        },
        headers={
            "Authorization": "Bearer valid_token"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid rule format"

def test_update_security_rule_success(mock_security_transformer, mock_storage):
    response = client.put(
        "/security/rules/rule_123",
        json={
            "conditions": [
                {
                    "field": "column_name",
                    "operator": "contains",
                    "value": "email"
                }
            ]
        },
        headers={
            "Authorization": "Bearer valid_token"
        }
    )
    assert response.status_code == 200
    assert response.json()["rule_id"] == "rule_123"
    assert response.json()["status"] == "updated"
    assert "downstream_rules" in response.json()

def test_update_security_rule_not_found(mock_storage):
    mock_storage.get_metadata.return_value = None
    response = client.put(
        "/security/rules/nonexistent",
        json={
            "conditions": []
        },
        headers={
            "Authorization": "Bearer valid_token"
        }
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Rule not found"

def test_delete_security_rule_success(mock_storage):
    response = client.delete(
        "/security/rules/rule_123",
        headers={
            "Authorization": "Bearer valid_token"
        }
    )
    assert response.status_code == 200
    assert response.json()["rule_id"] == "rule_123"
    assert response.json()["status"] == "deleted"

def test_delete_security_rule_not_found(mock_storage):
    mock_storage.delete_metadata.return_value = False
    response = client.delete(
        "/security/rules/nonexistent",
        headers={
            "Authorization": "Bearer valid_token"
        }
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Rule not found"

def test_query_events_success(mock_storage):
    response = client.get(
        "/events",
        params={
            "event_type": "security_rule",
            "source": "atlan",
            "limit": 10
        },
        headers={
            "Authorization": "Bearer valid_token"
        }
    )
    assert response.status_code == 200
    assert "events" in response.json()
    assert len(response.json()["events"]) > 0

def test_query_security_rules_success(mock_storage):
    response = client.get(
        "/security/rules",
        params={
            "rule_type": "PII",
            "asset_id": "asset_123",
            "limit": 10
        },
        headers={
            "Authorization": "Bearer valid_token"
        }
    )
    assert response.status_code == 200
    assert "rules" in response.json()
    assert len(response.json()["rules"]) > 0 