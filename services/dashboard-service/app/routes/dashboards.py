"""Dashboard API routes"""
import logging
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models import (
    DashboardCreate,
    DashboardUpdate,
    DashboardResponse,
    DashboardListItem,
    DashboardViewItem
)
from ..services import dashboard_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboards", tags=["Dashboards"])


@router.post("", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    dashboard_data: DashboardCreate,
    db: Session = Depends(get_db)
):
    """Create new dashboard"""
    try:
        dashboard = await dashboard_service.create_dashboard(db, dashboard_data)
        return dashboard
    except Exception as e:
        logger.exception("Failed to create dashboard")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create dashboard: {str(e)}"
        )


@router.get("/view", response_model=List[DashboardViewItem])
async def view_dashboards(
    owner_id: str,
    scope: str = "all",
    search: str = "",
    db: Session = Depends(get_db)
):
    """List dashboards with widget preview (optimized for view page)"""
    try:
        dashboards = dashboard_service.view_dashboards(
            db=db,
            scope=scope,
            search=search,
            user_id=owner_id
        )
        return dashboards
    except Exception as e:
        logger.exception("Failed to list dashboards for view")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list dashboards: {str(e)}"
        )


@router.get("", response_model=List[DashboardListItem])
async def list_dashboards(
    owner_id: str,
    db: Session = Depends(get_db)
):
    """List dashboards for user"""
    try:
        dashboards = dashboard_service.list_dashboards(db, owner_id)
        return dashboards
    except Exception as e:
        logger.exception("Failed to list dashboards")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list dashboards: {str(e)}"
        )


@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: UUID,
    owner_id: str,
    db: Session = Depends(get_db)
):
    """Get dashboard by ID (hydrated if dynamic)"""
    try:
        dashboard = await dashboard_service.get_dashboard(db, dashboard_id, owner_id)
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found"
            )
        return dashboard
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get dashboard")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard: {str(e)}"
        )


@router.put("/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(
    dashboard_id: UUID,
    owner_id: str,
    update_data: DashboardUpdate,
    db: Session = Depends(get_db)
):
    """Update dashboard"""
    try:
        dashboard = await dashboard_service.update_dashboard(
            db, dashboard_id, owner_id, update_data
        )
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found"
            )
        return dashboard
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update dashboard")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update dashboard: {str(e)}"
        )


@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(
    dashboard_id: UUID,
    owner_id: str,
    db: Session = Depends(get_db)
):
    """Delete dashboard"""
    try:
        deleted = dashboard_service.delete_dashboard(db, dashboard_id, owner_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete dashboard")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete dashboard: {str(e)}"
        )

