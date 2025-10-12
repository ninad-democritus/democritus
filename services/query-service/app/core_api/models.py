"""Core API request/response models"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ValidateSQLRequest(BaseModel):
    """Request to validate SQL query"""
    sql: str = Field(..., description="SQL query to validate")


class ValidateSQLResponse(BaseModel):
    """Response from SQL validation"""
    valid: bool
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None


class ExecuteSQLRequest(BaseModel):
    """Request to execute SQL query"""
    sql: str = Field(..., description="SQL query to execute")
    limit: Optional[int] = Field(1000, description="Maximum rows to return")


class ExecuteSQLResponse(BaseModel):
    """Response from SQL execution"""
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    truncated: bool


class BindChartDataRequest(BaseModel):
    """Request to bind data to chart configuration"""
    chart_config: Dict[str, Any] = Field(..., description="Chart configuration template")
    data: Dict[str, Any] = Field(..., description="Query results with columns and rows")
    chart_type: Optional[str] = Field("bar", description="Type of chart")


class BindChartDataResponse(BaseModel):
    """Response with data-bound chart configuration"""
    chart_config: Dict[str, Any]

