/**
 * Query Service Models
 * Request and response interfaces for the backend Query Service API
 */

import { QueryMetadata } from './dashboard-item.model';

/**
 * Request to Query Service
 * Sent from frontend AI Chat to backend
 */
export interface ChartGenerationRequest {
  // Required: User's natural language query
  naturalLanguageQuery: string;
  
  // Optional constraints from existing chart or user preference
  // Present in Workflow A (drag-drop first, then populate)
  // Absent in Workflow B (AI creates everything)
  constraints?: {
    chartType?: string; // 'bar', 'line', 'pie', etc.
    chartSize?: { cols: number; rows: number };
    position?: { x: number; y: number };
  };
  
  // Optional context for better AI understanding
  context?: {
    dashboardId?: string;
    existingCharts?: Array<{
      type: string;
      title: string;
      query: string;
    }>;
  };
}

/**
 * Response from Query Service
 * Contains data, chart configuration, and metadata
 */
export interface ChartGenerationResult {
  success: boolean;
  
  // Actual data from database
  data: any[];
  
  // Chart configuration
  chartConfig: {
    type: string; // Recommended or specified chart type
    title: string; // Auto-generated title
    echartsOptions: any; // Complete ECharts configuration
    size?: { cols: number; rows: number }; // Recommended size (if not constrained)
  };
  
  // Metadata for transparency and debugging
  metadata: QueryMetadata;
  
  // Echo back the original query for frontend storage
  naturalLanguageQuery: string;
  
  // Error message if success is false
  error?: string;
}

/**
 * Error response from Query Service
 */
export interface QueryServiceError {
  success: false;
  error: string; // Human-readable error message
  errorCode: string; // Machine-readable error code
  details?: any; // Additional error details
}

