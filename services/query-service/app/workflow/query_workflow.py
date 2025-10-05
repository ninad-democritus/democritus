"""LangGraph workflow for query processing"""
import logging
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END

from .state import WorkflowState
from .nodes import (
    nl_parser, 
    metadata_fetcher, 
    sql_generator, 
    sql_validator, 
    sql_executor, 
    chart_recommender, 
    echarts_generator,
    intent_refiner
)

logger = logging.getLogger(__name__)


def route_after_validation(state: WorkflowState) -> Literal["execute", "refine_intent", "error"]:
    """
    Routing logic after SQL validation.
    
    Strategy:
    1. If valid → execute
    2. If invalid and retry_count < max_retries → refine_intent (always)
    3. If invalid and retry_count >= max_retries → error
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node to execute
    """
    validation = state.get("validation_result")
    
    if not validation:
        logger.error("No validation result in state")
        return "error"
    
    if validation.is_valid:
        logger.info("SQL validation passed, proceeding to execution")
        return "execute"
    
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    
    logger.info(f"Validation failed. Attempt: {retry_count + 1}/{max_retries + 1}")
    logger.info(f"Validation errors: {validation.errors}")
    
    # Check if we've exceeded maximum attempts
    if retry_count >= max_retries:
        logger.warning(f"Max attempts ({max_retries + 1}) exceeded")
        state["error"] = f"SQL validation failed after {max_retries + 1} attempts: {validation.errors}"
        state["error_code"] = "SQL_VALIDATION_FAILED"
        return "error"
    
    # Note: retry_count is incremented in the intent_refiner node, not here
    # This ensures the state update persists correctly in LangGraph
    
    # Always refine intent on validation failure
    logger.info(f"Attempt {retry_count + 1} failed, refining intent and retrying...")
    return "refine_intent"


def check_for_errors(state: WorkflowState) -> Literal["continue", "error"]:
    """
    Check if any node has set an error in state.
    
    Args:
        state: Current workflow state
        
    Returns:
        "error" if error exists, "continue" otherwise
    """
    if state.get("error"):
        return "error"
    return "continue"


def create_query_workflow() -> StateGraph:
    """
    Create and compile the LangGraph workflow for query processing.
    
    The workflow:
    1. Parse natural language → extract intent (once)
    2. Fetch metadata → get table schemas (once)
    3. Generate SQL → convert intent to SQL
    4. Validate SQL → check against schema
    5. (Conditional) If invalid → refine intent → generate SQL (max 3 attempts)
    6. Execute SQL → run query via Trino
    7. Recommend chart → suggest chart type
    8. Generate ECharts config → create visualization
    
    Returns:
        Compiled workflow graph
    """
    # Create graph
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("parse_nl", nl_parser.parse_natural_language)
    workflow.add_node("fetch_metadata", metadata_fetcher.fetch_metadata)
    workflow.add_node("generate_sql", sql_generator.generate_sql)
    workflow.add_node("validate_sql", sql_validator.validate_sql)
    workflow.add_node("refine_intent", intent_refiner.refine_intent)  # NEW: Intent refinement
    workflow.add_node("execute_sql", sql_executor.execute_sql)
    workflow.add_node("recommend_chart", chart_recommender.recommend_chart)
    workflow.add_node("generate_echarts", echarts_generator.generate_echarts_config)
    
    # Set entry point
    workflow.set_entry_point("parse_nl")
    
    # Linear flow with error checks
    workflow.add_conditional_edges(
        "parse_nl",
        check_for_errors,
        {
            "continue": "fetch_metadata",
            "error": END
        }
    )
    
    workflow.add_conditional_edges(
        "fetch_metadata",
        check_for_errors,
        {
            "continue": "generate_sql",
            "error": END
        }
    )
    
    workflow.add_conditional_edges(
        "generate_sql",
        check_for_errors,
        {
            "continue": "validate_sql",
            "error": END
        }
    )
    
    # Conditional validation routing: always refine on failure
    workflow.add_conditional_edges(
        "validate_sql",
        route_after_validation,
        {
            "execute": "execute_sql",
            "refine_intent": "refine_intent",    # Always refine intent on validation failure
            "error": END                          # Max attempts exceeded
        }
    )
    
    # After intent refinement, go back to SQL generation with refined intent
    workflow.add_conditional_edges(
        "refine_intent",
        check_for_errors,
        {
            "continue": "generate_sql",
            "error": END
        }
    )
    
    workflow.add_conditional_edges(
        "execute_sql",
        check_for_errors,
        {
            "continue": "recommend_chart",
            "error": END
        }
    )
    
    workflow.add_conditional_edges(
        "recommend_chart",
        check_for_errors,
        {
            "continue": "generate_echarts",
            "error": END
        }
    )
    
    workflow.add_edge("generate_echarts", END)
    
    # Compile workflow
    compiled = workflow.compile()
    
    logger.info("Query workflow compiled successfully")
    
    return compiled


# Global workflow instance (created once)
_workflow = None


def get_workflow() -> StateGraph:
    """Get global workflow instance"""
    global _workflow
    if _workflow is None:
        _workflow = create_query_workflow()
    return _workflow

