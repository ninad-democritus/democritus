"""Pydantic models for API requests and responses"""
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# Request Models
# ============================================================================

class ChartConstraints(BaseModel):
    """Optional constraints from frontend"""
    chartType: Optional[str] = Field(
        None,
        description="Chart type: 'bar', 'line', 'pie', 'area', 'scatter', 'table', 'kpi', 'heatmap'"
    )
    chartSize: Optional[Dict[str, int]] = Field(
        None,
        description="Grid size with 'cols' and 'rows'"
    )
    position: Optional[Dict[str, int]] = Field(
        None,
        description="Grid position with 'x' and 'y'"
    )


class ExistingChart(BaseModel):
    """Existing chart in dashboard for context"""
    type: str
    title: str
    query: str


class ChartContext(BaseModel):
    """Dashboard context for better AI understanding"""
    dashboardId: Optional[str] = None
    existingCharts: Optional[List[ExistingChart]] = None


class ChartGenerationRequest(BaseModel):
    """Request to generate a chart from natural language"""
    naturalLanguageQuery: str = Field(
        ...,
        description="User's natural language query"
    )
    constraints: Optional[ChartConstraints] = None
    context: Optional[ChartContext] = None


# ============================================================================
# Response Models
# ============================================================================

class ChartGenerationInitiated(BaseModel):
    """Immediate response when query is initiated"""
    queryId: str = Field(..., description="UUID for tracking this query")
    websocketUrl: str = Field(..., description="WebSocket endpoint path")
    status: Literal["initiated"] = "initiated"


class ChartSize(BaseModel):
    """Chart size in grid units"""
    cols: int
    rows: int


class ChartConfig(BaseModel):
    """Chart configuration"""
    type: str
    title: str
    echartsOptions: Dict[str, Any]
    size: Optional[ChartSize] = None


class ChartMetadata(BaseModel):
    """Metadata about query execution"""
    sqlQuery: str
    dataSchema: Dict[str, str]
    recommendedChartType: Optional[str] = None
    confidence: float


class ChartGenerationResult(BaseModel):
    """Final result with data and chart config"""
    success: bool = True
    data: List[Dict[str, Any]]
    chartConfig: ChartConfig
    metadata: ChartMetadata
    naturalLanguageQuery: str


class ChartGenerationError(BaseModel):
    """Error response"""
    success: bool = False
    error: str
    errorCode: str
    details: Optional[Dict[str, Any]] = None


# ============================================================================
# WebSocket Message Models
# ============================================================================

class WSConnectedMessage(BaseModel):
    """WebSocket connection confirmation"""
    type: Literal["CONNECTED"] = "CONNECTED"
    queryId: str
    message: str
    timestamp: str


class WSProgressMessage(BaseModel):
    """WebSocket progress update"""
    type: Literal["PROGRESS"] = "PROGRESS"
    queryId: str
    stage: str
    message: str
    timestamp: str


class WSSQLGeneratedMessage(BaseModel):
    """WebSocket SQL generated message"""
    type: Literal["SQL_GENERATED"] = "SQL_GENERATED"
    queryId: str
    sqlQuery: str
    timestamp: str


class WSCompletedMessage(BaseModel):
    """WebSocket completion message"""
    type: Literal["COMPLETED"] = "COMPLETED"
    queryId: str
    result: ChartGenerationResult
    timestamp: str


class WSErrorMessage(BaseModel):
    """WebSocket error message"""
    type: Literal["ERROR"] = "ERROR"
    queryId: str
    error: ChartGenerationError
    timestamp: str


# ============================================================================
# Workflow Models (Internal)
# ============================================================================

class QueryIntent(BaseModel):
    """Parsed intent from natural language"""
    metrics: List[str] = Field(default_factory=list, description="Metrics to query, e.g., ['sales', 'revenue']")
    dimensions: List[str] = Field(default_factory=list, description="Dimensions to group by, e.g., ['region', 'product']")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Filters to apply, e.g., {'quarter': 'Q4'}")
    aggregations: Optional[Dict[str, str]] = Field(default=None, description="Aggregation functions, e.g., {'sales': 'SUM'}")
    time_dimension: Optional[str] = None
    chart_hint: Optional[str] = None


class TableColumn(BaseModel):
    """Column metadata"""
    name: str
    type: str
    description: Optional[str] = None


class TableMetadata(BaseModel):
    """Schema metadata from OpenMetadata"""
    table_name: str
    schema_name: str
    columns: List[TableColumn]
    relationships: List[Dict[str, Any]] = Field(default_factory=list)


class SQLValidationResult(BaseModel):
    """SQL validation result"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class ChartRecommendation(BaseModel):
    """Chart type recommendation"""
    chart_type: str
    confidence: float
    reasoning: str
    size: Dict[str, int]


# ============================================================================
# Health Check Models
# ============================================================================

class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
    timestamp: str
    dependencies: Dict[str, str] = Field(
        default_factory=dict,
        description="Status of dependencies (redis, trino, ollama, openmetadata)"
    )

