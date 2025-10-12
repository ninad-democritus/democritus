/**
 * AI Chat Component
 * Right panel for natural language interaction with Query Service
 * Supports async query processing with real-time progress updates
 */

import { Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewChecked, NgZone } from '@angular/core';
import { FormControl, Validators } from '@angular/forms';
import { Subject, takeUntil, distinctUntilChanged } from 'rxjs';
import { AIChatService } from '../../../../services/ai-chat.service';
import { ChartDataService } from '../../../../services/chart-data.service';
import { QueryService } from '../../../../services/query.service';
import { ChatMessage } from '../../../../models/chat-message.model';
import { DashboardItem } from '../../../../models/dashboard-item.model';
import { CHART_TYPES, ChartType } from '../../../../models/chart-type.model';
import {
  WebSocketMessage,
  WSProgressMessage,
  WSSQLGeneratedMessage,
  WSCompletedMessage,
  WSErrorMessage,
  QueryStage,
  ChartGenerationResult,
  STAGE_INFO
} from '../../../../models/query-service.model';
import { runInZone } from '../../../../utils/zone-operators';

@Component({
  selector: 'app-ai-chat',
  templateUrl: './ai-chat.component.html',
  styleUrl: './ai-chat.component.scss'
})
export class AIChatComponent implements OnInit, OnDestroy, AfterViewChecked {
  @ViewChild('messageContainer') private messageContainer!: ElementRef;
  
  private destroy$ = new Subject<void>();
  private shouldScrollToBottom = false;

  messages: ChatMessage[] = [];
  selectedChart: DashboardItem | null = null;
  messageControl = new FormControl('', [Validators.required]);
  isSending = false;

  // Query progress tracking
  isProcessingQuery = false;
  currentQueryId: string | null = null;
  currentStage: QueryStage | null = null;
  completedStages: Set<QueryStage> = new Set();
  generatedSQL: string | null = null;
  currentStatusMessage: string = ''; // Only track the latest status message
  selectedChartIdAtQueryStart: string | null = null; // Store the ID at query start to prevent stale references

  constructor(
    private zone: NgZone,
    private aiChatService: AIChatService,
    private chartDataService: ChartDataService,
    private queryService: QueryService
  ) {}

  ngOnInit(): void {
    // Subscribe to messages
    // Using runInZone to ensure change detection works in Module Federation
    this.aiChatService.messages$
      .pipe(
        runInZone(this.zone),
        takeUntil(this.destroy$)
      )
      .subscribe(messages => {
        this.messages = messages;
        this.shouldScrollToBottom = true;
      });

    // Subscribe to selected chart - use distinctUntilChanged to prevent duplicates
    this.chartDataService.selectedChartId$
      .pipe(
        distinctUntilChanged(), // Only emit when the ID actually changes
        runInZone(this.zone),
        takeUntil(this.destroy$)
      )
      .subscribe(chartId => {
        this.selectedChart = chartId ? this.chartDataService.getSelectedChart() : null;
        /* console.log('[AIChatComponent] Selected chart updated:', this.selectedChart?.id); */
      });
  }

  ngAfterViewChecked(): void {
    if (this.shouldScrollToBottom) {
      this.scrollToBottom();
      this.shouldScrollToBottom = false;
    }
  }

