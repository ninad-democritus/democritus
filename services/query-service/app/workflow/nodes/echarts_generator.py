"""ECharts configuration generation node"""
import json
import logging
from typing import Dict, Any, List

from ...services.ollama_client import get_llm
from ...services.redis_publisher import publish_progress
from ...prompts.echarts_generator import (
    create_echarts_prompt,
    validate_and_fix_echarts_config,
    limit_data
)
from ..state import WorkflowState

logger = logging.getLogger(__name__)


async def generate_chart_title_llm(
    query_id: str,
    nl_query: str,
    intent: dict,
    chart_type: str,
    data_sample: List[Dict[str, Any]]
) -> str:
    """
    Generate chart title using simple rules (no LLM call for speed).
    
    Args:
        query_id: Query ID for logging
        nl_query: Original natural language query
        intent: Parsed intent with metrics, dimensions, filters
        chart_type: Type of chart being created
        data_sample: Sample of query results
        
    Returns:
        Chart title string
    """
    try:
        metrics = intent.get("metrics", [])
        dimensions = intent.get("dimensions", [])
        filters = intent.get("filters") or {}
        
        # Simple rule-based title generation (much faster than LLM)
        title_parts = []
        
        # Add metrics
        if metrics:
            metric_str = ", ".join([m.replace("_", " ").title() for m in metrics])
            title_parts.append(metric_str)
        
        # Add dimensions
        if dimensions:
            dimension_str = ", ".join([d.replace("_", " ").title() for d in dimensions])
            if title_parts:
                title_parts.append(f"by {dimension_str}")
            else:
                title_parts.append(dimension_str)
        
        # Add key filter if exists
        if filters:
            # Only include first filter to keep title short
            first_filter = list(filters.items())[0] if filters else None
            if first_filter and first_filter[1]:
                filter_key, filter_val = first_filter
                # Keep filter info short
                if isinstance(filter_val, str) and len(str(filter_val)) < 20:
                    title_parts.append(f"({filter_val})")
        
        # Combine parts
        if title_parts:
            title = " ".join(title_parts)
        else:
            # Fallback to nl_query (truncated)
            title = nl_query[:50] if len(nl_query) > 50 else nl_query
            title = title.strip().title()
        
        # Ensure title is not too long
        if len(title) > 60:
            title = title[:57] + "..."
        
        logger.info(f"[{query_id}] Generated chart title (rule-based): {title}")
        return title
        
    except Exception as e:
        logger.warning(f"[{query_id}] Failed to generate title, using fallback: {e}")
        return f"{chart_type.title()} Chart"


