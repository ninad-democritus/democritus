import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

interface FileInfo {
  file: File;
  fileName: string;
  fileType: string;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  source: 'direct' | 'folder' | 'zip';
  path?: string;
}

@Component({
  selector: 'app-file-row',
  standalone: true,
  imports: [CommonModule],
  template: `
    <tr class="file-row" [class]="getTableRowClasses()">
      <!-- File Info -->
      <td class="file-table-td">
        <div class="file-info">
          <div class="file-icon" [class]="getFileIconClasses()">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    [attr.d]="getFileIconPath()"></path>
            </svg>
          </div>
          <div class="file-details">
            <span class="file-name">{{ fileInfo.fileName }}</span>
            <span *ngIf="fileInfo.path" class="file-path">{{ fileInfo.path }}</span>
          </div>
        </div>
      </td>
      
      <!-- Source -->
      <td class="file-table-td">
        <span class="source-badge" [class]="getSourceBadgeClass()">
          {{ getSourceText() }}
        </span>
      </td>
      
      <!-- Size -->
      <td class="file-table-td">
        <span class="file-size">{{ getFormattedSize() }}</span>
      </td>
      
      <!-- Status -->
      <td class="file-table-td">
        <span class="file-status" [class]="getStatusBadgeClasses()">
          {{ getStatusText() }}
        </span>
      </td>
      
      <!-- Progress/Actions -->
      <td class="file-table-td text-center">
        <!-- Uploading Spinner -->
        <div *ngIf="fileInfo.status === 'uploading'" class="progress-indicator">
          <svg class="animate-spin w-5 h-5" style="color: var(--color-primary-500);" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 714 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
        
        <!-- Completed Checkmark -->
        <div *ngIf="fileInfo.status === 'completed'" class="success-indicator">
          <svg class="w-5 h-5" style="color: var(--color-success-500);" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
          </svg>
        </div>
        
        <!-- Error X -->
        <div *ngIf="fileInfo.status === 'error'" class="error-indicator">
          <svg class="w-5 h-5" style="color: var(--color-error-500);" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </div>
        
        <!-- Remove Button (when pending) -->
        <button 
          *ngIf="fileInfo.status === 'pending'"
          (click)="onRemoveFile()"
          class="remove-file-button"
          title="Remove File">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
          </svg>
        </button>
      </td>
    </tr>
  `,
  styleUrls: ['./file-row.component.scss']
})
export class FileRowComponent {
  @Input() fileInfo!: FileInfo;
  @Output() removeFile = new EventEmitter<FileInfo>();

  onRemoveFile() {
    this.removeFile.emit(this.fileInfo);
  }

  getFormattedSize(): string {
    const sizeInMB = this.fileInfo.file.size / 1024 / 1024;
    return `${sizeInMB.toFixed(1)} MB`;
  }

  getStatusText(): string {
    switch (this.fileInfo.status) {
      case 'pending': return 'Ready';
      case 'uploading': return 'Uploading...';
      case 'completed': return 'Completed';
      case 'error': return 'Error';
      default: return 'Unknown';
    }
  }

  getSourceText(): string {
    switch (this.fileInfo.source) {
      case 'direct': return 'File';
      case 'folder': return 'Folder';
      case 'zip': return 'ZIP';
      default: return 'Unknown';
    }
  }

  getTableRowClasses(): string {
    switch (this.fileInfo.status) {
      case 'uploading': return 'file-item-uploading';
      case 'completed': return 'file-item-completed';
      case 'error': return 'file-item-error';
      default: return 'file-item-pending';
    }
  }

  getFileIconClasses(): string {
    switch (this.fileInfo.status) {
      case 'uploading': return 'file-icon-uploading';
      case 'completed': return 'file-icon-completed';
      case 'error': return 'file-icon-error';
      default: return 'file-icon-pending';
    }
  }

  getFileIconPath(): string {
    switch (this.fileInfo.status) {
      case 'uploading': return 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12';
      case 'completed': return 'M5 13l4 4L19 7';
      case 'error': return 'M6 18L18 6M6 6l12 12';
      default: return 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z';
    }
  }

  getStatusBadgeClasses(): string {
    switch (this.fileInfo.status) {
      case 'uploading': return 'status-uploading';
      case 'completed': return 'status-completed';
      case 'error': return 'status-error';
      default: return 'status-pending';
    }
  }

  getSourceBadgeClass(): string {
    switch (this.fileInfo.source) {
      case 'direct': return 'source-direct';
      case 'folder': return 'source-folder';
      case 'zip': return 'source-zip';
      default: return 'source-unknown';
    }
  }
}

