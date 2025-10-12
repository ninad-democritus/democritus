"""SQLAlchemy database models"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()


class Dashboard(Base):
    """Dashboard model"""
    __tablename__ = "dashboards"
    __table_args__ = {"schema": "dashboards_db"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    owner_id = Column(String(255), nullable=False, index=True)
    visibility = Column(String(20), nullable=False)
    dashboard_type = Column(String(20), nullable=False)
    gridster_config = Column(JSONB, nullable=False, default={
        "gridType": "fit",
        "minCols": 24,
        "maxCols": 24,
        "minRows": 24,
        "margin": 4,
        "compactType": "none"
    })
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    widgets = relationship("Widget", back_populates="dashboard", cascade="all, delete-orphan")


class Widget(Base):
    """Widget model"""
    __tablename__ = "widgets"
    __table_args__ = {"schema": "dashboards_db"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dashboard_id = Column(UUID(as_uuid=True), ForeignKey("dashboards_db.dashboards.id", ondelete="CASCADE"), nullable=False, index=True)
    grid_x = Column(Integer, nullable=False)
    grid_y = Column(Integer, nullable=False)
    grid_cols = Column(Integer, nullable=False)
    grid_rows = Column(Integer, nullable=False)
    chart_config = Column(JSONB, nullable=False)
    widget_metadata = Column(JSONB)
    nl_query = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    dashboard = relationship("Dashboard", back_populates="widgets")