async def generate_echarts_config(state: WorkflowState) -> Dict[str, Any]:
    """
    Generate ECharts configuration JSON.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with echarts_config and final_result
    """
    query_id = state["query_id"]
    data = state["query_results"]
    intent = state["parsed_intent"]
    recommendation = state["chart_recommendation"]
    sql = state["generated_sql"]
    nl_query = state["natural_language_query"]
    
    logger.info(f"[{query_id}] Generating ECharts configuration")
    
    try:
        # Publish progress
        await publish_progress(
            query_id=query_id,
            stage="generating_chart_config",
            message="Generating chart configuration..."
        )
        
        # Limit data first (before both prompt and validation)
        limited_data = limit_data(data, recommendation.chart_type)
        logger.info(f"[{query_id}] Using {len(limited_data)} rows for chart (from {len(data)} total)")
        
        # Generate title using LLM for better quality
        title = await generate_chart_title_llm(
            query_id=query_id,
            nl_query=nl_query,
            intent=intent.dict(),
            chart_type=recommendation.chart_type,
            data_sample=limited_data[:3] if limited_data else []
        )
        
        # Get LLM with JSON mode for ECharts config
        llm = get_llm(model=None, temperature=0.2, json_mode=True)
        
        # Create chart-specific prompts (pass already-limited data)
        system_prompt, user_prompt = create_echarts_prompt(
            chart_type=recommendation.chart_type,
            data=limited_data,
            title=title,
            size=recommendation.size,
            intent=intent.dict()
        )
        
        logger.info(f"[{query_id}] Using {recommendation.chart_type}-specific prompts")
        
        # Invoke LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await llm.ainvoke(messages)
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        logger.debug(f"[{query_id}] ECharts response: {response_text[:200]}...")
        
        # Parse JSON response
        try:
            echarts_config = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0].strip()
                echarts_config = json.loads(json_text)
            elif "```" in response_text:
                json_text = response_text.split("```")[1].split("```")[0].strip()
                echarts_config = json.loads(json_text)
            else:
                raise
        
        logger.info(f"[{query_id}] Successfully generated ECharts config from LLM")
        
        # Validate and fix the config (use limited_data for consistency)
        is_valid, fixed_config, validation_warnings = validate_and_fix_echarts_config(
            config=echarts_config,
            data=limited_data,
            chart_type=recommendation.chart_type
        )
        
        if validation_warnings:
            logger.warning(f"[{query_id}] ECharts config had {len(validation_warnings)} issues that were auto-fixed")
            for warning in validation_warnings:
                logger.warning(f"[{query_id}]   - {warning}")
        
        if not is_valid:
            raise ValueError("Failed to generate valid ECharts config even after attempting fixes")
        
        # Use the fixed config
        echarts_config = fixed_config
        
        logger.info(f"[{query_id}] ECharts config validation passed")
        logger.info(f"[{query_id}] Series count: {len(echarts_config['series'])}")
        
        # DEBUG: Log complete echarts config to diagnose color issue
        logger.info(f"[{query_id}] FULL ECHARTS CONFIG: {json.dumps(echarts_config, indent=2)}")
        
        # Log series details
        for i, series in enumerate(echarts_config["series"]):
            if isinstance(series, dict):
                series_type = series.get("type", "unknown")
                series_name = series.get("name", f"Series {i}")
                data_count = len(series.get("data", []))
                has_item_style = "itemStyle" in series
                item_color = series.get("itemStyle", {}).get("color", "none") if has_item_style else "none"
                logger.info(f"[{query_id}]   Series {i}: {series_name} ({series_type}) with {data_count} data points, itemStyle.color={item_color}")
        
        # Infer data schema from limited data
        from decimal import Decimal
        
        data_schema = {}
        if limited_data and len(limited_data) > 0 and limited_data[0] is not None and isinstance(limited_data[0], dict):
            for col, val in limited_data[0].items():
                # Handle Decimal from database queries
                if isinstance(val, (int, float, Decimal)):
                    data_schema[col] = "number"
                elif isinstance(val, str):
                    data_schema[col] = "string"
                else:
                    data_schema[col] = "unknown"
        
        # Build final result (use limited_data for chart, include metadata about limiting)
        final_result = {
            "success": True,
            "data": limited_data,  # Use limited data for chart rendering
            "chartConfig": {
                "type": recommendation.chart_type,
                "title": title,
                "echartsOptions": echarts_config,
                "size": recommendation.size
            },
            "metadata": {
                "sqlQuery": sql,
                "dataSchema": data_schema,
                "recommendedChartType": recommendation.chart_type,
                "confidence": recommendation.confidence,
                "totalRows": len(data),
                "displayedRows": len(limited_data),
                "dataLimited": len(limited_data) < len(data)
            },
            "naturalLanguageQuery": nl_query
        }
        
        # Debug: Log xAxis data being sent to frontend
        if "xAxis" in echarts_config and "data" in echarts_config["xAxis"]:
            xaxis_data = echarts_config["xAxis"]["data"]
            logger.info(f"[{query_id}] xAxis data being sent to frontend: {len(xaxis_data)} categories")
            logger.info(f"[{query_id}] First 5 xAxis labels: {xaxis_data[:5]}")
            logger.info(f"[{query_id}] Last 3 xAxis labels: {xaxis_data[-3:]}")
        
        # Publish completion
        await publish_progress(
            query_id=query_id,
            stage="completed",
            message="Query completed successfully!",
            message_type="COMPLETED",
            extra_data={"result": final_result}
        )
        
        return {
            "echarts_config": echarts_config,
            "final_result": final_result
        }
        
    except Exception as e:
        logger.exception(f"[{query_id}] ECharts generation failed")
        return {
            "error": f"Failed to generate chart configuration: {str(e)}",
            "error_code": "ECHARTS_GENERATION_ERROR"
        }

