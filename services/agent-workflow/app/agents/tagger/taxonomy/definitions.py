"""
OpenMetadata classification taxonomy definitions
"""
from typing import Dict, List, Any


# OpenMetadata-compatible classification hierarchy
CLASSIFICATION_TAXONOMY: Dict[str, Dict[str, Any]] = {
    'PII': {
        'description': 'Personally Identifiable Information',
        'subcategories': {
            'PII.Sensitive': {
                'description': 'Sensitive personally identifiable information',
                'examples': ['email', 'phone', 'ssn', 'passport', 'driver_license', 'address', 'name'],
                'mutually_exclusive_with': ['PII.NonSensitive']
            },
            'PII.NonSensitive': {
                'description': 'Non-sensitive identifiers',
                'examples': ['customer_id', 'order_id', 'uuid', 'reference_number'],
                'mutually_exclusive_with': ['PII.Sensitive']
            }
        }
    },
    
    'Finance': {
        'description': 'Financial and monetary data',
        'subcategories': {
            'Finance.Reporting': {
                'description': 'Financial reporting and metrics',
                'examples': ['revenue', 'cost', 'price', 'amount', 'balance', 'profit']
            },
            'Finance.Sensitive': {
                'description': 'Sensitive financial information',
                'examples': ['salary', 'wage', 'credit_card', 'bank_account', 'routing_number']
            }
        }
    },
    
    'Temporal': {
        'description': 'Date and time related data',
        'subcategories': {
            'Temporal.Fact': {
                'description': 'Event timestamps and transaction dates',
                'examples': ['order_date', 'transaction_time', 'event_timestamp', 'created_at']
            },
            'Temporal.Dimension': {
                'description': 'Descriptive temporal attributes',
                'examples': ['birth_date', 'expiry_date', 'hire_date', 'anniversary']
            }
        }
    },
    
    'DataQuality': {
        'description': 'Data quality and governance indicators',
        'subcategories': {
            'DataQuality.Audit': {
                'description': 'Audit trail and tracking columns',
                'examples': ['created_by', 'updated_by', 'modified_at', 'version']
            },
            'DataQuality.Completeness': {
                'description': 'Data completeness indicators',
                'examples': ['high_null_percentage', 'missing_values']
            }
        }
    },
    
    'DataDomain': {
        'description': 'Data domain and role classifications',
        'subcategories': {
            'DataDomain.Fact': {
                'description': 'Fact table designation',
                'examples': ['transactional_data', 'measurements', 'events'],
                'mutually_exclusive_with': ['DataDomain.Dimension']
            },
            'DataDomain.Dimension': {
                'description': 'Dimension table designation',
                'examples': ['reference_data', 'descriptive_attributes'],
                'mutually_exclusive_with': ['DataDomain.Fact']
            },
            'DataDomain.JoinKey': {
                'description': 'Foreign key or join key columns',
                'examples': ['foreign_key', 'relationship_column']
            }
        }
    },
    
    'Categorical': {
        'description': 'Categorical data classifications',
        'subcategories': {
            'Categorical.LowCardinality': {
                'description': 'Few distinct values (< 10)',
                'examples': ['status', 'type', 'category', 'flag']
            },
            'Categorical.HighCardinality': {
                'description': 'Many distinct values (> 1000)',
                'examples': ['unique_identifiers', 'descriptive_text']
            }
        }
    },
    
    'Boolean': {
        'description': 'Boolean flags and indicators',
        'subcategories': {
            'Boolean.Flag': {
                'description': 'True/false flags',
                'examples': ['is_active', 'has_permission', 'enabled', 'deleted']
            }
        }
    },
    
    'Location': {
        'description': 'Geographic and location data',
        'subcategories': {
            'Location.Geographic': {
                'description': 'Geographic location information',
                'examples': ['city', 'state', 'country', 'zip_code', 'latitude', 'longitude', 'region']
            }
        }
    }
}


def get_all_tags() -> List[str]:
    """Get flat list of all classification tags"""
    tags = []
    for category, cat_data in CLASSIFICATION_TAXONOMY.items():
        if 'subcategories' in cat_data:
            for subcategory in cat_data['subcategories'].keys():
                tags.append(subcategory)
        else:
            tags.append(category)
    return tags


def get_mutually_exclusive_tags() -> Dict[str, List[str]]:
    """Get mapping of tags to their mutually exclusive alternatives"""
    exclusions = {}
    for category, cat_data in CLASSIFICATION_TAXONOMY.items():
        if 'subcategories' in cat_data:
            for subcategory, sub_data in cat_data['subcategories'].items():
                if 'mutually_exclusive_with' in sub_data:
                    exclusions[subcategory] = sub_data['mutually_exclusive_with']
    return exclusions

