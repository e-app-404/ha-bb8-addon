#!/usr/bin/env python3
"""
BB-8 Command Schema Validator
Phase B2 - Strict JSON validation with clamping and clear error messages
"""

import json
import jsonschema
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import math

class BB8CommandValidator:
    """Validates BB-8 MQTT commands against schema with clamping and safety checks"""
    
    def __init__(self, schema_path: str):
        """Load schema from JSON file"""
        with open(schema_path, 'r') as f:
            self.schema_data = json.load(f)
        
        # Extract command schemas
        self.command_schemas = self.schema_data.get('commands', {})
        self.ack_schema = self.schema_data['definitions']['acknowledgment_base']
        
        # Safety state
        self.estop_active = False
    
    def clamp_value(self, value: Any, field_name: str, min_val: int, max_val: int) -> Tuple[Any, Optional[str]]:
        """Clamp numeric values to valid range, return (clamped_value, warning_message)"""
        if not isinstance(value, (int, float)):
            return value, f"field '{field_name}' must be numeric"
        
        original = value
        
        # Special handling for heading (wrap around)
        if field_name == 'heading':
            value = int(value) % 360
            if value != original:
                return value, f"heading {original} wrapped to {value}"
        else:
            # Standard clamping
            value = max(min_val, min(max_val, int(value)))
            if value != original:
                return value, f"{field_name} {original} clamped to {value}"
        
        return value, None
    
    def validate_command(self, topic: str, payload: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Validate command payload against schema
        Returns: (is_valid, processed_payload, error_message)
        """
        # Check if topic is supported
        if topic not in self.command_schemas:
            return False, payload, f"unsupported command topic: {topic}"
        
        # Check emergency stop for motion commands
        if topic == 'bb8/cmd/drive' and self.estop_active:
            return False, payload, "motion commands blocked - emergency stop active"
        
        schema = self.command_schemas[topic]
        processed = payload.copy()
        warnings = []
        
        try:
            # Pre-validation clamping for numeric fields
            if topic == 'bb8/cmd/drive':
                if 'speed' in processed:
                    processed['speed'], warning = self.clamp_value(processed['speed'], 'speed', 0, 255)
                    if warning:
                        warnings.append(warning)
                
                if 'heading' in processed:
                    processed['heading'], warning = self.clamp_value(processed['heading'], 'heading', 0, 359)
                    if warning:
                        warnings.append(warning)
                
                if 'ms' in processed:
                    processed['ms'], warning = self.clamp_value(processed['ms'], 'ms', 0, 5000)
                    if warning:
                        warnings.append(warning)
            
            elif topic == 'bb8/cmd/led':
                for color in ['r', 'g', 'b']:
                    if color in processed:
                        processed[color], warning = self.clamp_value(processed[color], color, 0, 255)
                        if warning:
                            warnings.append(warning)
            
            # JSON Schema validation
            jsonschema.validate(processed, schema)
            
            # Handle estop state changes
            if topic == 'bb8/cmd/estop':
                self.estop_active = True
                warnings.append("emergency stop activated - all motion disabled")
            elif topic == 'bb8/cmd/clear_estop':
                if not self.estop_active:
                    return False, processed, "cannot clear estop - no active emergency stop"
                self.estop_active = False
                warnings.append("emergency stop cleared - motion enabled")
            
            warning_msg = '; '.join(warnings) if warnings else None
            return True, processed, warning_msg
            
        except jsonschema.ValidationError as e:
            return False, payload, f"validation error: {e.message}"
        except Exception as e:
            return False, payload, f"validation failed: {str(e)}"
    
    def create_ack(self, command_topic: str, success: bool, cid: Optional[str] = None, 
                   reason: Optional[str] = None) -> Dict[str, Any]:
        """Create acknowledgment message"""
        # Extract command name from topic
        cmd_name = command_topic.split('/')[-1]
        
        ack = {
            'ok': success,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        if cid:
            ack['cid'] = cid
        
        if reason:
            ack['reason'] = reason
        
        return ack
    
    def get_ack_topic(self, command_topic: str) -> str:
        """Convert command topic to acknowledgment topic"""
        # bb8/cmd/drive -> bb8/ack/drive
        return command_topic.replace('/cmd/', '/ack/')


def test_validator():
    """Test the validator with sample commands"""
    import tempfile
    import os
    
    # Create temp schema file
    schema_content = """
    {
        "definitions": {
            "correlation_id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]{1,32}$"},
            "acknowledgment_base": {
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                    "cid": {"$ref": "#/definitions/correlation_id"},
                    "reason": {"type": "string"},
                    "timestamp": {"type": "string", "format": "date-time"}
                },
                "required": ["ok"]
            }
        },
        "commands": {
            "bb8/cmd/drive": {
                "type": "object",
                "properties": {
                    "speed": {"type": "integer", "minimum": 0, "maximum": 255},
                    "heading": {"type": "integer", "minimum": 0, "maximum": 359},
                    "ms": {"type": "integer", "minimum": 0, "maximum": 5000},
                    "cid": {"$ref": "#/definitions/correlation_id"}
                },
                "required": ["speed", "heading", "ms"],
                "additionalProperties": false
            }
        }
    }
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(schema_content)
        schema_path = f.name
    
    try:
        validator = BB8CommandValidator(schema_path)
        
        # Test valid command
        valid_cmd = {"speed": 100, "heading": 90, "ms": 2000}
        is_valid, processed, error = validator.validate_command("bb8/cmd/drive", valid_cmd)
        print(f"Valid command: {is_valid}, Error: {error}")
        
        # Test clamping
        clamp_cmd = {"speed": 300, "heading": 400, "ms": 10000}
        is_valid, processed, error = validator.validate_command("bb8/cmd/drive", clamp_cmd)
        print(f"Clamped command: {is_valid}, Processed: {processed}, Warning: {error}")
        
        # Test missing field
        invalid_cmd = {"speed": 100, "heading": 90}  # missing 'ms'
        is_valid, processed, error = validator.validate_command("bb8/cmd/drive", invalid_cmd)
        print(f"Invalid command: {is_valid}, Error: {error}")
        
    finally:
        os.unlink(schema_path)


if __name__ == "__main__":
    test_validator()