"""Adapter for Query Service Core API"""
import logging
from typing import Dict, Any
import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class QueryServiceAdapter:
    """Client for Query Service Core API"""
    
    def __init__(self):
        self.base_url = settings.QUERY_SERVICE_URL
        self.timeout = httpx.Timeout(30.0)
    
    async def validate_sql(self, sql: str) -> Dict[str, Any]:
        """
        Validate SQL query.
        
        Args:
            sql: SQL query
            
        Returns:
            Validation result
        """
        logger.info(f"Calling Query Service validate-sql endpoint")
        logger.debug(f"SQL to validate: {sql[:200]}...")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/core/v1/validate-sql",
                json={"sql": sql}
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"SQL validation result: valid={result.get('valid')}")
            if not result.get('valid'):
                logger.warning(f"SQL validation errors: {result.get('errors')}")
            
            return result
    
    async def execute_sql(self, sql: str, limit: int = 1000) -> Dict[str, Any]:
        """
        Execute SQL query.
        
        Args:
            sql: SQL query
            limit: Row limit
            
        Returns:
            Query results
        """
        logger.info(f"Calling Query Service execute-sql endpoint (limit={limit})")
        logger.debug(f"SQL to execute: {sql[:200]}...")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/core/v1/execute-sql",
                json={"sql": sql, "limit": limit}
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"SQL execution result: {result.get('row_count', 0)} rows, truncated={result.get('truncated', False)}")
            
            return result
    
    async def bind_chart_data(
        self,
        chart_config: Dict[str, Any],
        data: Dict[str, Any],
        chart_type: str
    ) -> Dict[str, Any]:
        """
        Bind data to chart configuration.
        
        Args:
            chart_config: Chart template
            data: Query results
            chart_type: Chart type
            
        Returns:
            Bound chart config
        """
        logger.info(f"=== QUERY ADAPTER: bind_chart_data START ===")
        logger.info(f"Chart type: {chart_type}")
        logger.info(f"Data rows to bind: {data.get('row_count', len(data.get('rows', [])))}")
        logger.info(f"Input chart_config keys: {list(chart_config.keys())}")
        
        if "echartsOptions" in chart_config:
            echarts = chart_config["echartsOptions"]
            logger.info(f"  Input echartsOptions: has_series={'series' in echarts}, "
                       f"has_legend={'legend' in echarts}, has_color={'color' in echarts}")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/core/v1/bind-chart-data",
                json={
                    "chart_config": chart_config,
                    "data": data,
                    "chart_type": chart_type
                }
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Response from bind-chart-data API: keys={list(result.keys())}")
            
            if "chart_config" in result:
                returned_config = result["chart_config"]
                logger.info(f"  Returned chart_config keys: {list(returned_config.keys())}")
                
                if "echartsOptions" in returned_config:
                    echarts = returned_config["echartsOptions"]
                    logger.info(f"  Returned echartsOptions: has_series={'series' in echarts}, "
                               f"has_legend={'legend' in echarts}, has_color={'color' in echarts}")
                    if "series" in echarts and echarts["series"]:
                        logger.info(f"    series[0] keys: {list(echarts['series'][0].keys())}")
                        logger.info(f"    series[0] has_label={'label' in echarts['series'][0]}")
            
            logger.info(f"=== QUERY ADAPTER: bind_chart_data END ===")
            
            return result


# Singleton instance
_adapter = None


def get_query_adapter() -> QueryServiceAdapter:
    """Get global query adapter instance"""
    global _adapter
    if _adapter is None:
        _adapter = QueryServiceAdapter()
    return _adapter

