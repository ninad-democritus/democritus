#!/usr/bin/env python3
"""
Debug script to test relationship validation
"""

import sys
import os
sys.path.append('services/data-pipeline')

from app.utils.validators import SchemaValidator

# Your actual relationship data from the error
test_relationships = [
    {
        "from": "Location",
        "to": "Event",
        "type": "one_to_many",
        "foreign_key": "NOC",
        "references": "NOC",
        "confidence": 0.9,
        "description": "Each Event can have multiple Location records"
    },
    {
        "from": "Event",
        "to": "Location",
        "type": "many_to_one",
        "foreign_key": "NOC",
        "references": "NOC",
        "confidence": 0.9,
        "description": "Each Event belongs to one Location (via NOC)"
    }
]

# Test entities
test_entities = [
    {"name": "Location"},
    {"name": "Event"}
]

# Test the validation
print("Testing relationship validation...")
print("Relationship 0:", test_relationships[0])
print("Keys in relationship 0:", list(test_relationships[0].keys()))

is_valid, error = SchemaValidator._validate_relationships(test_relationships, test_entities)
print(f"Validation result: {is_valid}")
if not is_valid:
    print(f"Error: {error}")
else:
    print("Validation passed!")

