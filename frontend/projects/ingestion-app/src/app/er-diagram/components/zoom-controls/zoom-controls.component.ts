import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-zoom-controls',template: `
    <div class="zoom-controls">
      <button 
        (click)="onZoomIn()"
        class="zoom-btn"
        title="Zoom In"
        [disabled]="zoom >= maxZoom">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7"></path>
        </svg>
      </button>
      
      <span class="zoom-level">{{ Math.round(zoom * 100) }}%</span>
      
      <button 
        (click)="onZoomOut()"
        class="zoom-btn"
        title="Zoom Out"
        [disabled]="zoom <= minZoom">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0M13 10H7"></path>
        </svg>
      </button>
      
      <button 
        (click)="onResetZoom()"
        class="zoom-btn"
        title="Reset Zoom">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
        </svg>
      </button>
      
      <button 
        (click)="onFitToScreen()"
        class="zoom-btn"
        title="Fit to Screen">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"></path>
        </svg>
      </button>
    </div>
  `,
  styleUrls: ['./zoom-controls.component.scss']
})
export class ZoomControlsComponent {
  @Input() zoom = 1;
  @Input() minZoom = 0.25;
  @Input() maxZoom = 4;
  
  @Output() zoomIn = new EventEmitter<void>();
  @Output() zoomOut = new EventEmitter<void>();
  @Output() resetZoom = new EventEmitter<void>();
  @Output() fitToScreen = new EventEmitter<void>();

  Math = Math; // Make Math available in template

  onZoomIn() {
    this.zoomIn.emit();
  }

  onZoomOut() {
    this.zoomOut.emit();
  }

  onResetZoom() {
    this.resetZoom.emit();
  }

  onFitToScreen() {
    this.fitToScreen.emit();
  }
}

