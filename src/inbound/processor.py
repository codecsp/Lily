import json
import boto3
from typing import Dict, Any
from src.common.config import settings
from src.inbound.monte_carlo.client import MonteCarloClient
from src.storage.dynamodb import DynamoDBStorage

class InboundProcessor:
    def __init__(self):
        self.monte_carlo_client = MonteCarloClient()
        self.storage = DynamoDBStorage()
        self.sqs = boto3.client('sqs', **settings.get_aws_config())
        self.eventbridge = boto3.client('events', **settings.get_aws_config())

    def process_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """Process a webhook event from Monte Carlo."""
        # Verify webhook signature
        if not self.monte_carlo_client.verify_webhook_signature(payload, signature):
            raise ValueError("Invalid webhook signature")

        # Parse the webhook payload
        event_data = json.loads(payload)
        parsed_event = self.monte_carlo_client.parse_webhook_event(event_data)

        # Enrich the event data
        enriched_data = self.monte_carlo_client.enrich_incident_data(parsed_event["payload"])

        # Store the enriched data
        event_id = self.storage.store_metadata({
            **parsed_event,
            "payload": enriched_data
        })

        # Send to EventBridge for further processing
        self._publish_to_eventbridge(parsed_event)

        return {
            "event_id": event_id,
            "status": "processed"
        }

    def process_sqs_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message from SQS."""
        try:
            # Parse the message body
            body = json.loads(message["Body"])
            
            # Process the event
            result = self.process_webhook(
                json.dumps(body).encode(),
                message.get("MessageAttributes", {}).get("Signature", {}).get("StringValue", "")
            )

            # Delete the message from the queue
            self.sqs.delete_message(
                QueueUrl=settings.INBOUND_QUEUE_URL,
                ReceiptHandle=message["ReceiptHandle"]
            )

            return result
        except Exception as e:
            print(f"Error processing SQS message: {str(e)}")
            raise

    def _publish_to_eventbridge(self, event: Dict[str, Any]) -> None:
        """Publish an event to EventBridge."""
        try:
            self.eventbridge.put_events(
                Entries=[
                    {
                        "Source": "atlan.lily",
                        "DetailType": event["event_type"],
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
                    QueueUrl=settings.INBOUND_QUEUE_URL,
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
    processor = InboundProcessor()
    processor.start_processing()

if __name__ == "__main__":
    main() 