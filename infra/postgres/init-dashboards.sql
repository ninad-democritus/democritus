-- =====================================================
-- Dashboard Management Service Database Schema
-- =====================================================
-- This script initializes the dashboards_db schema
-- for storing dashboard configurations and widgets
-- =====================================================

-- Create dashboard schema
CREATE SCHEMA IF NOT EXISTS dashboards_db;

-- =====================================================
-- Table: dashboards
-- Stores dashboard metadata and configuration
-- =====================================================
CREATE TABLE IF NOT EXISTS dashboards_db.dashboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    owner_id VARCHAR(255) NOT NULL,
    visibility VARCHAR(20) NOT NULL CHECK (visibility IN ('private', 'public')),
    dashboard_type VARCHAR(20) NOT NULL CHECK (dashboard_type IN ('static', 'dynamic')),
    gridster_config JSONB DEFAULT '{
        "gridType": "fit",
        "minCols": 24,
        "maxCols": 24,
        "minRows": 24,
        "margin": 4,
        "compactType": "none"
    }'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =====================================================
-- Table: widgets
-- Stores individual chart widgets within dashboards
-- =====================================================
CREATE TABLE IF NOT EXISTS dashboards_db.widgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dashboard_id UUID NOT NULL,
    
    -- Grid position and size
    grid_x INTEGER NOT NULL,
    grid_y INTEGER NOT NULL,
    grid_cols INTEGER NOT NULL,
    grid_rows INTEGER NOT NULL,
    
    -- Chart configuration and data
    chart_config JSONB NOT NULL,
    widget_metadata JSONB,
    nl_query TEXT,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Foreign key constraint with cascade delete
    CONSTRAINT fk_dashboard
        FOREIGN KEY (dashboard_id)
        REFERENCES dashboards_db.dashboards(id)
        ON DELETE CASCADE
);

-- =====================================================
-- Indexes for performance optimization
-- =====================================================

-- Index for filtering dashboards by owner
CREATE INDEX IF NOT EXISTS idx_dashboards_owner 
    ON dashboards_db.dashboards(owner_id);

-- Index for filtering dashboards by visibility
CREATE INDEX IF NOT EXISTS idx_dashboards_visibility 
    ON dashboards_db.dashboards(visibility);

-- Index for fetching widgets by dashboard
CREATE INDEX IF NOT EXISTS idx_widgets_dashboard 
    ON dashboards_db.widgets(dashboard_id);

-- =====================================================
-- Triggers for automatic timestamp updates
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION dashboards_db.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at on dashboard changes
CREATE TRIGGER update_dashboards_updated_at
    BEFORE UPDATE ON dashboards_db.dashboards
    FOR EACH ROW
    EXECUTE FUNCTION dashboards_db.update_updated_at_column();

-- =====================================================
-- Comments for documentation
-- =====================================================

COMMENT ON SCHEMA dashboards_db IS 'Dashboard Management Service schema';
COMMENT ON TABLE dashboards_db.dashboards IS 'Stores dashboard metadata and configuration';
COMMENT ON TABLE dashboards_db.widgets IS 'Stores chart widgets within dashboards';
COMMENT ON COLUMN dashboards_db.dashboards.visibility IS 'Access control: private (owner only) or public (all users)';
COMMENT ON COLUMN dashboards_db.dashboards.dashboard_type IS 'Dashboard behavior: static (data snapshot) or dynamic (live queries)';
COMMENT ON COLUMN dashboards_db.widgets.chart_config IS 'ECharts configuration (template for dynamic, complete for static)';
COMMENT ON COLUMN dashboards_db.widgets.widget_metadata IS 'Additional metadata including SQL queries for dynamic dashboards';

-- =====================================================
-- End of initialization script
-- =====================================================

