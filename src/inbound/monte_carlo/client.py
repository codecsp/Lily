import json
import hmac
import hashlib
from typing import Dict, Any, Optional
import requests
from src.common.config import settings

class MonteCarloClient:
    def __init__(self):
        self.api_key = settings.MONTE_CARLO_API_KEY
        self.webhook_secret = settings.MONTE_CARLO_WEBHOOK_SECRET
        self.base_url = "https://api.getmontecarlo.com/v1"

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify the webhook signature from Monte Carlo."""
        if not self.webhook_secret:
            return True  # Skip verification if no secret is configured
        
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)

    def get_incident_details(self, incident_id: str) -> Dict[str, Any]:
        """Fetch detailed information about a specific incident."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{self.base_url}/incidents/{incident_id}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()

    def get_affected_assets(self, incident_id: str) -> Dict[str, Any]:
        """Fetch assets affected by a specific incident."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{self.base_url}/incidents/{incident_id}/assets",
            headers=headers
        )
        response.raise_for_status()
        return response.json()

    def parse_webhook_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate a webhook event from Monte Carlo."""
        required_fields = ["id", "type", "timestamp", "data"]
        for field in required_fields:
            if field not in payload:
                raise ValueError(f"Missing required field: {field}")

        return {
            "event_id": payload["id"],
            "event_type": payload["type"],
            "timestamp": payload["timestamp"],
            "source": "monte_carlo",
            "payload": payload["data"]
        }

    def enrich_incident_data(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich incident data with additional context."""
        incident_id = incident_data["id"]
        
        # Fetch additional details
        incident_details = self.get_incident_details(incident_id)
        affected_assets = self.get_affected_assets(incident_id)
        
        # Combine the data
        enriched_data = {
            **incident_data,
            "details": incident_details,
            "affected_assets": affected_assets,
            "metadata": {
                "source": "monte_carlo",
                "enrichment_timestamp": incident_details.get("updated_at")
            }
        }
        
        return enriched_data 