import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-upload-progress',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div *ngIf="isVisible" class="upload-progress-container">
      <!-- Overall Progress -->
      <div class="progress-header">
        <h3 class="progress-title">Upload Progress</h3>
        <span class="progress-percentage">{{ Math.round(progress) }}%</span>
      </div>
      
      <!-- Progress Bar -->
      <div class="progress-bar-container">
        <div class="progress-bar-track">
          <div 
            class="progress-bar-fill"
            [style.width.%]="progress">
          </div>
        </div>
      </div>
      
      <!-- Progress Details -->
      <div class="progress-details">
        <span class="progress-text">
          {{ completedFiles }} of {{ totalFiles }} files uploaded
        </span>
        <span *ngIf="hasErrors" class="error-text">
          {{ errorCount }} error{{ errorCount !== 1 ? 's' : '' }}
        </span>
      </div>
      
      <!-- Action Buttons -->
      <div class="progress-actions">
        <button 
          *ngIf="!isUploading && !isCompleted"
          (click)="startUpload()"
          class="start-upload-button"
          [disabled]="totalFiles === 0">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
          </svg>
          <span>Start Upload & Analysis</span>
        </button>
        
        <button 
          *ngIf="isUploading"
          (click)="cancelUpload()"
          class="cancel-upload-button">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
          <span>Cancel Upload</span>
        </button>
        
        <button 
          *ngIf="isCompleted"
          (click)="proceedToNext()"
          class="proceed-button">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path>
          </svg>
          <span>Proceed to Schema Review</span>
        </button>
      </div>
    </div>
  `,
  styleUrls: ['./upload-progress.component.scss']
})
export class UploadProgressComponent {
  @Input() isVisible = false;
  @Input() isUploading = false;
  @Input() progress = 0;
  @Input() totalFiles = 0;
  @Input() completedFiles = 0;
  @Input() errorCount = 0;

  @Output() uploadStart = new EventEmitter<void>();
  @Output() uploadCancel = new EventEmitter<void>();
  @Output() proceedNext = new EventEmitter<void>();

  Math = Math; // Make Math available in template

  get isCompleted(): boolean {
    return this.completedFiles === this.totalFiles && this.totalFiles > 0 && !this.isUploading;
  }

  get hasErrors(): boolean {
    return this.errorCount > 0;
  }

  startUpload() {
    this.uploadStart.emit();
  }

  cancelUpload() {
    this.uploadCancel.emit();
  }

  proceedToNext() {
    this.proceedNext.emit();
  }
}

