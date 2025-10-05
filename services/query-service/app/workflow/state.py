"""Workflow state definition for LangGraph"""
from typing import TypedDict, Optional, List, Dict, Any
from ..models import (
    QueryIntent,
    TableMetadata,
    SQLValidationResult,
    ChartRecommendation
)


class WorkflowState(TypedDict, total=False):
    """
    State definition for LangGraph workflow.
    
    LangGraph automatically manages state transitions between nodes.
    Each node receives the current state and returns updated state.
    """
    
    # ========================================================================
    # Input (Set at workflow start)
    # ========================================================================
    query_id: str
    natural_language_query: str
    constraints: Optional[Dict[str, Any]]
    context: Optional[Dict[str, Any]]
    
    # ========================================================================
    # Intermediate Results (Updated by nodes)
    # ========================================================================
    parsed_intent: Optional[QueryIntent]
    metadata: Optional[List[TableMetadata]]
    generated_sql: Optional[str]
    validation_result: Optional[SQLValidationResult]
    query_results: Optional[List[Dict[str, Any]]]
    chart_recommendation: Optional[ChartRecommendation]
    echarts_config: Optional[Dict[str, Any]]
    
    # ========================================================================
    # Control Flow
    # ========================================================================
    retry_count: int
    max_retries: int
    intent_refinement_count: int
    max_intent_refinements: int
    original_parsed_intent: Optional[QueryIntent]  # Preserve original for context
    error: Optional[str]
    error_code: Optional[str]
    
    # ========================================================================
    # Output (Final result)
    # ========================================================================
    final_result: Optional[Dict[str, Any]]


def create_initial_state(
    query_id: str,
    natural_language_query: str,
    constraints: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
    max_intent_refinements: int = 3
) -> WorkflowState:
    """
    Create initial workflow state.
    
    Args:
        query_id: Unique identifier for this query
        natural_language_query: User's natural language query
        constraints: Optional UI constraints (chart type, size, position)
        context: Optional dashboard context (existing charts, etc.)
        max_retries: Maximum number of retry attempts (3 total attempts)
        max_intent_refinements: Same as max_retries (always refine on failure)
        
    Returns:
        Initial workflow state
    """
    return WorkflowState(
        # Input
        query_id=query_id,
        natural_language_query=natural_language_query,
        constraints=constraints,
        context=context,
        
        # Intermediate (initialized to None)
        parsed_intent=None,
        metadata=None,
        generated_sql=None,
        validation_result=None,
        query_results=None,
        chart_recommendation=None,
        echarts_config=None,
        
        # Control flow
        retry_count=0,
        max_retries=max_retries,
        intent_refinement_count=0,
        max_intent_refinements=max_intent_refinements,
        original_parsed_intent=None,
        error=None,
        error_code=None,
        
        # Output
        final_result=None
    )

