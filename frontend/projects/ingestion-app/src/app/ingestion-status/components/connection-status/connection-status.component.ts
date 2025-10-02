import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-connection-status',template: `
    <div class="connection-status-container">
      <!-- Connection Status Badge -->
      <div class="connection-badge" [class]="getConnectionClass()">
        <div class="connection-dot" [class]="getConnectionDotClass()"></div>
        <span class="connection-text">{{ getConnectionText() }}</span>
      </div>
      
      <!-- Retry Button (when disconnected) -->
      <button 
        *ngIf="!isConnected"
        (click)="onRetryConnection()"
        class="retry-button"
        title="Retry Connection">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
        </svg>
      </button>
    </div>
  `,
  styleUrls: ['./connection-status.component.scss']
})
export class ConnectionStatusComponent {
  @Input() isConnected = false;
  @Input() isConnecting = false;
  @Output() retryConnection = new EventEmitter<void>();

  onRetryConnection() {
    this.retryConnection.emit();
  }

  getConnectionClass(): string {
    if (this.isConnecting) return 'connection-badge-connecting';
    return this.isConnected ? 'connection-badge-connected' : 'connection-badge-disconnected';
  }

  getConnectionDotClass(): string {
    if (this.isConnecting) return 'connection-dot-connecting';
    return this.isConnected ? 'connection-dot-connected' : 'connection-dot-disconnected';
  }

  getConnectionText(): string {
    if (this.isConnecting) return 'Connecting...';
    return this.isConnected ? 'Connected' : 'Disconnected';
  }
}

