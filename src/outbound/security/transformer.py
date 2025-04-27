from typing import Dict, Any, List
from datetime import datetime
import json

class SecurityTransformer:
    def __init__(self):
        self.supported_rule_types = ["PII", "GDPR", "CUSTOM"]

    def transform_security_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a security rule into a standardized format."""
        if "rule_type" not in rule_data:
            raise ValueError("Missing required field: rule_type")
        
        if rule_data["rule_type"] not in self.supported_rule_types:
            raise ValueError(f"Unsupported rule type: {rule_data['rule_type']}")

        transformed_rule = {
            "rule_id": rule_data.get("rule_id", self._generate_rule_id()),
            "rule_type": rule_data["rule_type"],
            "asset_id": rule_data.get("asset_id"),
            "asset_type": rule_data.get("asset_type"),
            "conditions": self._transform_conditions(rule_data.get("conditions", [])),
            "actions": self._transform_actions(rule_data.get("actions", [])),
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "source": "atlan",
                "version": "1.0"
            }
        }

        return transformed_rule

    def _transform_conditions(self, conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform conditions into a standardized format."""
        transformed_conditions = []
        
        for condition in conditions:
            if not all(k in condition for k in ["field", "operator", "value"]):
                raise ValueError("Invalid condition format")
            
            transformed_condition = {
                "field": condition["field"],
                "operator": condition["operator"],
                "value": condition["value"],
                "metadata": {
                    "description": condition.get("description", ""),
                    "severity": condition.get("severity", "medium")
                }
            }
            transformed_conditions.append(transformed_condition)
        
        return transformed_conditions

    def _transform_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform actions into a standardized format."""
        transformed_actions = []
        
        for action in actions:
            if "type" not in action:
                raise ValueError("Invalid action format")
            
            transformed_action = {
                "type": action["type"],
                "parameters": action.get("parameters", {}),
                "metadata": {
                    "description": action.get("description", ""),
                    "priority": action.get("priority", "normal")
                }
            }
            transformed_actions.append(transformed_action)
        
        return transformed_actions

    def _generate_rule_id(self) -> str:
        """Generate a unique rule ID."""
        return f"rule_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    def validate_rule(self, rule: Dict[str, Any]) -> bool:
        """Validate a security rule."""
        required_fields = ["rule_type", "asset_id", "conditions", "actions"]
        
        # Check required fields
        for field in required_fields:
            if field not in rule:
                return False
        
        # Validate rule type
        if rule["rule_type"] not in self.supported_rule_types:
            return False
        
        # Validate conditions
        for condition in rule["conditions"]:
            if not all(k in condition for k in ["field", "operator", "value"]):
                return False
        
        # Validate actions
        for action in rule["actions"]:
            if "type" not in action:
                return False
        
        return True

    def format_for_downstream(self, rule: Dict[str, Any], target_system: str) -> Dict[str, Any]:
        """Format the rule for a specific downstream system."""
        if target_system == "snowflake":
            return self._format_for_snowflake(rule)
        elif target_system == "databricks":
            return self._format_for_databricks(rule)
        else:
            raise ValueError(f"Unsupported target system: {target_system}")

    def _format_for_snowflake(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Format the rule for Snowflake."""
        return {
            "type": "snowflake_policy",
            "name": f"atlan_{rule['rule_id']}",
            "database": rule.get("database", "PUBLIC"),
            "schema": rule.get("schema", "PUBLIC"),
            "table": rule.get("table"),
            "conditions": self._format_snowflake_conditions(rule["conditions"]),
            "actions": self._format_snowflake_actions(rule["actions"])
        }

    def _format_for_databricks(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Format the rule for Databricks."""
        return {
            "type": "databricks_policy",
            "name": f"atlan_{rule['rule_id']}",
            "catalog": rule.get("catalog", "hive_metastore"),
            "schema": rule.get("schema", "default"),
            "table": rule.get("table"),
            "conditions": self._format_databricks_conditions(rule["conditions"]),
            "actions": self._format_databricks_actions(rule["actions"])
        }

    def _format_snowflake_conditions(self, conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format conditions for Snowflake."""
        return [
            {
                "column": condition["field"],
                "operator": condition["operator"],
                "value": condition["value"]
            }
            for condition in conditions
        ]

    def _format_databricks_conditions(self, conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format conditions for Databricks."""
        return [
            {
                "column": condition["field"],
                "operator": condition["operator"],
                "value": condition["value"]
            }
            for condition in conditions
        ]

    def _format_snowflake_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format actions for Snowflake."""
        return [
            {
                "type": action["type"],
                "parameters": action["parameters"]
            }
            for action in actions
        ]

    def _format_databricks_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format actions for Databricks."""
        return [
            {
                "type": action["type"],
                "parameters": action["parameters"]
            }
            for action in actions
        ] 