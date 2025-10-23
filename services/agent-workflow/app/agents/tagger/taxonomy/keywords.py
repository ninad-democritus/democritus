"""
Keyword mappings for classification assignment
"""
from typing import Dict, List


# Map semantic types to classification tags
SEMANTIC_TYPE_MAPPINGS: Dict[str, List[str]] = {
    # PII Sensitive
    'email': ['PII.Sensitive'],
    'phone_number': ['PII.Sensitive'],
    'ssn': ['PII.Sensitive'],
    'passport': ['PII.Sensitive'],
    'driver_license': ['PII.Sensitive'],
    'address': ['PII.Sensitive', 'Location.Geographic'],
    'name': ['PII.Sensitive'],
    'person_name': ['PII.Sensitive'],
    
    # PII Non-Sensitive
    'identifier': ['PII.NonSensitive'],
    'uuid': ['PII.NonSensitive'],
    'guid': ['PII.NonSensitive'],
    
    # Finance
    'currency': ['Finance.Reporting'],
    'money': ['Finance.Reporting'],
    'credit_card': ['Finance.Sensitive', 'PII.Sensitive'],
    
    # Temporal
    'date': ['Temporal'],
    'datetime': ['Temporal'],
    'timestamp': ['Temporal'],
    'time': ['Temporal'],
    
    # Location
    'zipcode': ['Location.Geographic'],
    'postal_code': ['Location.Geographic'],
    'latitude': ['Location.Geographic'],
    'longitude': ['Location.Geographic'],
    'coordinates': ['Location.Geographic'],
}


# Keywords for pattern-based classification matching
# Used for matching against canonical names and synonyms
CLASSIFICATION_KEYWORDS: Dict[str, List[str]] = {
    'PII.Sensitive': [
        'email', 'e-mail', 'mail',
        'phone', 'mobile', 'telephone', 'tel', 'fax',
        'ssn', 'social_security',
        'passport', 'license', 'licence',
        'address', 'street', 'location',
        'name', 'first_name', 'last_name', 'full_name', 'firstname', 'lastname',
        'dob', 'birth_date', 'birthdate',
        'password', 'secret', 'token', 'credential'
    ],
    
    'PII.NonSensitive': [
        'id', 'identifier', 'key', 'code', 'number', 'ref', 'reference',
        'uuid', 'guid',
        'customer_id', 'user_id', 'order_id', 'product_id',
        'account_number', 'member_id'
    ],
    
    'Finance.Reporting': [
        'amount', 'price', 'cost', 'value',
        'revenue', 'sales', 'income',
        'profit', 'loss', 'margin',
        'balance', 'total', 'subtotal',
        'tax', 'fee', 'charge',
        'payment', 'transaction'
    ],
    
    'Finance.Sensitive': [
        'salary', 'wage', 'compensation', 'pay',
        'credit_card', 'card_number', 'cvv', 'cvc',
        'bank_account', 'account_number', 'routing_number',
        'iban', 'swift'
    ],
    
    'Temporal.Fact': [
        'order_date', 'purchase_date', 'transaction_date',
        'event_date', 'event_time', 'timestamp',
        'created_at', 'created_on', 'created_date',
        'updated_at', 'updated_on', 'modified_at',
        'occurred_at', 'recorded_at'
    ],
    
    'Temporal.Dimension': [
        'birth_date', 'birthdate', 'dob',
        'hire_date', 'start_date', 'end_date',
        'expiry_date', 'expiration_date',
        'anniversary', 'effective_date'
    ],
    
    'DataQuality.Audit': [
        'created_by', 'created_user',
        'updated_by', 'modified_by', 'changed_by',
        'deleted_by', 'archived_by',
        'version', 'revision', 'audit'
    ],
    
    'Boolean.Flag': [
        'is_', 'has_', 'can_', 'should_',
        'active', 'inactive', 'enabled', 'disabled',
        'deleted', 'archived',
        'valid', 'invalid',
        'approved', 'rejected',
        'flag'
    ],
    
    'Location.Geographic': [
        'address', 'street', 'avenue', 'road',
        'city', 'town', 'municipality',
        'state', 'province', 'region',
        'country', 'nation',
        'zip', 'zipcode', 'postal_code', 'postcode',
        'latitude', 'lat', 'longitude', 'lon', 'lng',
        'coordinates', 'geolocation', 'geo'
    ],
    
    'Categorical.LowCardinality': [
        'status', 'state', 'type', 'kind',
        'category', 'class', 'classification',
        'group', 'segment', 'tier',
        'priority', 'level', 'grade'
    ]
}


# Patterns for identifying specific classifications
# Used for regex or exact matching
CLASSIFICATION_PATTERNS: Dict[str, List[str]] = {
    'DataDomain.JoinKey': [
        r'.*_id$',           # ends with _id
        r'.*_key$',          # ends with _key
        r'.*_code$',         # ends with _code
        r'.*_ref$',          # ends with _ref
        r'fk_.*',            # starts with fk_
    ],
    
    'Boolean.Flag': [
        r'^is_.*',           # starts with is_
        r'^has_.*',          # starts with has_
        r'^can_.*',          # starts with can_
        r'^should_.*',       # starts with should_
        r'.*_flag$',         # ends with _flag
    ],
    
    'DataQuality.Audit': [
        r'.*_at$',           # ends with _at (timestamps)
        r'.*_by$',           # ends with _by (users)
        r'.*_date$',         # ends with _date
    ]
}

