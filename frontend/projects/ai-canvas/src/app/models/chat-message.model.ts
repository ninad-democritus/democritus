/**
 * Chat Message Model
 * Represents messages in the AI chat interface
 */

import { ChartGenerationResult } from './query-service.model';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  content: string;
  timestamp: Date;
  
  // Reference to chart this message relates to
  chartReference?: string;
  
  // Full result from Query Service (for AI messages with chart suggestions)
  chartSuggestion?: ChartGenerationResult;
  
  // Show loading state while query is in progress
  queryInProgress?: boolean;
}

