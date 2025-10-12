"""Dashboard business logic"""
import logging
import copy
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from sqlalchemy.orm.attributes import flag_modified

from ..db.models import Dashboard, Widget
from ..models import DashboardCreate, DashboardUpdate, DashboardListItem, DashboardViewItem, WidgetPreview
from .query_adapter import get_query_adapter

logger = logging.getLogger(__name__)


def strip_chart_data(chart_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove data arrays from chart config (for dynamic dashboards).
    
    Clears all data-dependent values while preserving the chart structure.
    The styling engine will intelligently reconstruct colors and legends
    based on the fresh data during hydration.
    
    Args:
        chart_config: Full chart configuration
        
    Returns:
        Template without data
    """
    config = copy.deepcopy(chart_config)
    
    if "echartsOptions" in config:
        echarts = config["echartsOptions"]
        
        # Strip xAxis data (categories)
        if "xAxis" in echarts:
            if isinstance(echarts["xAxis"], dict) and "data" in echarts["xAxis"]:
                echarts["xAxis"]["data"] = []
            elif isinstance(echarts["xAxis"], list):
                for axis in echarts["xAxis"]:
                    if "data" in axis:
                        axis["data"] = []
        
        # Strip yAxis data (if present)
        if "yAxis" in echarts:
            if isinstance(echarts["yAxis"], dict) and "data" in echarts["yAxis"]:
                echarts["yAxis"]["data"] = []
            elif isinstance(echarts["yAxis"], list):
                for axis in echarts["yAxis"]:
                    if "data" in axis:
                        axis["data"] = []
        
        # Strip series data (values and potentially itemStyle colors)
        # Note: The styling engine will reapply per-item colors if needed
        if "series" in echarts:
            for series in echarts["series"]:
                if "data" in series:
                    series["data"] = []
        
        # Strip legend data (will be reconstructed from fresh data)
        if "legend" in echarts and isinstance(echarts["legend"], dict):
            if "data" in echarts["legend"]:
                echarts["legend"]["data"] = []
    
    logger.debug("Stripped chart data for dynamic dashboard storage")
    return config


async def create_dashboard(db: Session, dashboard_data: DashboardCreate) -> Dashboard:
    """
    Create new dashboard.
    
    Args:
        db: Database session
        dashboard_data: Dashboard creation data
        
    Returns:
        Created dashboard
    """
    # Create dashboard
    dashboard = Dashboard(
        name=dashboard_data.name,
        owner_id=dashboard_data.owner_id,
        visibility=dashboard_data.visibility,
        dashboard_type=dashboard_data.dashboard_type,
        gridster_config=dashboard_data.gridster_config or {}
    )
    db.add(dashboard)
    db.flush()  # Get dashboard ID
    
    # Create widgets
    for widget_data in dashboard_data.widgets:
        # For dynamic dashboards, strip data from chart config
        chart_config = widget_data.chart_config
        if dashboard_data.dashboard_type == "dynamic":
            chart_config = strip_chart_data(chart_config)
        
        widget = Widget(
            dashboard_id=dashboard.id,
            grid_x=widget_data.grid_x,
            grid_y=widget_data.grid_y,
            grid_cols=widget_data.grid_cols,
            grid_rows=widget_data.grid_rows,
            chart_config=chart_config,
            widget_metadata=widget_data.metadata,
            nl_query=widget_data.nl_query
        )
        db.add(widget)
    
    db.commit()
    db.refresh(dashboard)
    
    logger.info(f"Created dashboard {dashboard.id} with {len(dashboard_data.widgets)} widgets")
    
    return dashboard


async def get_dashboard(db: Session, dashboard_id: UUID, owner_id: str) -> Optional[Dashboard]:
    """
    Get dashboard by ID.
    For dynamic dashboards, fetches live data.
    
    Args:
        db: Database session
        dashboard_id: Dashboard ID
        owner_id: User ID (for access control)
        
    Returns:
        Dashboard with hydrated widgets
    """
    # Fetch dashboard
    dashboard = db.query(Dashboard).filter(
        Dashboard.id == dashboard_id,
        (Dashboard.owner_id == owner_id) | (Dashboard.visibility == "public")
    ).first()
    
    if not dashboard:
        logger.warning(f"Dashboard {dashboard_id} not found or access denied for user {owner_id}")
        return None
    
    logger.info(f"Loading dashboard {dashboard_id} (type: {dashboard.dashboard_type}, widgets: {len(dashboard.widgets)})")
    
    # If static, return as-is
    if dashboard.dashboard_type == "static":
        logger.info(f"Dashboard {dashboard_id} is static, returning without hydration")
        return dashboard
    
    # Dynamic: hydrate widgets with live data
    logger.info(f"Starting hydration for dynamic dashboard {dashboard_id}")
    query_adapter = get_query_adapter()
    
    hydrated_count = 0
    error_count = 0
    
    for widget in dashboard.widgets:
        try:
            logger.info(f"Processing widget {widget.id}")
            
            # Extract SQL from metadata
            sql = widget.widget_metadata.get("sqlQuery") if widget.widget_metadata else None
            if not sql:
                logger.warning(f"Widget {widget.id} missing SQL query in metadata")
                # Create new config dict to ensure mutation is tracked
                new_config = copy.deepcopy(widget.chart_config)
                new_config["hydration_error"] = {
                    "message": "Missing SQL query in widget metadata",
                    "widget_id": str(widget.id),
                    "timestamp": datetime.utcnow().isoformat()
                }
                widget.chart_config = new_config
                flag_modified(widget, "chart_config")
                error_count += 1
                continue
            
            logger.info(f"Widget {widget.id} SQL query: {sql[:100]}...")
            
            # Validate SQL
            validation = await query_adapter.validate_sql(sql)
            logger.info(f"Widget {widget.id} SQL validation result: {validation}")
            
            if not validation["valid"]:
                logger.warning(f"Widget {widget.id} SQL validation failed: {validation.get('errors')}")
                # Create new config dict to ensure mutation is tracked
                new_config = copy.deepcopy(widget.chart_config)
                new_config["hydration_error"] = {
                    "message": "SQL validation failed",
                    "errors": validation.get("errors", []),
                    "widget_id": str(widget.id),
                    "timestamp": datetime.utcnow().isoformat()
                }
                widget.chart_config = new_config
                flag_modified(widget, "chart_config")
                error_count += 1
                continue
            
            # Execute SQL
            logger.info(f"Executing SQL for widget {widget.id}")
            data_result = await query_adapter.execute_sql(sql, limit=1000)
            logger.info(f"Widget {widget.id} query returned {data_result.get('row_count', 0)} rows")
            
            # Bind data to chart template
            # Try chartType first (set by frontend), fallback to recommendedChartType (legacy/AI suggestion), then default to bar
            chart_type = widget.widget_metadata.get("chartType") or widget.widget_metadata.get("recommendedChartType", "bar")
            logger.info(f"Binding data to {chart_type} chart for widget {widget.id}")
            logger.info(f"Sending to bind_chart_data: chart_config keys={list(widget.chart_config.keys())}")
            
            if "echartsOptions" in widget.chart_config:
                echarts = widget.chart_config["echartsOptions"]
                logger.info(f"  echartsOptions before binding: series={len(echarts.get('series', []))}, "
                           f"has_legend={'legend' in echarts}, has_color={'color' in echarts}")
                if echarts.get("series"):
                    logger.info(f"    series[0] keys: {list(echarts['series'][0].keys())}")
            
            bound_result = await query_adapter.bind_chart_data(
                chart_config=widget.chart_config,
                data=data_result,
                chart_type=chart_type
            )
            
            logger.info(f"Received from bind_chart_data: keys={list(bound_result.keys())}")
            
            # Update widget with live data - create new dict to ensure SQLAlchemy tracks the change
            new_config = bound_result["chart_config"]
            
            logger.info(f"Extracted chart_config: keys={list(new_config.keys())}")
            
            if "echartsOptions" in new_config:
                echarts = new_config["echartsOptions"]
                logger.info(f"  echartsOptions after binding: series={len(echarts.get('series', []))}, "
                           f"has_legend={'legend' in echarts}, has_color={'color' in echarts}")
                if echarts.get("series"):
                    series0 = echarts['series'][0]
                    logger.info(f"    series[0] keys: {list(series0.keys())}")
                    logger.info(f"    series[0] has_label={'label' in series0}")
                    if 'label' in series0:
                        logger.info(f"    series[0].label: {series0['label']}")
                if 'legend' in echarts:
                    logger.info(f"    legend: {echarts['legend']}")
            
            # Add hydration metadata
            new_config["hydration_metadata"] = {
                "hydrated_at": datetime.utcnow().isoformat(),
                "row_count": data_result.get("row_count", 0),
                "chart_type": chart_type
            }
            
            widget.chart_config = new_config
            flag_modified(widget, "chart_config")
            
            logger.info(f"Successfully hydrated widget {widget.id}")
            hydrated_count += 1
            
        except Exception as e:
            logger.exception(f"Failed to hydrate widget {widget.id}")
            # Create new config dict to ensure mutation is tracked
            new_config = copy.deepcopy(widget.chart_config)
            new_config["hydration_error"] = {
                "message": str(e),
                "widget_id": str(widget.id),
                "timestamp": datetime.utcnow().isoformat()
            }
            widget.chart_config = new_config
            flag_modified(widget, "chart_config")
            error_count += 1
    
    logger.info(f"Dashboard {dashboard_id} hydration complete: {hydrated_count} successful, {error_count} errors")
    
    return dashboard


def list_dashboards(db: Session, owner_id: str) -> List[DashboardListItem]:
    """
    List dashboards for user.
    
    Args:
        db: Database session
        owner_id: User ID
        
    Returns:
        List of dashboards
    """
    dashboards = db.query(
        Dashboard.id,
        Dashboard.name,
        Dashboard.visibility,
        Dashboard.dashboard_type,
        Dashboard.created_at,
        Dashboard.updated_at,
        func.count(Widget.id).label("widget_count")
    ).outerjoin(Widget).filter(
        (Dashboard.owner_id == owner_id) | (Dashboard.visibility == "public")
    ).group_by(Dashboard.id).all()
    
    return [
        DashboardListItem(
            id=d.id,
            name=d.name,
            visibility=d.visibility,
            dashboard_type=d.dashboard_type,
            widget_count=d.widget_count,
            created_at=d.created_at,
            updated_at=d.updated_at
        )
        for d in dashboards
    ]


def view_dashboards(
    db: Session,
    scope: str,
    search: str,
    user_id: str
) -> List[DashboardViewItem]:
    """
    Get dashboard list with widget preview (optimized for view page, no pagination).
    
    Args:
        db: Database session
        scope: Filter scope ('my', 'public', 'all')
        search: Search query for dashboard name
        user_id: User ID for filtering
        
    Returns:
        List of dashboards with widget previews
    """
    query_conditions = []
    params = {"user_id": user_id, "search": f"%{search}%"}
    
    if scope == "my":
        query_conditions.append("d.owner_id = :user_id")
    elif scope == "public":
        query_conditions.append("d.visibility = 'public'")
    else:
        query_conditions.append("(d.visibility = 'public' OR d.owner_id = :user_id)")

    where_clause = " AND ".join(query_conditions)

    # Optimized SQL with JSON aggregation for widget preview
    sql = f"""
        SELECT
            d.id, d.name, d.owner_id, d.visibility, d.dashboard_type,
            d.created_at, d.updated_at,
            COUNT(w.id) as widget_count,
            COALESCE(
                json_agg(
                    json_build_object(
                        'id', w.id,
                        'name', COALESCE(w.chart_config->>'title', 'Untitled'),
                        'chart_type', COALESCE(
                            w.widget_metadata->>'chartType',
                            w.chart_config->'queryMetadata'->>'recommendedChartType',
                            w.chart_config->'echartsOptions'->'series'->0->>'type',
                            'bar'
                        ),
                        'position', json_build_object('x', w.grid_x, 'y', w.grid_y),
                        'size', json_build_object('cols', w.grid_cols, 'rows', w.grid_rows)
                    ) ORDER BY w.grid_y, w.grid_x
                ) FILTER (WHERE w.id IS NOT NULL),
                '[]'::json
            ) as widgets_preview
        FROM dashboards_db.dashboards d
        LEFT JOIN dashboards_db.widgets w ON d.id = w.dashboard_id
        WHERE {where_clause} AND d.name ILIKE :search
        GROUP BY d.id
        ORDER BY d.updated_at DESC
    """

    results = db.execute(text(sql), params).fetchall()
    
    return [
        DashboardViewItem(
            id=row.id,
            name=row.name,
            owner_id=row.owner_id,
            visibility=row.visibility,
            dashboard_type=row.dashboard_type,
            created_at=row.created_at,
            updated_at=row.updated_at,
            widget_count=row.widget_count,
            widgets_preview=[
                WidgetPreview(**widget) for widget in row.widgets_preview
            ] if row.widgets_preview else []
        )
        for row in results
    ]


async def update_dashboard(
    db: Session,
    dashboard_id: UUID,
    owner_id: str,
    update_data: DashboardUpdate
) -> Optional[Dashboard]:
    """
    Update dashboard.
    
    Args:
        db: Database session
        dashboard_id: Dashboard ID
        owner_id: User ID
        update_data: Update data
        
    Returns:
        Updated dashboard
    """
    dashboard = db.query(Dashboard).filter(
        Dashboard.id == dashboard_id,
        Dashboard.owner_id == owner_id
    ).first()
    
    if not dashboard:
        return None
    
    # Update fields
    if update_data.name:
        dashboard.name = update_data.name
    if update_data.visibility:
        dashboard.visibility = update_data.visibility
    
    # Update widgets if provided
    if update_data.widgets is not None:
        # Delete existing widgets
        db.query(Widget).filter(Widget.dashboard_id == dashboard_id).delete()
        
        # Create new widgets
        for widget_data in update_data.widgets:
            chart_config = widget_data.chart_config
            if dashboard.dashboard_type == "dynamic":
                chart_config = strip_chart_data(chart_config)
            
            widget = Widget(
                dashboard_id=dashboard.id,
                grid_x=widget_data.grid_x,
                grid_y=widget_data.grid_y,
                grid_cols=widget_data.grid_cols,
                grid_rows=widget_data.grid_rows,
                chart_config=chart_config,
                widget_metadata=widget_data.metadata,
                nl_query=widget_data.nl_query
            )
            db.add(widget)
    
    db.commit()
    db.refresh(dashboard)
    
    return dashboard


def delete_dashboard(db: Session, dashboard_id: UUID, owner_id: str) -> bool:
    """
    Delete dashboard.
    
    Args:
        db: Database session
        dashboard_id: Dashboard ID
        owner_id: User ID
        
    Returns:
        True if deleted, False if not found
    """
    dashboard = db.query(Dashboard).filter(
        Dashboard.id == dashboard_id,
        Dashboard.owner_id == owner_id
    ).first()
    
    if not dashboard:
        return False
    
    db.delete(dashboard)
    db.commit()
    
    logger.info(f"Deleted dashboard {dashboard_id}")
    
    return True

