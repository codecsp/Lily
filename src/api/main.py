from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.security import OAuth2PasswordBearer
from fastapi.openapi.utils import get_openapi
from typing import List, Optional, Dict, Any
from datetime import datetime
import hmac
import hashlib
import yaml
from pathlib import Path
from src.common.config import settings
from src.inbound.monte_carlo.client import MonteCarloClient
from src.outbound.security.transformer import SecurityTransformer
from src.storage.dynamodb import DynamoDBStorage

app = FastAPI(
    title="Atlan Lily API",
    description="API for real-time metadata ingestion and consumption",
    version="1.0.0"
)

# Load OpenAPI specification
def load_openapi_spec():
    spec_path = Path(__file__).parent.parent.parent / "docs" / "swagger.yaml"
    with open(spec_path) as f:
        return yaml.safe_load(f)

# Override OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Merge with custom spec
    custom_spec = load_openapi_spec()
    openapi_schema.update(custom_spec)
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
monte_carlo_client = MonteCarloClient()
security_transformer = SecurityTransformer()
storage = DynamoDBStorage()

async def verify_token(token: str = Depends(oauth2_scheme)):
    # TODO: Implement proper JWT verification
    return token

async def verify_webhook_signature(
    x_monte_carlo_signature: str = Header(None),
    body: bytes = None
):
    if not x_monte_carlo_signature:
        raise HTTPException(status_code=401, detail="Missing signature")
    
    if not monte_carlo_client.verify_webhook_signature(body, x_monte_carlo_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

@app.post("/webhooks/monte-carlo")
async def monte_carlo_webhook(
    body: Dict[str, Any],
    signature: str = Header(..., alias="X-Monte-Carlo-Signature")
):
    """Handle webhook events from Monte Carlo."""
    try:
        result = monte_carlo_client.process_webhook(
            body.encode(),
            signature
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events/{event_id}")
async def get_event(
    event_id: str,
    token: str = Depends(verify_token)
):
    """Get event details by ID."""
    event = storage.get_metadata(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@app.post("/security/rules")
async def create_security_rule(
    rule: Dict[str, Any],
    token: str = Depends(verify_token)
):
    """Create a new security rule."""
    try:
        transformed_rule = security_transformer.transform_security_rule(rule)
        if not security_transformer.validate_rule(transformed_rule):
            raise HTTPException(status_code=400, detail="Invalid rule format")
        
        event_id = storage.store_metadata({
            "event_id": transformed_rule["rule_id"],
            "event_type": "security_rule",
            "timestamp": transformed_rule["metadata"]["created_at"],
            "source": "atlan",
            "payload": transformed_rule
        })
        
        downstream_rules = security_transformer.format_for_downstream(transformed_rule)
        
        return {
            "rule_id": transformed_rule["rule_id"],
            "status": "created",
            "downstream_rules": downstream_rules
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/security/rules/{rule_id}")
async def update_security_rule(
    rule_id: str,
    rule: Dict[str, Any],
    token: str = Depends(verify_token)
):
    """Update an existing security rule."""
    try:
        existing_rule = storage.get_metadata(rule_id)
        if not existing_rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        updated_rule = {**existing_rule["payload"], **rule}
        transformed_rule = security_transformer.transform_security_rule(updated_rule)
        
        if not security_transformer.validate_rule(transformed_rule):
            raise HTTPException(status_code=400, detail="Invalid rule format")
        
        storage.update_metadata(rule_id, {
            "payload": transformed_rule,
            "updated_at": datetime.utcnow().isoformat()
        })
        
        downstream_rules = security_transformer.format_for_downstream(transformed_rule)
        
        return {
            "rule_id": rule_id,
            "status": "updated",
            "downstream_rules": downstream_rules
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/security/rules/{rule_id}")
async def delete_security_rule(
    rule_id: str,
    token: str = Depends(verify_token)
):
    """Delete a security rule."""
    try:
        if not storage.delete_metadata(rule_id):
            raise HTTPException(status_code=404, detail="Rule not found")
        return {"rule_id": rule_id, "status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events")
async def query_events(
    event_type: Optional[str] = None,
    source: Optional[str] = None,
    tenant_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    token: str = Depends(verify_token)
):
    """Query events with various filters."""
    try:
        events = storage.query_metadata(
            event_type=event_type,
            source=source,
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        return {"events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/security/rules")
async def query_security_rules(
    rule_type: Optional[str] = None,
    asset_id: Optional[str] = None,
    asset_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    token: str = Depends(verify_token)
):
    """Query security rules with various filters."""
    try:
        rules = storage.query_metadata(
            event_type="security_rule",
            source="atlan",
            limit=limit
        )
        return {"rules": [rule["payload"] for rule in rules]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        debug=settings.API_DEBUG
    ) 