"""
Prompt templates for LLM narrative generation
"""


class PromptTemplates:
    """Structured prompt templates for different narrative types"""
    
    @staticmethod
    def entity_description_prompt(context_dict: dict) -> str:
        """Generate entity description prompt"""
        return f"""Generate a business-friendly description for a data entity.

Entity Context:
- Name: {context_dict['canonical_name']}
- Type: {context_dict['entity_type'].capitalize()} Table
- Synonyms: {', '.join(context_dict['synonyms']) if context_dict['synonyms'] else 'None'}
- Primary Key: {context_dict['primary_key'].get('column')} ({context_dict['primary_key'].get('semantic_type', 'identifier')})
- Domain: {context_dict.get('domain', 'Not specified')}
- Row Count: {context_dict['row_count']:,} records

Key Columns ({len(context_dict['columns'])} total):
{chr(10).join(f"- {col['canonical_name']} ({col['semantic_type']}): {col.get('data_type_display', '')} [{', '.join(col['classifications'])}]" for col in context_dict['columns'][:5])}
{'...' if len(context_dict['columns']) > 5 else ''}

Relationships:
{chr(10).join(f"- {rel['direction'].capitalize()}: {rel.get('to_entity') or rel.get('from_entity')} ({rel['cardinality']}, {rel['confidence']:.0%} confidence)" for rel in context_dict['relationships'][:3])}

Classifications:
- Entity: {', '.join(context_dict['classifications']) if context_dict['classifications'] else 'None'}

Generate a 3-4 sentence business description suitable for OpenMetadata:
1. Start with the entity's purpose and role
2. Mention key attributes and identifiers
3. Describe main relationships and dependencies
4. Note any governance or classification context
Use {'confident' if context_dict['confidence'] > 0.85 else 'tentative'} language given the {context_dict['confidence']:.0%} confidence level."""
    
    @staticmethod
    def column_description_prompt(context_dict: dict) -> str:
        """Generate column description prompt"""
        stats_text = ""
        if context_dict.get('statistics'):
            stats = context_dict['statistics']
            if stats.get('min_value') is not None and stats.get('max_value') is not None:
                stats_text = f"\n- Range: {stats['min_value']} to {stats['max_value']}"
                if stats.get('mean_value'):
                    stats_text += f" (average: {stats['mean_value']})"
            if stats.get('distinct_count'):
                stats_text += f"\n- Distinct Values: {stats['distinct_count']:,}"
            if stats.get('null_percentage') is not None:
                stats_text += f"\n- Null Percentage: {stats['null_percentage']:.1f}%"
        
        relationships_text = ""
        if context_dict.get('relationships'):
            relationships_text = "\nRelationship Participation:\n" + "\n".join(
                f"- {rel['relationship']}" for rel in context_dict['relationships'][:2]
            )
        
        return f"""Generate a column description for OpenMetadata.

Column Context:
- Name: {context_dict['name']}
- Display Name: {context_dict['canonical_name']}
- Entity: {context_dict['entity_name']} ({'Primary Key' if context_dict['is_primary_key'] else 'Attribute'})
- FQN: {context_dict['fqn']}

Semantic Context:
- Semantic Type: {context_dict['semantic_type']} ({context_dict['semantic_type_confidence']:.0%} confidence)
- Data Type: {context_dict['data_type_display']}
- Nullable: {'Yes' if context_dict['nullable'] else 'No'}
{stats_text}

Classifications: {', '.join(context_dict['classifications']) if context_dict['classifications'] else 'None'}
{f"Glossary Term: {context_dict['glossary_term']}" if context_dict.get('glossary_term') else ''}
{relationships_text}

Generate a 2-3 sentence business description:
1. Explain the column's business meaning and purpose
2. Include relevant data characteristics (type, range, cardinality)
3. Mention governance classifications if applicable
Keep it concise and focused on business value."""
    
    @staticmethod
    def relationship_description_prompt(context_dict: dict) -> str:
        """Generate relationship description prompt"""
        return f"""Generate a relationship narrative for two entities.

Relationship Context:
- From: {context_dict['from_entity']} ({context_dict['entity_types']['from_entity_type']})
- To: {context_dict['to_entity']} ({context_dict['entity_types']['to_entity_type']})
- Cardinality: {context_dict['cardinality']}
- Via Columns: {context_dict['from_entity']}.{context_dict['from_column']} → {context_dict['to_entity']}.{context_dict['to_column']}

Detection Details:
- Method: {context_dict['detection_method']}
- Confidence: {context_dict['confidence']:.0%}
- Key Factors: {', '.join(f"{k}: {v:.0%}" for k, v in list(context_dict['confidence_factors'].items())[:3])}

Column Semantics:
- {context_dict['from_column']}: {context_dict['column_semantics'].get('from_column_semantic_type')} (nullable: {context_dict['column_semantics'].get('from_column_nullable')})
- {context_dict['to_column']}: {context_dict['column_semantics'].get('to_column_semantic_type')} (unique: {context_dict['column_semantics'].get('to_column_unique')})

Generate a 1-2 sentence relationship description:
1. Describe the business relationship in clear terms
2. Mention how it enables analysis or data operations
Use {'confident' if context_dict['confidence'] > 0.85 else 'qualified'} language based on the confidence level."""
    
    @staticmethod
    def glossary_term_narrative_prompt(term_dict: dict, context_info: dict) -> str:
        """Generate enriched glossary term narrative"""
        return f"""Enrich a glossary term definition with contextual system information.

Original Definition:
{term_dict['definition']}

System Context:
- Associated Entities: {', '.join(context_info.get('associated_entities', []))}
- Associated Columns: {', '.join(context_info.get('associated_columns', [])[:3])}
- Related Terms: {', '.join(context_info.get('related_terms', [])[:3])}
- Classifications: {', '.join(context_info.get('classifications', []))}
- Domain: {context_info.get('domain', 'Not specified')}
- Row Count: {context_info.get('row_count', 'Unknown')} records

Generate a 2-3 sentence contextual narrative that:
1. References how this term is used in the system
2. Mentions key relationships and data volume
3. Notes related business concepts
This will be appended to the original definition, so don't repeat it."""
    
    @staticmethod
    def domain_description_prompt(context_dict: dict) -> str:
        """Generate domain/glossary description prompt"""
        return f"""Generate a business domain summary.

Domain Context:
- Name: {context_dict['display_name']}
- Glossary ID: {context_dict['name']}

Entities ({context_dict['data_characteristics']['total_entities']} total):
{chr(10).join(f"- {e['name']} ({e['type']}): {e['row_count']:,} records" for e in context_dict['entities'][:5])}

Relationships: {context_dict['data_characteristics']['total_relationships']} connections
Glossary Terms: {context_dict['data_characteristics']['total_terms']} terms

Classification Profile:
{chr(10).join(f"- {tag}: {count} occurrences" for tag, count in list(context_dict['classification_profile'].items())[:5])}

Data Volume:
- Total Records: {context_dict['data_characteristics']['total_rows']:,}
- Fact Tables: {context_dict['data_characteristics']['fact_entities']}
- Dimension Tables: {context_dict['data_characteristics']['dimension_entities']}

Generate a 4-5 sentence domain description:
1. Describe the overall business domain and purpose
2. Highlight key entities and their roles (fact vs dimension)
3. Mention data volume and relationship complexity
4. Note governance and classification context
5. Explain what business processes or analytics this domain supports"""

