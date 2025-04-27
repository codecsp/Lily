import os
from typing import Dict, Any
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    # AWS Configuration
    AWS_REGION: str = Field(default="us-east-1")
    AWS_ACCESS_KEY_ID: str = Field(default="")
    AWS_SECRET_ACCESS_KEY: str = Field(default="")
    
    # DynamoDB Configuration
    DYNAMODB_TABLE_NAME: str = Field(default="atlan-lily-metadata")
    DYNAMODB_ENDPOINT_URL: str = Field(default="")
    
    # EventBridge Configuration
    EVENT_BUS_NAME: str = Field(default="atlan-lily-bus")
    
    # SQS Configuration
    INBOUND_QUEUE_URL: str = Field(default="")
    OUTBOUND_QUEUE_URL: str = Field(default="")
    
    # API Configuration
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    API_DEBUG: bool = Field(default=False)
    
    # Security Configuration
    JWT_SECRET_KEY: str = Field(default="")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    
    # Monte Carlo Configuration
    MONTE_CARLO_API_KEY: str = Field(default="")
    MONTE_CARLO_WEBHOOK_SECRET: str = Field(default="")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    @classmethod
    def get_settings(cls) -> "Settings":
        return cls()

    def get_aws_config(self) -> Dict[str, Any]:
        return {
            "region_name": self.AWS_REGION,
            "aws_access_key_id": self.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": self.AWS_SECRET_ACCESS_KEY,
        }

    def get_dynamodb_config(self) -> Dict[str, Any]:
        config = self.get_aws_config()
        if self.DYNAMODB_ENDPOINT_URL:
            config["endpoint_url"] = self.DYNAMODB_ENDPOINT_URL
        return config

# Create a global settings instance
settings = Settings.get_settings() 