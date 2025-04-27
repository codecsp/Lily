import json
import boto3
from typing import Dict, Any, List
from src.common.config import settings
from src.outbound.security.transformer import SecurityTransformer
from src.storage.dynamodb import DynamoDBStorage

class OutboundProcessor:
    def __init__(self):
        self.security_transformer = SecurityTransformer()
        self.storage = DynamoDBStorage()
        self.sqs = boto3.client('sqs', **settings.get_aws_config())
        self.eventbridge = boto3.client('events', **settings.get_aws_config())

    def process_security_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process a security event from DynamoDB Streams."""
        # Transform the security rule
        transformed_rule = self.security_transformer.transform_security_rule(event)

        # Validate the transformed rule
        if not self.security_transformer.validate_rule(transformed_rule):
            raise ValueError("Invalid security rule")

        # Store the transformed rule
        event_id = self.storage.store_metadata({
            "event_id": transformed_rule["rule_id"],
            "event_type": "security_rule",
            "timestamp": transformed_rule["metadata"]["created_at"],
            "source": "atlan",
            "payload": transformed_rule
        })

        # Format for downstream systems
        downstream_rules = self._format_for_downstream_systems(transformed_rule)

        # Send to EventBridge for further processing
        self._publish_to_eventbridge(transformed_rule)

        return {
            "event_id": event_id,
            "status": "processed",
            "downstream_rules": downstream_rules
        }

    def process_sqs_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message from SQS."""
        try:
            # Parse the message body
            body = json.loads(message["Body"])
            
            # Process the event
            result = self.process_security_event(body)

            # Delete the message from the queue
            self.sqs.delete_message(
                QueueUrl=settings.OUTBOUND_QUEUE_URL,
                ReceiptHandle=message["ReceiptHandle"]
            )

            return result
        except Exception as e:
            print(f"Error processing SQS message: {str(e)}")
            raise

    def _format_for_downstream_systems(self, rule: Dict[str, Any]) -> Dict[str, str]:
        """Format the rule for different downstream systems."""
        downstream_rules = {}
        
        # Format for Snowflake
        try:
            snowflake_rule = self.security_transformer.format_for_downstream(rule, "snowflake")
            downstream_rules["snowflake"] = snowflake_rule
        except Exception as e:
            print(f"Error formatting for Snowflake: {str(e)}")

        # Format for Databricks
        try:
            databricks_rule = self.security_transformer.format_for_downstream(rule, "databricks")
            downstream_rules["databricks"] = databricks_rule
        except Exception as e:
            print(f"Error formatting for Databricks: {str(e)}")

        return downstream_rules

    def _publish_to_eventbridge(self, event: Dict[str, Any]) -> None:
        """Publish an event to EventBridge."""
        try:
            self.eventbridge.put_events(
                Entries=[
                    {
                        "Source": "atlan.lily",
                        "DetailType": "security_rule",
                        "Detail": json.dumps(event),
                        "EventBusName": settings.EVENT_BUS_NAME
                    }
                ]
            )
        except Exception as e:
            print(f"Error publishing to EventBridge: {str(e)}")
            raise

    def start_processing(self):
        """Start processing messages from SQS."""
        while True:
            try:
                # Receive messages from SQS
                response = self.sqs.receive_message(
                    QueueUrl=settings.OUTBOUND_QUEUE_URL,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=20
                )

                messages = response.get("Messages", [])
                if not messages:
                    continue

                # Process each message
                for message in messages:
                    try:
                        self.process_sqs_message(message)
                    except Exception as e:
                        print(f"Error processing message: {str(e)}")
                        # Move to DLQ if needed
                        continue

            except Exception as e:
                print(f"Error in message processing loop: {str(e)}")
                continue

def main():
    processor = OutboundProcessor()
    processor.start_processing()

if __name__ == "__main__":
    main() 