  ngOnDestroy(): void {
    // Clean up WebSocket connections
    if (this.currentQueryId) {
      this.queryService.closeConnection(this.currentQueryId);
    }
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Send message to AI and process query
   */
  sendMessage(): void {
    if (this.messageControl.invalid || this.isSending || this.isProcessingQuery) return;

    const message = this.messageControl.value?.trim();
    if (!message) return;

    // Add user message
    this.aiChatService.addMessage({
      id: this.generateId(),
      sender: 'user',
      content: message,
      timestamp: new Date()
    });

    // Clear input
    this.messageControl.reset();

    // Process query
    this.processQuery(message);
  }

  /**
   * Process query with async WebSocket flow
   */
  private processQuery(query: string): void {
    this.isProcessingQuery = true;
    this.isSending = true;
    this.currentStage = null;
    this.completedStages.clear();
    this.generatedSQL = null;
    
    // CRITICAL: Store the selected chart ID at query start to prevent stale reference issues
    this.selectedChartIdAtQueryStart = this.selectedChart?.id || null;
    /* console.log('[AIChatComponent] Starting query with selected chart ID:', this.selectedChartIdAtQueryStart); */

    // Add AI "thinking" message
    const aiMessageId = this.generateId();
    this.aiChatService.addMessage({
      id: aiMessageId,
      sender: 'ai',
      content: 'Processing your query...',
      timestamp: new Date(),
      queryInProgress: true
    });

    // Build request
    const request = {
      naturalLanguageQuery: query,
      constraints: this.selectedChart ? {
        chartType: this.selectedChart.chartType.id,
        chartSize: {
          cols: this.selectedChart.cols,
          rows: this.selectedChart.rows
        },
        position: {
          x: this.selectedChart.x,
          y: this.selectedChart.y
        }
      } : undefined,
      context: {
        dashboardId: 'default', // TODO: Get actual dashboard ID
        existingCharts: this.chartDataService.getDashboardItems().map(chart => ({
          type: chart.chartType.id,
          title: chart.config.title,
          query: chart.config.naturalLanguageQuery || ''
        }))
      }
    };

    // Connect to query service with WebSocket
    this.queryService.generateChartWithProgress(request)
      .pipe(
        runInZone(this.zone),
        takeUntil(this.destroy$)
      )
      .subscribe({
        next: (message: WebSocketMessage) => {
          this.handleWebSocketMessage(message, aiMessageId);
        },
        error: (error) => {
          this.handleQueryError(error, aiMessageId);
        },
        complete: () => {
          /* console.log('[AIChatComponent] Query processing completed'); */
        }
      });
  }

  /**
   * Handle WebSocket messages
   */
  private handleWebSocketMessage(message: WebSocketMessage, aiMessageId: string): void {
/*     console.log('[AIChatComponent] Received message:', message); */

    switch (message.type) {
      case 'CONNECTED':
        this.currentQueryId = message.queryId;
        this.currentStatusMessage = 'Thinking';
        this.updateStatusMessage(aiMessageId);
        break;

      case 'PROGRESS':
        const progressMsg = message as WSProgressMessage;
        this.currentStage = progressMsg.stage;
        const stageInfo = STAGE_INFO[progressMsg.stage];
        
        // Update to latest status only
        this.currentStatusMessage = `${stageInfo.icon} ${stageInfo.description}`;
        this.updateStatusMessage(aiMessageId);
        
        if (this.currentStage && this.currentStage !== 'completed') {
          this.completedStages.add(this.currentStage);
        }
        break;

      case 'SQL_GENERATED':
        const sqlMsg = message as WSSQLGeneratedMessage;
        this.generatedSQL = sqlMsg.sqlQuery;
        break;

      case 'COMPLETED':
        const completedMsg = message as WSCompletedMessage;
        this.handleQuerySuccess(completedMsg.result, aiMessageId);
        break;

      case 'ERROR':
        const errorMsg = message as WSErrorMessage;
        this.handleQueryError(new Error(errorMsg.error.error), aiMessageId);
        break;
    }
  }

  /**
   * Update the status message with latest status only
   */
  private updateStatusMessage(messageId: string): void {
    this.aiChatService.updateMessage(messageId, {
      content: this.currentStatusMessage,
      queryInProgress: true
    });
  }

  /**
   * Handle successful query completion
   */
  private handleQuerySuccess(result: ChartGenerationResult, aiMessageId: string): void {
    /* console.log('[AIChatComponent] Query succeeded:', result);
    console.log('[AIChatComponent] Updating message with ID:', aiMessageId, 'to set queryInProgress: false'); */

    // CRITICAL: Explicitly set queryInProgress to false to stop the animation
    this.aiChatService.updateMessage(aiMessageId, {
      content: `✨ Chart generated successfully!`,
      queryInProgress: false  // This must be explicitly false, not undefined
    });

    // Add chart to dashboard or update existing, and highlight it
    let chartId: string;
    
    // Use the stored ID from query start to prevent stale reference issues
    /* console.log('[AIChatComponent] selectedChartIdAtQueryStart:', this.selectedChartIdAtQueryStart);
    console.log('[AIChatComponent] Current selected chart:', this.selectedChart?.id); */
    
    if (this.selectedChartIdAtQueryStart) {
      // Update existing chart
      chartId = this.selectedChartIdAtQueryStart;
      /* console.log('[AIChatComponent] Updating existing chart:', chartId); */
      
      // Verify the chart still exists
      const chartExists = this.chartDataService.getDashboardItems().find(item => item.id === chartId);
      /* console.log('[AIChatComponent] Chart exists:', !!chartExists, chartExists?.id); */
      
      this.chartDataService.updateChart(chartId, {
        config: {
          title: result.chartConfig.title,
          naturalLanguageQuery: result.naturalLanguageQuery,
          queryTimestamp: new Date(),
          echartsOptions: result.chartConfig.echartsOptions,
          queryMetadata: result.metadata
        }
      });
    } else {
      // Create new chart
      /* console.log('[AIChatComponent] Creating new chart (no selected chart at query start)'); */
      chartId = this.chartDataService.generateId(); // Use service's ID generator with 'chart-' prefix
      const newChart: DashboardItem = {
        id: chartId,
        chartType: this.getChartTypeFromId(result.chartConfig.type),
        x: 0,
        y: 0,
        cols: result.chartConfig.size?.cols || 12,
        rows: result.chartConfig.size?.rows || 6,
        config: {
          title: result.chartConfig.title,
          naturalLanguageQuery: result.naturalLanguageQuery,
          queryTimestamp: new Date(),
          echartsOptions: result.chartConfig.echartsOptions,
          queryMetadata: result.metadata
        }
      };
      this.chartDataService.addChart(newChart);
    }

    // Highlight the chart with animation
    this.chartDataService.highlightChart(chartId);

    // Reset state
    this.resetQueryState();
  }

  /**
   * Handle query error
   */
  private handleQueryError(error: any, aiMessageId: string): void {
    console.error('[AIChatComponent] Query failed:', error);
    console.log('[AIChatComponent] Updating message with ID:', aiMessageId, 'to set queryInProgress: false (ERROR)');

    const errorMessage = error?.message || 'Failed to process query. Please try again.';

    // CRITICAL: Explicitly set queryInProgress to false to stop the animation
    this.aiChatService.updateMessage(aiMessageId, {
      content: `❌ Error: ${errorMessage}`,
      queryInProgress: false  // This must be explicitly false, not undefined
    });

    console.log('[AIChatComponent] Error message updated, queryInProgress set to false');

    // Reset state
    this.resetQueryState();
  }

  /**
   * Reset query state
   */
  private resetQueryState(): void {
    this.isProcessingQuery = false;
    this.isSending = false;
    this.currentQueryId = null;
    this.currentStage = null;
    this.completedStages.clear();
    this.generatedSQL = null;
    this.currentStatusMessage = '';
    this.selectedChartIdAtQueryStart = null;
  }

  /**
   * Handle Enter key to send message
   */
  onKeyPress(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  /**
   * Clear chart selection
   */
  clearSelection(): void {
    this.chartDataService.selectChart(null);
  }

  /**
   * Scroll messages to bottom
   */
  private scrollToBottom(): void {
    try {
      if (this.messageContainer) {
        const element = this.messageContainer.nativeElement;
        element.scrollTop = element.scrollHeight;
      }
    } catch (err) {
      console.error('Error scrolling to bottom:', err);
    }
  }

  /**
   * Format timestamp
   */
  formatTime(date: Date): string {
    return new Date(date).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit'
    });
  }

  /**
   * Track by function for ngFor
   */
  trackByMessageId(index: number, message: ChatMessage): string {
    return message.id;
  }

  /**
   * Get chart type from ID
   */
  private getChartTypeFromId(id: string): ChartType {
    return CHART_TYPES.find(ct => ct.id === id) || CHART_TYPES[0];
  }

  /**
   * Generate unique ID
   */
  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}
