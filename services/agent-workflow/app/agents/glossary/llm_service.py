"""
LLM service for definition and domain generation
Supports Ollama and OpenAI providers
"""
import json
import logging
import requests
from typing import List, Dict, Any, Optional, Tuple
from .config import GlossaryConfig
from .models import CandidateTerm, TermCluster, DomainCluster

logger = logging.getLogger(__name__)


class LLMService:
    """LLM service for glossary generation"""
    
    def __init__(self, config: GlossaryConfig):
        self.config = config
        self.session = requests.Session()
    
    def generate_term_definitions(self, term_clusters: List[TermCluster]) -> Dict[int, Dict[str, Any]]:
        """
        Generate definitions for term clusters using LLM
        Batches multiple terms per request for efficiency
        
        Args:
            term_clusters: List of TermCluster objects
            
        Returns:
            Dict mapping cluster_id to {definition, business_synonyms, quality_score}
        """
        logger.info(f"Generating definitions for {len(term_clusters)} term clusters")
        
        results = {}
        
        # Process in batches
        for i in range(0, len(term_clusters), self.config.llm_batch_size):
            batch = term_clusters[i:i + self.config.llm_batch_size]
            batch_results = self._generate_definitions_batch(batch)
            results.update(batch_results)
        
        logger.info(f"Generated {len(results)} definitions")
        return results
    
    def generate_domain_names(self, domain_clusters: List[DomainCluster]) -> Dict[int, Dict[str, str]]:
        """
        Generate domain names and descriptions using LLM
        
        Args:
            domain_clusters: List of DomainCluster objects
            
        Returns:
            Dict mapping cluster_id to {domain_name, description}
        """
        logger.info(f"Generating domain names for {len(domain_clusters)} domains")
        
        results = {}
        
        # Process each domain (not batched, as domains are fewer and need more context)
        for domain_cluster in domain_clusters:
            result = self._generate_domain_name(domain_cluster)
            if result:
                results[domain_cluster.cluster_id] = result
        
        logger.info(f"Generated {len(results)} domain names")
        return results
    
    def _generate_definitions_batch(self, term_clusters: List[TermCluster]) -> Dict[int, Dict[str, Any]]:
        """Generate definitions for a batch of term clusters"""
        if not term_clusters:
            return {}
        
        # Build prompt
        prompt = self._build_definition_prompt(term_clusters)
        
        # Call LLM with retries
        for attempt in range(self.config.llm_max_retries):
            try:
                response_text = self._call_llm(prompt)
                
                # Parse response
                batch_results = self._parse_definition_response(response_text, term_clusters)
                
                if batch_results:
                    return batch_results
                else:
                    logger.warning(f"Failed to parse LLM response on attempt {attempt + 1}")
                    
            except Exception as e:
                logger.error(f"LLM call failed on attempt {attempt + 1}: {e}")
                if attempt == self.config.llm_max_retries - 1:
                    # Final attempt failed, use fallback
                    return self._generate_fallback_definitions(term_clusters)
        
        return self._generate_fallback_definitions(term_clusters)
    
    def _generate_domain_name(self, domain_cluster: DomainCluster) -> Optional[Dict[str, str]]:
        """Generate domain name and description for a single domain"""
        prompt = self._build_domain_prompt(domain_cluster)
        
        # Call LLM with retries
        for attempt in range(self.config.llm_max_retries):
            try:
                response_text = self._call_llm(prompt)
                
                # Parse response
                result = self._parse_domain_response(response_text)
                
                if result:
                    return result
                else:
                    logger.warning(f"Failed to parse domain LLM response on attempt {attempt + 1}")
                    
            except Exception as e:
                logger.error(f"Domain LLM call failed on attempt {attempt + 1}: {e}")
                if attempt == self.config.llm_max_retries - 1:
                    # Final attempt failed, use fallback
                    return self._generate_fallback_domain_name(domain_cluster)
        
        return self._generate_fallback_domain_name(domain_cluster)
    
    def _build_definition_prompt(self, term_clusters: List[TermCluster]) -> str:
        """Build prompt for term definition generation"""
        terms_context = []
        
        for cluster in term_clusters:
            rep_term = cluster.representative_term or cluster.members[0]
            
            # Build context for this term
            context = {
                "canonical_name": rep_term.canonical_name,
                "synonyms": list(set(rep_term.synonyms + [m.canonical_name for m in cluster.members])),
                "source_type": rep_term.source_type,
                "entity_type": rep_term.entity_type,
                "classifications": list(set(rep_term.classifications)),
                "sample_values": rep_term.sample_values[:3] if rep_term.sample_values else [],
                "related_entities": list(set(rep_term.related_entities)),
                "is_key_identifier": rep_term.is_primary_key
            }
            
            # Add relationship context
            if rep_term.relationships:
                rel_descriptions = [rel.get('semantic', '') for rel in rep_term.relationships if rel.get('semantic')]
                if rel_descriptions:
                    context["relationships"] = rel_descriptions[:2]
            
            terms_context.append(context)
        
        # Build prompt
        prompt = f"""You are a business glossary expert. Generate clear, concise business definitions for the following data terms.

For each term, provide:
1. A business-friendly definition (2-3 sentences) that non-technical users can understand
2. Additional business synonyms commonly used for this concept
3. A quality score (0.0-1.0) indicating your confidence in the definition

Terms to define:
{json.dumps(terms_context, indent=2)}

Return your response as a JSON array with this structure:
[
  {{
    "canonical_name": "Term Name",
    "definition": "Clear business definition...",
    "business_synonyms": ["Synonym1", "Synonym2"],
    "quality_score": 0.9
  }}
]

Important guidelines:
- Focus on WHAT the term represents in business terms, not technical details
- Explain WHY it matters to the business
- Use simple language that any stakeholder can understand
- For key identifiers, emphasize their role in uniquely identifying records
- For measures/amounts, explain what is being measured
- For transactional data (facts), describe the business event
- For reference data (dimensions), describe the business entity

Return ONLY the JSON array, no additional text."""
        
        return prompt
    
    def _build_domain_prompt(self, domain_cluster: DomainCluster) -> str:
        """Build prompt for domain name generation"""
        # Get representative terms from domain
        term_names = []
        for term_cluster in domain_cluster.term_clusters[:10]:  # Top 10 terms
            rep_term = term_cluster.representative_term or term_cluster.members[0]
            term_names.append(rep_term.canonical_name)
        
        context = {
            "terms": term_names,
            "classifications": domain_cluster.dominant_classifications[:5],
            "entity_types": domain_cluster.entity_types,
            "term_count": sum(len(tc.members) for tc in domain_cluster.term_clusters)
        }
        
        prompt = f"""You are a business glossary expert. Generate a business-friendly domain name and description for a group of related data terms.

Domain context:
{json.dumps(context, indent=2)}

Provide:
1. A concise domain name (2-4 words) that describes this business area
2. A business-friendly description (2-3 sentences) of what this domain covers

Return your response as JSON:
{{
  "domain_name": "Domain Name",
  "description": "Description of the business domain..."
}}

Guidelines:
- Domain name should be professional and business-appropriate
- Use terminology that business users recognize
- Description should explain the scope and purpose of this domain
- Avoid technical jargon
- Make it clear what types of data and processes this domain covers

Return ONLY the JSON object, no additional text."""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM provider (Ollama or OpenAI)"""
        if self.config.llm_provider == "ollama":
            return self._call_ollama(prompt)
        elif self.config.llm_provider == "openai":
            return self._call_openai(prompt)
        else:
            raise ValueError(f"Unknown LLM provider: {self.config.llm_provider}")
    
    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API"""
        url = f"{self.config.llm_base_url}/api/generate"
        
        payload = {
            "model": self.config.llm_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,  # Lower temperature for more consistent output
                "top_p": 0.9
            }
        }
        
        response = self.session.post(
            url,
            json=payload,
            timeout=self.config.llm_timeout
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get('response', '')
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        # Placeholder for OpenAI implementation
        raise NotImplementedError("OpenAI provider not yet implemented")
    
    def _parse_definition_response(self, response_text: str, 
                                   term_clusters: List[TermCluster]) -> Dict[int, Dict[str, Any]]:
        """Parse LLM response for definitions"""
        try:
            # Try to extract JSON from response
            response_text = response_text.strip()
            
            # Handle markdown code blocks
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                # Remove first and last lines (```json and ```)
                response_text = '\n'.join(lines[1:-1])
            
            # Parse JSON
            definitions = json.loads(response_text)
            
            if not isinstance(definitions, list):
                logger.error("LLM response is not a JSON array")
                return {}
            
            # Map definitions back to cluster IDs
            results = {}
            for definition in definitions:
                canonical_name = definition.get('canonical_name', '')
                
                # Find matching cluster
                for cluster in term_clusters:
                    rep_term = cluster.representative_term or cluster.members[0]
                    if rep_term.canonical_name == canonical_name:
                        results[cluster.cluster_id] = {
                            'definition': definition.get('definition', ''),
                            'business_synonyms': definition.get('business_synonyms', []),
                            'quality_score': definition.get('quality_score', 0.8)
                        }
                        break
            
            return results
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error parsing definition response: {e}")
            return {}
    
    def _parse_domain_response(self, response_text: str) -> Optional[Dict[str, str]]:
        """Parse LLM response for domain name"""
        try:
            # Try to extract JSON from response
            response_text = response_text.strip()
            
            # Handle markdown code blocks
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1])
            
            # Parse JSON
            domain_info = json.loads(response_text)
            
            if 'domain_name' in domain_info and 'description' in domain_info:
                return {
                    'domain_name': domain_info['domain_name'],
                    'description': domain_info['description']
                }
            
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse domain JSON response: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing domain response: {e}")
            return None
    
    def _generate_fallback_definitions(self, term_clusters: List[TermCluster]) -> Dict[int, Dict[str, Any]]:
        """Generate template-based definitions when LLM fails"""
        logger.info("Using fallback template-based definitions")
        
        results = {}
        
        for cluster in term_clusters:
            rep_term = cluster.representative_term or cluster.members[0]
            
            # Build template definition
            if rep_term.is_primary_key:
                definition = f"Unique identifier for {rep_term.canonical_name} records."
            elif rep_term.source_type == 'entity':
                definition = f"Business entity representing {rep_term.canonical_name}."
                if rep_term.entity_type == 'fact':
                    definition += " Contains transactional or event data."
                else:
                    definition += " Contains reference or master data."
            else:
                definition = f"Data attribute representing {rep_term.canonical_name}."
            
            # Add classification context
            if rep_term.classifications:
                main_class = rep_term.classifications[0]
                if 'Finance' in main_class:
                    definition += " Used in financial reporting and analysis."
                elif 'PII' in main_class:
                    definition += " Contains personally identifiable information."
            
            results[cluster.cluster_id] = {
                'definition': definition,
                'business_synonyms': rep_term.synonyms[:3],
                'quality_score': 0.5  # Lower quality for templates
            }
        
        return results
    
    def _generate_fallback_domain_name(self, domain_cluster: DomainCluster) -> Dict[str, str]:
        """Generate rule-based domain name when LLM fails"""
        logger.info("Using fallback rule-based domain naming")
        
        # Map classification prefixes to domain names
        classification_map = {
            'Finance': 'Financial Data',
            'PII': 'Customer Information',
            'DataDomain': 'Business Data',
            'DataQuality': 'Data Management',
            'Temporal': 'Time-Based Data',
            'Transactional': 'Transactional Data'
        }
        
        # Get dominant classification
        if domain_cluster.dominant_classifications:
            main_class = domain_cluster.dominant_classifications[0]
            prefix = main_class.split('.')[0] if '.' in main_class else main_class
            
            domain_name = classification_map.get(prefix, 'Business Data')
            description = f"Data classified under {main_class} and related categories."
        else:
            domain_name = 'General Business Data'
            description = 'General business data and information.'
        
        # Add entity type context
        if domain_cluster.entity_types:
            if 'fact' in domain_cluster.entity_types:
                description += ' Includes transactional and operational data.'
            if 'dimension' in domain_cluster.entity_types:
                description += ' Includes reference and master data.'
        
        return {
            'domain_name': domain_name,
            'description': description
        }

