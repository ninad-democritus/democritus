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

/**
 * Async response when query is initiated (202 Accepted)
 */
export interface ChartGenerationInitiated {
  queryId: string;
  websocketUrl: string;
  status: 'initiated';
}

/**
 * WebSocket message types
 */
export type WebSocketMessageType = 
  | 'CONNECTED' 
  | 'PROGRESS' 
  | 'SQL_GENERATED' 
  | 'COMPLETED' 
  | 'ERROR';

/**
 * Base WebSocket message
 */
export interface WebSocketMessage {
  type: WebSocketMessageType;
  queryId: string;
  timestamp: string;
}

/**
 * Connection confirmation message
 */
export interface WSConnectedMessage extends WebSocketMessage {
  type: 'CONNECTED';
  message: string;
}

/**
 * Progress update message
 */
export interface WSProgressMessage extends WebSocketMessage {
  type: 'PROGRESS';
  stage: QueryStage;
  message: string;
}

/**
 * SQL generated message (for transparency)
 */
export interface WSSQLGeneratedMessage extends WebSocketMessage {
  type: 'SQL_GENERATED';
  sqlQuery: string;
}

/**
 * Completion message with final result
 */
export interface WSCompletedMessage extends WebSocketMessage {
  type: 'COMPLETED';
  result: ChartGenerationResult;
}

/**
 * Error message
 */
export interface WSErrorMessage extends WebSocketMessage {
  type: 'ERROR';
  error: QueryServiceError;
}

/**
 * Query processing stages
 */
export type QueryStage =
  | 'parsing_query'
  | 'fetching_metadata'
  | 'generating_sql'
  | 'validating_sql'
  | 'retrying_sql'
  | 'executing_query'
  | 'recommending_chart'
  | 'generating_chart_config'
  | 'completed';

/**
 * Stage display information
 */
export interface StageInfo {
  stage: QueryStage;
  label: string;
  icon: string;
  description: string;
  estimatedDuration?: number; // in seconds
}

/**
 * Stage metadata for UI display
 */
export const STAGE_INFO: Record<QueryStage, StageInfo> = {
  parsing_query: {
    stage: 'parsing_query',
    label: 'Parsing Query',
    icon: '🔍',
    description: 'Understanding your natural language query',
    estimatedDuration: 2
  },
  fetching_metadata: {
    stage: 'fetching_metadata',
    label: 'Fetching Metadata',
    icon: '📚',
    description: 'Retrieving table schemas from catalog',
    estimatedDuration: 3
  },
  generating_sql: {
    stage: 'generating_sql',
    label: 'Generating SQL',
    icon: '⚙️',
    description: 'Converting query to SQL (this may take 1-2 minutes)',
    estimatedDuration: 90
  },
  validating_sql: {
    stage: 'validating_sql',
    label: 'Validating SQL',
    icon: '✅',
    description: 'Checking SQL against schema',
    estimatedDuration: 5
  },
  retrying_sql: {
    stage: 'retrying_sql',
    label: 'Retrying',
    icon: '🔄',
    description: 'Retrying with corrections',
    estimatedDuration: 60
  },
  executing_query: {
    stage: 'executing_query',
    label: 'Executing Query',
    icon: '🚀',
    description: 'Running query against data warehouse',
    estimatedDuration: 10
  },
  recommending_chart: {
    stage: 'recommending_chart',
    label: 'Recommending Chart',
    icon: '📊',
    description: 'Analyzing data and suggesting visualization',
    estimatedDuration: 5
  },
  generating_chart_config: {
    stage: 'generating_chart_config',
    label: 'Generating Chart',
    icon: '🎨',
    description: 'Creating chart configuration (this may take 1-2 minutes)',
    estimatedDuration: 90
  },
  completed: {
    stage: 'completed',
    label: 'Completed',
    icon: '✨',
    description: 'Chart generated successfully!',
    estimatedDuration: 0
  }
};

