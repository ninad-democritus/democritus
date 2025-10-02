import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FileRowComponent } from '../file-row/file-row.component';

interface FileInfo {
  file: File;
  fileName: string;
  fileType: string;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  source: 'direct' | 'folder' | 'zip';
  path?: string;
}

@Component({
  selector: 'app-file-list',template: `
    <div *ngIf="files.length > 0" class="file-list-container">
      <!-- Header -->
      <div class="file-list-header">
        <h3>Selected Files</h3>
        <div class="file-actions">
          <span class="file-count-badge">
            {{ files.length }} file{{ files.length !== 1 ? 's' : '' }}
          </span>
          <button 
            *ngIf="files.length > 0"
            (click)="clearAllFiles()"
            class="clear-button"
            title="Clear All Files">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
            </svg>
          </button>
        </div>
      </div>
      
      <!-- File Table -->
      <div class="file-list">
        <table class="w-full">
          <thead class="file-table-header">
            <tr>
              <th class="file-table-th">File</th>
              <th class="file-table-th">Source</th>
              <th class="file-table-th">Size</th>
              <th class="file-table-th">Status</th>
              <th class="file-table-th text-center">Progress</th>
            </tr>
          </thead>
          <tbody class="file-table-body">
            <app-file-row
              *ngFor="let fileInfo of files; trackBy: trackByFileName"
              [fileInfo]="fileInfo"
              (removeFile)="onRemoveFile($event)">
            </app-file-row>
          </tbody>
        </table>
      </div>
    </div>
  `,
  styleUrls: ['./file-list.component.scss']
})
export class FileListComponent {
  @Input() files: FileInfo[] = [];
  @Output() removeFile = new EventEmitter<FileInfo>();
  @Output() clearAll = new EventEmitter<void>();

  trackByFileName(index: number, fileInfo: FileInfo): string {
    return fileInfo.fileName + fileInfo.source;
  }

  onRemoveFile(fileInfo: FileInfo) {
    this.removeFile.emit(fileInfo);
  }

  clearAllFiles() {
    this.clearAll.emit();
  }
}
