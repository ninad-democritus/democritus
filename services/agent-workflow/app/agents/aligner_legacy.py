from typing import List, Dict, Any
from dataclasses import dataclass
import logging
from .profiler import FileProfile, ColumnProfile
try:
    from ..observability import trace_agent, observability
except ImportError:
    # Fallback for when observability is not available
    def trace_agent(name):
        def decorator(func):
            return func
        return decorator
    
    class MockObservability:
        def create_agent_span(self, *args, **kwargs): return None
        def log_agent_output(self, *args, **kwargs): pass
        def end_agent_span(self, *args, **kwargs): pass
    
    observability = MockObservability()

logger = logging.getLogger(__name__)

@dataclass
class Entity:
    name: str
    source_file: str
    file_id: str
    columns: List[ColumnProfile]
    primary_key_candidates: List[str]
    entity_type: str  # 'fact', 'dimension', 'bridge'

class AlignerAgent:
    """
    Aligner Agent: Receives profiles and identifies potential entities within files.
    For MVP1, focuses on identifying entities like 'Customers', 'Sales', 'Orders', etc.
    """
    
    def __init__(self):
        # Common entity patterns and their indicators
        self.entity_patterns = {
            'customer': ['customer', 'client', 'user', 'account', 'buyer', 'person'],
            'order': ['order', 'purchase', 'transaction', 'sale'],
            'product': ['product', 'item', 'sku', 'inventory', 'catalog'],
            'invoice': ['invoice', 'bill', 'receipt', 'payment'],
            'employee': ['employee', 'staff', 'worker', 'personnel'],
            'vendor': ['vendor', 'supplier', 'partner'],
            'location': ['location', 'address', 'store', 'branch', 'region'],
            'category': ['category', 'type', 'classification', 'group'],
            'event': ['event', 'log', 'activity', 'action']
        }
        
        # Columns that typically indicate ID fields
        self.id_patterns = ['id', '_id', 'key', '_key', 'code', '_code', 'num', 'number']
        
    @trace_agent("AlignerAgent")
    def identify_entities(self, file_profiles: List[FileProfile]) -> List[Entity]:
        """Identify entities from file profiles"""
        span = observability.create_agent_span("AlignerAgent", {
            "input_files": [fp.file_name for fp in file_profiles],
            "total_files": len(file_profiles)
        })
        
        entities = []
        
        try:
            for file_profile in file_profiles:
                entity = self._analyze_file_for_entity(file_profile)
                if entity:
                    entities.append(entity)
            
            # Log entity identification results
            entity_metrics = {
                "entities_identified": len(entities),
                "entity_types": [e.entity_type for e in entities],
                "entity_names": [e.name for e in entities]
            }
            
            observability.log_agent_output("AlignerAgent", {
                "entities": [(e.name, e.entity_type) for e in entities]
            }, entity_metrics)
            
            observability.end_agent_span(span, {
                "entities_count": len(entities),
                "metrics": entity_metrics
            })
            
        except Exception as e:
            observability.end_agent_span(span, {}, str(e))
            raise
        
        return entities
    
    def _analyze_file_for_entity(self, file_profile: FileProfile) -> Entity:
        """Analyze a single file to determine its primary entity"""
        file_name = file_profile.file_name.lower()
        
        # Determine entity name based on file name and column analysis
        entity_name = self._determine_entity_name(file_name, file_profile.columns)
        
        # Determine entity type (fact vs dimension)
        entity_type = self._determine_entity_type(file_profile.columns)
        
        # Find primary key candidates
        primary_key_candidates = self._find_primary_key_candidates(file_profile.columns)
        
        return Entity(
            name=entity_name,
            source_file=file_profile.file_name,
            file_id=file_profile.file_id,
            columns=file_profile.columns,
            primary_key_candidates=primary_key_candidates,
            entity_type=entity_type
        )
    
    def _determine_entity_name(self, file_name: str, columns: List[ColumnProfile]) -> str:
        """Determine the most likely entity name"""
        # Check file name against known patterns
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                if pattern in file_name:
                    return entity_type.title()
        
        # Check column names for entity indicators
        column_names = [col.name.lower() for col in columns]
        entity_scores = {}
        
        for entity_type, patterns in self.entity_patterns.items():
            score = 0
            for pattern in patterns:
                for col_name in column_names:
                    if pattern in col_name:
                        score += 1
            entity_scores[entity_type] = score
        
        # Return the highest scoring entity type
        if entity_scores:
            best_entity = max(entity_scores, key=entity_scores.get)
            if entity_scores[best_entity] > 0:
                return best_entity.title()
        
        # Default naming based on file name
        base_name = file_name.replace('.csv', '').replace('.xlsx', '').replace('.xls', '')
        # Remove common prefixes/suffixes
        base_name = base_name.replace('data_', '').replace('_data', '')
        base_name = base_name.replace('export_', '').replace('_export', '')
        
        return base_name.replace('_', ' ').title()
    
    def _determine_entity_type(self, columns: List[ColumnProfile]) -> str:
        """Determine if this is a fact table or dimension table"""
        numeric_columns = sum(1 for col in columns if col.data_type in ['integer', 'float'])
        total_columns = len(columns)
        
        # Check for typical fact table indicators
        has_measures = any(col.name.lower() in ['amount', 'quantity', 'count', 'total', 'sum', 'value', 'price', 'cost']
                          for col in columns)
        
        has_dates = any(col.data_type == 'datetime' for col in columns)
        
        # Check for foreign key patterns
        foreign_key_count = sum(1 for col in columns 
                               if any(pattern in col.name.lower() for pattern in self.id_patterns)
                               and col.name.lower() != 'id')
        
        # Heuristics for fact vs dimension
        if (numeric_columns / total_columns > 0.3 and has_measures) or foreign_key_count > 2:
            return 'fact'
        elif has_dates and foreign_key_count > 0:
            return 'fact'
        else:
            return 'dimension'
    
    def _find_primary_key_candidates(self, columns: List[ColumnProfile]) -> List[str]:
        """Find columns that could serve as primary keys"""
        candidates = []
        
        for col in columns:
            col_name_lower = col.name.lower()
            
            # Check for explicit ID patterns
            if any(pattern in col_name_lower for pattern in self.id_patterns):
                candidates.append(col.name)
                continue
            
            # Check for high uniqueness
            if col.total_count > 0:
                uniqueness_ratio = col.distinct_count / col.total_count
                if uniqueness_ratio > 0.95 and col.null_count == 0:
                    candidates.append(col.name)
        
        # Sort by preference (exact 'id' first, then others)
        def sort_key(col_name):
            name_lower = col_name.lower()
            if name_lower == 'id':
                return 0
            elif name_lower.endswith('_id'):
                return 1
            elif 'id' in name_lower:
                return 2
            else:
                return 3
        
        candidates.sort(key=sort_key)
        return candidates
