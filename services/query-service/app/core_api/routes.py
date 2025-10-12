"""Core API routes - stable endpoints for dashboard service"""
import logging
from fastapi import APIRouter, HTTPException

from .models import (
    ValidateSQLRequest, ValidateSQLResponse,
    ExecuteSQLRequest, ExecuteSQLResponse,
    BindChartDataRequest, BindChartDataResponse
)
from .service import validate_sql_with_metadata, execute_sql_query
from .chart_data_binder import bind_data_to_chart

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/core/v1", tags=["Core API"])


@router.post("/validate-sql", response_model=ValidateSQLResponse)
async def validate_sql_endpoint(request: ValidateSQLRequest):
    """
    Validate SQL query against schema.
    Fetches metadata internally - no external metadata needed.
    
    Args:
        request: SQL validation request
        
    Returns:
        Validation result with errors, warnings, and suggestions
    """
    try:
        validation_result = await validate_sql_with_metadata(request.sql)
        
        return ValidateSQLResponse(
            valid=validation_result.is_valid,
            errors=validation_result.errors if validation_result.errors else None,
            warnings=validation_result.warnings if validation_result.warnings else None,
            suggestions=validation_result.suggestions if validation_result.suggestions else None
        )
        
    except Exception as e:
        logger.exception("SQL validation failed")
        raise HTTPException(
            status_code=500,
            detail=f"SQL validation failed: {str(e)}"
        )


@router.post("/execute-sql", response_model=ExecuteSQLResponse)
async def execute_sql_endpoint(request: ExecuteSQLRequest):
    """
    Execute SQL query via Trino and return results.
    
    Args:
        request: SQL execution request with query and optional limit
        
    Returns:
        Query results with columns and rows
    """
    try:
        result = execute_sql_query(request.sql, request.limit)
        
        return ExecuteSQLResponse(
            columns=result["columns"],
            rows=result["rows"],
            row_count=result["row_count"],
            truncated=result["truncated"]
        )
        
    except Exception as e:
        logger.exception("SQL execution failed")
        raise HTTPException(
            status_code=500,
            detail=f"SQL execution failed: {str(e)}"
        )


@router.post("/bind-chart-data", response_model=BindChartDataResponse)
async def bind_chart_data_endpoint(request: BindChartDataRequest):
    """
    Bind query data to chart configuration template.
    Populates data arrays while preserving chart structure.
    
    Args:
        request: Chart config template, data, and chart type
        
    Returns:
        Chart configuration with data bound
    """
    try:
        logger.info(f"=== BIND-CHART-DATA ENDPOINT START ===")
        logger.info(f"Chart type: {request.chart_type}")
        logger.info(f"Request chart_config keys: {list(request.chart_config.keys())}")
        logger.info(f"Data rows: {len(request.data.get('rows', []))}")
        
        bound_config = bind_data_to_chart(
            chart_config=request.chart_config,
            data=request.data.get("rows", []),
            chart_type=request.chart_type
        )
        
        logger.info(f"After bind_data_to_chart: config keys={list(bound_config.keys())}")
        
        if "echartsOptions" in bound_config:
            echarts = bound_config["echartsOptions"]
            logger.info(f"  Bound echartsOptions: has_series={'series' in echarts}, "
                       f"has_legend={'legend' in echarts}, has_color={'color' in echarts}")
            if "series" in echarts and echarts["series"]:
                logger.info(f"    series[0] keys: {list(echarts['series'][0].keys())}")
                logger.info(f"    series[0] has_label={'label' in echarts['series'][0]}")
                if 'label' in echarts['series'][0]:
                    logger.info(f"    series[0].label value: {echarts['series'][0]['label']}")
            if 'legend' in echarts:
                logger.info(f"    legend value: {echarts['legend']}")
        
        response = BindChartDataResponse(chart_config=bound_config)
        logger.info(f"Returning BindChartDataResponse")
        logger.info(f"=== BIND-CHART-DATA ENDPOINT END ===")
        
        return response
        
    except Exception as e:
        logger.exception("Failed to bind chart data")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to bind chart data: {str(e)}"
        )

