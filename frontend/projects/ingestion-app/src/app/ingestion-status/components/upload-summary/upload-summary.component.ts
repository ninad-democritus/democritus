import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

interface FileSummary {
  file_name: string;
  record_count: number;
  processing_time: number;
  processed_at: string;
}

interface UploadStats {
  total_files: number;
  total_records: number;
  file_summary: FileSummary[];
}

@Component({
  selector: 'app-upload-summary',template: `
    <div class="upload-summary-container">
      <!-- Summary Header -->
      <div class="summary-header">
        <h3 class="summary-title">
          <svg class="summary-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
          </svg>
          Upload Summary
        </h3>
        
        <!-- Quick Stats -->
        <div class="quick-stats">
          <div class="stat-item">
            <span class="stat-value">{{ stats.total_files }}</span>
            <span class="stat-label">Files</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-value">{{ formatNumber(stats.total_records) }}</span>
            <span class="stat-label">Records</span>
          </div>
        </div>
      </div>
      
      <!-- File Details Table -->
      <div *ngIf="stats.file_summary && stats.file_summary.length > 0" class="file-details">
        <div class="table-container">
          <table class="summary-table">
            <thead class="table-header">
              <tr>
                <th class="table-th">File Name</th>
                <th class="table-th text-right">Records</th>
                <th class="table-th text-right">Processing Time</th>
                <th class="table-th text-right">Processed At</th>
              </tr>
            </thead>
            <tbody class="table-body">
              <tr *ngFor="let file of stats.file_summary" class="table-row">
                <td class="table-td">
                  <div class="file-info">
                    <div class="file-icon">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                      </svg>
                    </div>
                    <span class="file-name">{{ file.file_name }}</span>
                  </div>
                </td>
                <td class="table-td text-right">
                  <span class="record-count">{{ formatNumber(file.record_count) }}</span>
                </td>
                <td class="table-td text-right">
                  <span class="processing-time">{{ formatTime(file.processing_time) }}</span>
                </td>
                <td class="table-td text-right">
                  <span class="processed-time">{{ formatTimestamp(file.processed_at) }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      <!-- Empty State -->
      <div *ngIf="!stats.file_summary || stats.file_summary.length === 0" class="empty-state">
        <svg class="empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
        </svg>
        <p class="empty-text">No file details available yet</p>
        <p class="empty-subtext">File processing information will appear here once ingestion completes</p>
      </div>
    </div>
  `,
  styleUrls: ['./upload-summary.component.scss']
})
export class UploadSummaryComponent {
  @Input() stats: UploadStats = {
    total_files: 0,
    total_records: 0,
    file_summary: []
  };

  formatNumber(num: number): string {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  }

  formatTime(seconds: number): string {
    if (seconds < 60) {
      return `${seconds.toFixed(1)}s`;
    } else {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = Math.floor(seconds % 60);
      return `${minutes}m ${remainingSeconds}s`;
    }
  }

  formatTimestamp(timestamp: string): string {
    if (!timestamp) return '';
    
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch (error) {
      return timestamp;
    }
  }
}

