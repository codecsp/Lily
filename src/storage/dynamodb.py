import boto3
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from src.common.config import settings

class DynamoDBStorage:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', **settings.get_dynamodb_config())
        self.table = self.dynamodb.Table(settings.DYNAMODB_TABLE_NAME)

    def store_metadata(self, metadata: Dict[str, Any]) -> str:
        """Store metadata in DynamoDB."""
        if "event_id" not in metadata:
            raise ValueError("Missing required field: event_id")

        item = {
            "event_id": metadata["event_id"],
            "event_type": metadata.get("event_type", "unknown"),
            "timestamp": metadata.get("timestamp", datetime.utcnow().isoformat()),
            "source": metadata.get("source", "unknown"),
            "tenant_id": metadata.get("tenant_id", "default"),
            "payload": metadata.get("payload", {}),
            "metadata": metadata.get("metadata", {}),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        self.table.put_item(Item=item)
        return item["event_id"]

    def get_metadata(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve metadata by event ID."""
        response = self.table.get_item(Key={"event_id": event_id})
        return response.get("Item")

    def query_metadata(self, 
                      event_type: Optional[str] = None,
                      source: Optional[str] = None,
                      tenant_id: Optional[str] = None,
                      start_time: Optional[str] = None,
                      end_time: Optional[str] = None,
                      limit: int = 100) -> List[Dict[str, Any]]:
        """Query metadata with various filters."""
        filter_expressions = []
        expression_values = {}
        expression_names = {}

        if event_type:
            filter_expressions.append("event_type = :event_type")
            expression_values[":event_type"] = event_type

        if source:
            filter_expressions.append("source = :source")
            expression_values[":source"] = source

        if tenant_id:
            filter_expressions.append("tenant_id = :tenant_id")
            expression_values[":tenant_id"] = tenant_id

        if start_time:
            filter_expressions.append("timestamp >= :start_time")
            expression_values[":start_time"] = start_time

        if end_time:
            filter_expressions.append("timestamp <= :end_time")
            expression_values[":end_time"] = end_time

        query_params = {
            "Limit": limit
        }

        if filter_expressions:
            query_params["FilterExpression"] = " AND ".join(filter_expressions)
            query_params["ExpressionAttributeValues"] = expression_values
            if expression_names:
                query_params["ExpressionAttributeNames"] = expression_names

        response = self.table.scan(**query_params)
        return response.get("Items", [])

    def update_metadata(self, event_id: str, updates: Dict[str, Any]) -> bool:
        """Update metadata for a specific event."""
        update_expressions = []
        expression_values = {}
        expression_names = {}

        for key, value in updates.items():
            if key in ["event_id", "created_at"]:
                continue  # Skip immutable fields
            
            update_expressions.append(f"#{key} = :{key}")
            expression_values[f":{key}"] = value
            expression_names[f"#{key}"] = key

        if not update_expressions:
            return False

        update_expressions.append("#updated_at = :updated_at")
        expression_values[":updated_at"] = datetime.utcnow().isoformat()
        expression_names["#updated_at"] = "updated_at"

        try:
            self.table.update_item(
                Key={"event_id": event_id},
                UpdateExpression=f"SET {', '.join(update_expressions)}",
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names
            )
            return True
        except Exception as e:
            print(f"Error updating metadata: {str(e)}")
            return False

    def delete_metadata(self, event_id: str) -> bool:
        """Delete metadata for a specific event."""
        try:
            self.table.delete_item(Key={"event_id": event_id})
            return True
        except Exception as e:
            print(f"Error deleting metadata: {str(e)}")
            return False

    def batch_store_metadata(self, metadata_list: List[Dict[str, Any]]) -> List[str]:
        """Store multiple metadata items in batch."""
        with self.table.batch_writer() as batch:
            stored_ids = []
            for metadata in metadata_list:
                if "event_id" not in metadata:
                    continue

                item = {
                    "event_id": metadata["event_id"],
                    "event_type": metadata.get("event_type", "unknown"),
                    "timestamp": metadata.get("timestamp", datetime.utcnow().isoformat()),
                    "source": metadata.get("source", "unknown"),
                    "tenant_id": metadata.get("tenant_id", "default"),
                    "payload": metadata.get("payload", {}),
                    "metadata": metadata.get("metadata", {}),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }

                batch.put_item(Item=item)
                stored_ids.append(item["event_id"])

            return stored_ids

    def create_table_if_not_exists(self):
        """Create the DynamoDB table if it doesn't exist."""
        try:
            self.table = self.dynamodb.create_table(
                TableName=settings.DYNAMODB_TABLE_NAME,
                KeySchema=[
                    {
                        "AttributeName": "event_id",
                        "KeyType": "HASH"
                    }
                ],
                AttributeDefinitions=[
                    {
                        "AttributeName": "event_id",
                        "AttributeType": "S"
                    }
                ],
                BillingMode="PAY_PER_REQUEST"
            )
            self.table.wait_until_exists()
        except self.dynamodb.meta.client.exceptions.ResourceInUseException:
            # Table already exists
            pass 