/**
 * Dashboard Item Model
 * Represents a single chart widget on the dashboard grid
 */

import { ChartType } from './chart-type.model';

export interface DashboardItem {
  id: string;
  chartType: ChartType;
  x: number;
  y: number;
  cols: number;
  rows: number;
  config: ChartConfig;
  isSelected?: boolean; // For AI chat context
  isHighlighted?: boolean; // For highlighting newly created/updated charts
}

/**
 * Chart Configuration
 * Stores the data query, ECharts options, and metadata
 */
export interface ChartConfig {
  title: string;
  
  // CRITICAL: Natural language query stored for:
  // 1. Dashboard reload/persistence
  // 2. Data refresh
  // 3. User reference
  naturalLanguageQuery?: string;
  
  // When the query was last executed
  queryTimestamp?: Date;
  
  // Complete ECharts configuration from backend
  echartsOptions: any;
  
  // Metadata from Query Service
  queryMetadata?: QueryMetadata;
  
  // Hydration error (for dynamic dashboards that failed to load data)
  hydration_error?: {
    message: string;
    errors?: string[];
    widget_id: string;
    timestamp: string;
  };
  
  // Hydration metadata (for successfully loaded dynamic dashboards)
  hydration_metadata?: {
    hydrated_at: string;
    row_count: number;
    chart_type: string;
  };
}

/**
 * Query Metadata
 * Additional information from the Query Service backend
 */
export interface QueryMetadata {
  sqlQuery?: string; // Generated SQL (for debugging/transparency)
  dataSchema?: any; // Schema of returned data
  recommendedChartType?: string; // AI's recommendation if user didn't specify
  confidence?: number; // AI confidence in the result (0-1)
}

/**
 * Dashboard Model
 * Complete dashboard with all charts and metadata
 */
export interface Dashboard {
  id: string;
  name: string;
  description?: string;
  items: DashboardItem[];
  createdAt: Date;
  updatedAt: Date;
}

