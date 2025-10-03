/**
 * AI Chat Service
 * Orchestrates chat messages and Query Service interaction
 * Handles both Workflow A (with chart context) and Workflow B (without context)
 */

import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, throwError } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';
import { ChatMessage } from '../models/chat-message.model';
import { ChartGenerationRequest, ChartGenerationResult } from '../models/query-service.model';
import { DashboardItem } from '../models/dashboard-item.model';
import { CHART_TYPES, ChartType } from '../models/chart-type.model';
import { QueryService } from './query.service';
import { ChartDataService } from './chart-data.service';

@Injectable({
  providedIn: 'root'
})
export class AIChatService {
  private messagesSubject = new BehaviorSubject<ChatMessage[]>([]);
  public messages$ = this.messagesSubject.asObservable();

  constructor(
    private queryService: QueryService,
    private chartDataService: ChartDataService
  ) {
    // Add welcome message
    this.addMessage({
      id: this.generateId(),
      sender: 'ai',
      content: 'Hello! I can help you create data visualizations. You can either drag a chart type from the library and ask me to populate it, or simply describe what you want to see and I\'ll create a chart for you.',
      timestamp: new Date()
    });
  }

  /**
   * Send user message and get AI response
   * Handles both workflows:
   * - With selected chart (Workflow A)
   * - Without selected chart (Workflow B)
   */
  sendMessage(content: string): void {
    // Add user message immediately
    const userMessage: ChatMessage = {
      id: this.generateId(),
      sender: 'user',
      content,
      timestamp: new Date()
    };
    this.addMessage(userMessage);

    // Get selected chart context if any
    const selectedChart = this.chartDataService.getSelectedChart();

    // Prepare request
    const request: ChartGenerationRequest = {
      naturalLanguageQuery: content,
      constraints: selectedChart ? {
        chartType: selectedChart.chartType.id,
        chartSize: {
          cols: selectedChart.cols,
          rows: selectedChart.rows
        },
        position: { x: selectedChart.x, y: selectedChart.y }
      } : undefined
    };

    // Add loading message
    const loadingMessage: ChatMessage = {
      id: this.generateId(),
      sender: 'ai',
      content: 'Analyzing your query and generating visualization...',
      timestamp: new Date(),
      queryInProgress: true,
      chartReference: selectedChart?.id
    };
    this.addMessage(loadingMessage);

    // Call Query Service
    this.queryService.generateChart(request).pipe(
      tap(result => {
        // Remove loading message
        this.removeMessage(loadingMessage.id);

        // Add AI response
        const aiMessage: ChatMessage = {
          id: this.generateId(),
          sender: 'ai',
          content: this.generateResponseText(result, selectedChart),
          timestamp: new Date(),
          chartSuggestion: result,
          chartReference: selectedChart?.id
        };
        this.addMessage(aiMessage);

        // Update chart or create new one
        if (selectedChart) {
          // Workflow A: Update existing chart
          this.chartDataService.updateChartFromAI(selectedChart.id, result);
        } else {
          // Workflow B: Create new chart
          this.createChartFromAI(result);
        }
      }),
      catchError(error => {
        this.removeMessage(loadingMessage.id);
        const errorMessage: ChatMessage = {
          id: this.generateId(),
          sender: 'ai',
          content: `Sorry, I encountered an error: ${error.message}. Please try rephrasing your query.`,
          timestamp: new Date()
        };
        this.addMessage(errorMessage);
        return throwError(() => error);
      })
    ).subscribe();
  }

  /**
   * Generate AI response text based on result
   */
  private generateResponseText(
    result: ChartGenerationResult,
    selectedChart?: DashboardItem | null
  ): string {
    if (selectedChart) {
      return `✅ I've updated your ${result.chartConfig.type} chart with the requested data. The query returned ${result.data.length} records.`;
    } else {
      let response = `✅ I've created a ${result.chartConfig.type} chart for you with ${result.data.length} records.`;
      if (result.metadata.recommendedChartType) {
        response += ` I recommended this chart type as it's best suited for your data.`;
      }
      return response;
    }
  }

  /**
   * Create new chart from AI suggestion (Workflow B)
   */
  private createChartFromAI(result: ChartGenerationResult): void {
    const chartType = this.getChartType(result.chartConfig.type);
    
    const newItem: DashboardItem = {
      id: this.chartDataService.generateId(),
      chartType: chartType,
      x: 0,
      y: 0,
      cols: result.chartConfig.size?.cols || chartType.defaultSize.cols,
      rows: result.chartConfig.size?.rows || chartType.defaultSize.rows,
      config: {
        title: result.chartConfig.title,
        naturalLanguageQuery: result.naturalLanguageQuery,
        queryTimestamp: new Date(),
        echartsOptions: result.chartConfig.echartsOptions,
        queryMetadata: result.metadata
      }
    };

    this.chartDataService.addChart(newItem);
  }

  /**
   * Get chart type by ID
   */
  private getChartType(typeId: string): ChartType {
    return CHART_TYPES.find(ct => ct.id === typeId) || CHART_TYPES[0];
  }

  /**
   * Add message to chat
   */
  private addMessage(message: ChatMessage): void {
    const messages = this.messagesSubject.value;
    this.messagesSubject.next([...messages, message]);
  }

  /**
   * Remove message from chat
   */
  private removeMessage(id: string): void {
    const messages = this.messagesSubject.value.filter(m => m.id !== id);
    this.messagesSubject.next(messages);
  }

  /**
   * Clear all messages
   */
  clearMessages(): void {
    this.messagesSubject.next([]);
  }

  /**
   * Generate unique ID
   */
  private generateId(): string {
    return `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}

