/**
 * AI Chat Component
 * Right panel for natural language interaction with Query Service
 */

import { Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { FormControl, Validators } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { AIChatService } from '../../../../services/ai-chat.service';
import { ChartDataService } from '../../../../services/chart-data.service';
import { ChatMessage } from '../../../../models/chat-message.model';
import { DashboardItem } from '../../../../models/dashboard-item.model';

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

  constructor(
    private aiChatService: AIChatService,
    private chartDataService: ChartDataService
  ) {}

  ngOnInit(): void {
    // Subscribe to messages
    this.aiChatService.messages$
      .pipe(takeUntil(this.destroy$))
      .subscribe(messages => {
        this.messages = messages;
        this.shouldScrollToBottom = true;
      });

    // Subscribe to selected chart
    this.chartDataService.selectedChartId$
      .pipe(takeUntil(this.destroy$))
      .subscribe(chartId => {
        this.selectedChart = chartId ? this.chartDataService.getSelectedChart() : null;
      });
  }

  ngAfterViewChecked(): void {
    if (this.shouldScrollToBottom) {
      this.scrollToBottom();
      this.shouldScrollToBottom = false;
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Send message to AI
   */
  sendMessage(): void {
    if (this.messageControl.invalid || this.isSending) return;

    const message = this.messageControl.value?.trim();
    if (!message) return;

    this.isSending = true;
    this.aiChatService.sendMessage(message);
    this.messageControl.reset();
    this.isSending = false;
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
}

