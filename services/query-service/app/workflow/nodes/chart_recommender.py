"""Chart type recommendation node"""
import json
import logging
from typing import Dict, Any

from ...services.ollama_client import get_llm
from ...services.redis_publisher import publish_progress
from ...prompts.chart_recommender import (
    CHART_RECOMMENDER_SYSTEM_PROMPT,
    create_chart_recommendation_prompt
)
from ...utils.chart_rules import recommend_chart_type_by_rules, generate_chart_title
from ...models import ChartRecommendation
from ..state import WorkflowState

logger = logging.getLogger(__name__)


async def recommend_chart(state: WorkflowState) -> Dict[str, Any]:
    """
    Recommend chart type based on data characteristics.
    
    Uses rule-based recommendation by default, with optional LLM fallback.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with chart_recommendation
    """
    query_id = state["query_id"]
    data = state["query_results"]
    intent = state["parsed_intent"]
    constraints = state.get("constraints")
    
    logger.info(f"[{query_id}] Recommending chart type")
    
    try:
        # Publish progress
        await publish_progress(
            query_id=query_id,
            stage="recommending_chart",
            message="Analyzing data and recommending chart type..."
        )
        
        # Check for user constraint
        user_chart_type = None
        if constraints and "chartType" in constraints:
            user_chart_type = constraints["chartType"]
            logger.info(f"[{query_id}] User specified chart type: {user_chart_type}")
        
        # Use rule-based recommendation (fast and reliable)
        rule_recommendation = recommend_chart_type_by_rules(
            data=data,
            intent=intent.dict(),
            user_constraint=user_chart_type
        )
        
        logger.info(
            f"[{query_id}] Rule-based recommendation: {rule_recommendation['chart_type']} "
            f"(confidence={rule_recommendation['confidence']:.2f})"
        )
        
        # If confidence is high or user specified, use rule-based result
        if rule_recommendation["confidence"] >= 0.8 or user_chart_type:
            recommendation = ChartRecommendation(**rule_recommendation)
        else:
            # Low confidence - use LLM for better recommendation
            logger.info(f"[{query_id}] Low confidence, using LLM for recommendation")
            
            try:
                llm = get_llm(model="llama3.1:8b", temperature=0.2, json_mode=True)  # Use smaller model with JSON output
                
                user_prompt = create_chart_recommendation_prompt(
                    data=data,
                    intent=intent.dict(),
                    user_constraint=user_chart_type
                )
                
                messages = [
                    {"role": "system", "content": CHART_RECOMMENDER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]
                
                response = await llm.ainvoke(messages)
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # Parse JSON response
                llm_recommendation = json.loads(response_text)
                recommendation = ChartRecommendation(**llm_recommendation)
                
                logger.info(f"[{query_id}] LLM recommendation: {recommendation.chart_type}")
                
            except Exception as llm_error:
                logger.warning(f"[{query_id}] LLM recommendation failed, using rule-based: {llm_error}")
                recommendation = ChartRecommendation(**rule_recommendation)
        
        # Apply user size constraint if provided
        if constraints and "chartSize" in constraints:
            recommendation.size = constraints["chartSize"]
            logger.info(f"[{query_id}] Applied user size constraint: {recommendation.size}")
        
        return {
            "chart_recommendation": recommendation
        }
        
    except Exception as e:
        logger.exception(f"[{query_id}] Chart recommendation failed")
        
        # Fallback to bar chart
        fallback = ChartRecommendation(
            chart_type="bar",
            confidence=0.5,
            reasoning="Using fallback chart type due to recommendation error",
            size={"cols": 4, "rows": 3}
        )
        
        return {
            "chart_recommendation": fallback
        }

