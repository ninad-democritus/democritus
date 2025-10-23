"""
Canonical name selection for AlignerAgent (rule-based + optional LLM)
"""
import os
import logging
import json
from typing import List, Tuple, Dict, Any
from .models import EntityCluster, ColumnCluster
from .config import AlignerConfig

try:
    from langchain_community.chat_models import ChatOllama
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

logger = logging.getLogger(__name__)


class CanonicalNamingService:
    """Select canonical names from clusters using rules and optional LLM"""
    
    def __init__(self, config: AlignerConfig):
        """
        Initialize canonical naming service
        
        Args:
            config: AlignerConfig instance
        """
        self.config = config
        self.llm = None
        
        if config.use_llm and LLM_AVAILABLE:
            try:
                self.llm = self._init_llm()
                logger.info("LLM initialized for canonical naming")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM: {e}")
                self.llm = None
        else:
            logger.info("LLM disabled or not available for canonical naming")
    
    def _init_llm(self):
        """Initialize Ollama LLM"""
        ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            base_url=ollama_host,
            temperature=0.1,
            num_predict=500
        )
    
    def select_canonical_names(self, 
                              clusters: List,
                              cluster_type: str) -> Dict[int, Dict[str, Any]]:
        """
        Select canonical names for all clusters
        
        Args:
            clusters: List of cluster objects (EntityCluster or ColumnCluster)
            cluster_type: 'entity' or 'column'
            
        Returns:
            Dictionary mapping cluster_id -> {canonical_name, synonyms}
        """
        results = {}
        
        # Separate clusters into LLM and rule-based
        llm_clusters = []
        rule_clusters = []
        
        for cluster in clusters:
            if self._should_use_llm(cluster):
                llm_clusters.append(cluster)
            else:
                rule_clusters.append(cluster)
        
        logger.info(f"Processing {len(rule_clusters)} clusters with rules, {len(llm_clusters)} with LLM")
        
        # Process rule-based clusters
        for cluster in rule_clusters:
            canonical, synonyms = self._select_rule_based(cluster)
            results[cluster.cluster_id] = {
                'canonical_name': canonical,
                'synonyms': synonyms
            }
        
        # Process LLM clusters in batches
        if llm_clusters and self.llm:
            llm_results = self._refine_with_llm_batched(llm_clusters, cluster_type)
            results.update(llm_results)
        elif llm_clusters:
            # Fallback to rules if LLM not available
            logger.warning(f"LLM not available, falling back to rules for {len(llm_clusters)} clusters")
            for cluster in llm_clusters:
                canonical, synonyms = self._select_rule_based(cluster)
                results[cluster.cluster_id] = {
                    'canonical_name': canonical,
                    'synonyms': synonyms
                }
        
        return results
    
    def _should_use_llm(self, cluster) -> bool:
        """Determine if cluster needs LLM refinement"""
        if not self.config.use_llm or not self.llm:
            return False
        
        # Use LLM if cluster has multiple members and high variance
        return (len(cluster.members) > 1 and 
                cluster.variance > self.config.llm_variance_threshold)
    
    def _select_rule_based(self, cluster) -> Tuple[str, List[str]]:
        """
        Select canonical name using rule-based heuristics
        
        Returns:
            Tuple of (canonical_name, synonyms)
        """
        members = [m['normalized'] for m in cluster.members]
        raw_names = [m['raw_name'] for m in cluster.members]
        
        # Score each name
        scored_names = []
        for name in members:
            score = 0
            
            # +2 if contains spaces (more readable)
            if ' ' in name:
                score += 2
            
            # +1 if length > median
            median_len = sorted([len(n) for n in members])[len(members) // 2]
            if len(name) > median_len:
                score += 1
            
            # +1 if not all lowercase with underscores
            if not (name.islower() and '_' in name):
                score += 1
            
            scored_names.append((score, name))
        
        # Pick highest scoring
        scored_names.sort(reverse=True, key=lambda x: x[0])
        canonical = scored_names[0][1]
        
        # Transform: title case
        canonical = canonical.title()
        
        # Synonyms: other unique normalized names
        synonyms = list(set([n for n in members if n != scored_names[0][1]]))[:3]
        
        logger.debug(f"Rule-based selection: '{canonical}' from {members}")
        return canonical, synonyms
    
    def _refine_with_llm_batched(self, 
                                clusters: List,
                                cluster_type: str) -> Dict[int, Dict[str, Any]]:
        """
        Refine clusters using LLM in batches
        
        Args:
            clusters: List of clusters to refine
            cluster_type: 'entity' or 'column'
            
        Returns:
            Dictionary mapping cluster_id -> {canonical_name, synonyms}
        """
        results = {}
        
        # Process in batches
        for i in range(0, len(clusters), self.config.llm_batch_size):
            batch = clusters[i:i + self.config.llm_batch_size]
            
            try:
                batch_results = self._call_llm_batch(batch, cluster_type)
                results.update(batch_results)
            except Exception as e:
                logger.error(f"LLM batch failed: {e}, falling back to rules")
                # Fallback to rule-based for this batch
                for cluster in batch:
                    canonical, synonyms = self._select_rule_based(cluster)
                    results[cluster.cluster_id] = {
                        'canonical_name': canonical,
                        'synonyms': synonyms
                    }
        
        return results
    
    def _call_llm_batch(self, 
                       clusters: List,
                       cluster_type: str) -> Dict[int, Dict[str, Any]]:
        """Call LLM for a batch of clusters"""
        
        # Create prompt
        cluster_info = []
        cluster_id_map = {}
        for idx, cluster in enumerate(clusters):
            members = [m['normalized'] for m in cluster.members]
            cluster_info.append(f"{idx + 1}: {members}")
            cluster_id_map[idx + 1] = cluster.cluster_id
        
        cluster_list = "\n    ".join(cluster_info)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are a data catalog assistant. For each cluster of {cluster_type} names, suggest:
- canonical_name: A short, human-readable name
- synonyms: List of 2-3 alternate readable names

Return ONLY a JSON object mapping cluster numbers to results. Example format:
{{
  "1": {{"canonical_name": "Customer ID", "synonyms": ["customer id", "client id"]}},
  "2": {{"canonical_name": "Order Date", "synonyms": ["order date", "purchase date"]}}
}}
"""),
            ("human", f"Clusters to process:\n    {cluster_list}")
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        
        # Invoke with retry
        response = self._call_with_retry(chain, max_retries=3)
        
        # Parse response
        return self._parse_llm_response(response, cluster_id_map)
    
    def _call_with_retry(self, chain, max_retries: int = 3):
        """Call LLM with exponential backoff"""
        import time
        
        for attempt in range(max_retries):
            try:
                return chain.invoke({})
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"LLM call failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise
    
    def _parse_llm_response(self, 
                           response: str,
                           cluster_id_map: Dict[int, int]) -> Dict[int, Dict[str, Any]]:
        """Parse LLM JSON response"""
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)
                
                # Map back to actual cluster IDs
                results = {}
                for llm_id_str, data in parsed.items():
                    llm_id = int(llm_id_str)
                    if llm_id in cluster_id_map:
                        actual_id = cluster_id_map[llm_id]
                        results[actual_id] = data
                
                logger.info(f"Successfully parsed LLM response for {len(results)} clusters")
                return results
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Response was: {response}")
            return {}

