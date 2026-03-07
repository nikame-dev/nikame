"""Data model shorthand parser for NIKAME wizard.

Converts strings like 'User: name, email; Post: title, body, user_id->User'
into structured dicts compatible with DataModelConfig.
"""

from __future__ import annotations
import re
from typing import Any


def parse_model_shorthand(shorthand: str) -> dict[str, Any]:
    """Parse shorthand into a dict of model definitions.
    
    Format: 'Model1: field1, field2(type), field3->Target; Model2: ...'
    """
    models: dict[str, Any] = {}
    
    # Split by semicolon for multiple models
    segments = shorthand.split(";")
    for segment in segments:
        segment = segment.strip()
        if not segment or ":" not in segment:
            continue
            
        model_name, fields_str = segment.split(":", 1)
        model_name = model_name.strip()
        fields_raw = [f.strip() for f in fields_str.split(",") if f.strip()]
        
        model_def: dict[str, Any] = {
            "fields": {},
            "relationships": {}
        }
        
        for field_raw in fields_raw:
            # 1. Check for relationship (e.g., user_id->User)
            if "->" in field_raw:
                field_name, target = field_raw.split("->", 1)
                field_name = field_name.strip()
                target = target.strip()
                model_def["relationships"][field_name] = {
                    "type": "many-to-one",
                    "target": target
                }
                # Also add the field itself
                model_def["fields"][field_name] = "str"
                continue
                
            # 2. Check for type (e.g., age(int))
            match = re.match(r"(\w+)\((\w+)\)", field_raw)
            if match:
                field_name, field_type = match.groups()
                model_def["fields"][field_name] = field_type
            else:
                # 3. Plain field (default to str)
                model_def["fields"][field_raw] = "str"
        
        models[model_name] = model_def
        
    return models
