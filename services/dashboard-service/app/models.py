"""Pydantic models for API requests/responses"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


# Request Models
class WidgetCreate(BaseModel):
    """Widget data for creation"""
    grid_x: int
    grid_y: int
    grid_cols: int
    grid_rows: int
    chart_config: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    nl_query: Optional[str] = None


class DashboardCreate(BaseModel):
    """Dashboard creation request"""
    name: str = Field(..., min_length=3, max_length=255)
    owner_id: str = Field(..., description="User ID (temporary)")
    visibility: str = Field(..., pattern="^(private|public)$")
    dashboard_type: str = Field(..., pattern="^(static|dynamic)$")
    gridster_config: Optional[Dict[str, Any]] = None
    widgets: List[WidgetCreate]


class DashboardUpdate(BaseModel):
    """Dashboard update request"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    visibility: Optional[str] = Field(None, pattern="^(private|public)$")
    widgets: Optional[List[WidgetCreate]] = None


# Response Models
class WidgetResponse(BaseModel):
    """Widget response"""
    id: UUID
    dashboard_id: UUID
    grid_x: int
    grid_y: int
    grid_cols: int
    grid_rows: int
    chart_config: Dict[str, Any]
    widget_metadata: Optional[Dict[str, Any]] = Field(None, serialization_alias="metadata")
    nl_query: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class DashboardResponse(BaseModel):
    """Dashboard response"""
    id: UUID
    name: str
    owner_id: str
    visibility: str
    dashboard_type: str
    gridster_config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    widgets: List[WidgetResponse]
    
    class Config:
        from_attributes = True


class DashboardListItem(BaseModel):
    """Dashboard list item (without widgets)"""
    id: UUID
    name: str
    visibility: str
    dashboard_type: str
    widget_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WidgetPreview(BaseModel):
    """Lightweight widget preview for dashboard cards"""
    id: UUID
    name: str
    chart_type: str
    position: Dict[str, int]
    size: Dict[str, int]


class DashboardViewItem(BaseModel):
    """Dashboard list item with widget preview"""
    id: UUID
    name: str
    owner_id: str
    visibility: str
    dashboard_type: str
    created_at: datetime
    updated_at: datetime
    widget_count: int
    widgets_preview: List[WidgetPreview]


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
    timestamp: str
    dependencies: Dict[str, str]

