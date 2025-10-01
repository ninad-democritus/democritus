import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

interface PipelineStatus {
  run_id: string;
  status: string;
  step: string;
  message: string;
  duration: string;
  started_at: string;
  completed_at?: string;
  error?: string;
  timestamp: string;
}

@Component({
  selector: 'app-status-summary',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="status-summary-container">
      <!-- Run Info -->
      <div class="run-info">
        <div class="run-detail">
          <span class="detail-label">Status:</span>
          <span class="detail-value" [class]="getStatusClass()">
            {{ status.status | titlecase }}
          </span>
        </div>
        
        <div class="run-detail">
          <span class="detail-label">Duration:</span>
          <span class="detail-value">{{ status.duration }}</span>
        </div>
        
        <div class="run-detail">
          <span class="detail-label">Run ID:</span>
          <span class="detail-value detail-mono">{{ status.run_id.substring(0, 8) }}...</span>
        </div>
        
        <div *ngIf="status.started_at" class="run-detail">
          <span class="detail-label">Started:</span>
          <span class="detail-value">{{ formatTimestamp(status.started_at) }}</span>
        </div>
        
        <div *ngIf="status.completed_at" class="run-detail">
          <span class="detail-label">Completed:</span>
          <span class="detail-value">{{ formatTimestamp(status.completed_at) }}</span>
        </div>
      </div>
      
      <!-- Status Message -->
      <div *ngIf="status.message" class="status-message" [class]="getMessageClass()">
        <div class="message-content">
          <svg class="message-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" [attr.d]="getMessageIconPath()"></path>
          </svg>
          <span class="message-text">{{ status.message }}</span>
        </div>
      </div>
      
      <!-- Error Details -->
      <div *ngIf="status.error" class="error-details">
        <div class="error-header">
          <svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <span class="error-title">Pipeline Error</span>
        </div>
        <div class="error-content">{{ status.error }}</div>
      </div>
    </div>
  `,
  styleUrls: ['./status-summary.component.scss']
})
export class StatusSummaryComponent {
  @Input() status!: PipelineStatus;

  getStatusClass(): string {
    switch (this.status.status?.toLowerCase()) {
      case 'completed': return 'status-completed';
      case 'failed': return 'status-failed';
      case 'running': return 'status-running';
      default: return 'status-pending';
    }
  }

  getMessageClass(): string {
    switch (this.status.status?.toLowerCase()) {
      case 'completed': return 'message-success';
      case 'failed': return 'message-error';
      case 'running': return 'message-info';
      default: return 'message-neutral';
    }
  }

  getMessageIconPath(): string {
    switch (this.status.status?.toLowerCase()) {
      case 'completed': return 'M5 13l4 4L19 7';
      case 'failed': return 'M6 18L18 6M6 6l12 12';
      case 'running': return 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
      default: return 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
    }
  }

  formatTimestamp(timestamp: string): string {
    if (!timestamp) return '';
    
    try {
      const date = new Date(timestamp);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch (error) {
      return timestamp;
    }
  }
}

