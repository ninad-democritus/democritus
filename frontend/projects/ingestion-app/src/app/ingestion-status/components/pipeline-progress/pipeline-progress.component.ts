import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

interface PipelineStage {
  id: string;
  name: string;
  description: string;
}

@Component({
  selector: 'app-pipeline-progress',template: `
    <div class="pipeline-progress-container">
      <!-- Progress Header -->
      <div class="progress-header">
        <h3 class="progress-title">Pipeline Progress</h3>
        <div class="progress-summary">
          {{ getCompletedStages() }} of {{ stages.length }} steps completed
        </div>
      </div>
      
      <!-- Progress Steps -->
      <div class="progress-steps">
        <div 
          *ngFor="let stage of stages; let i = index"
          class="progress-step"
          [class]="getStepClass(stage.id)">
          
          <!-- Step Number/Icon -->
          <div class="step-indicator" [class]="getStepIndicatorClass(stage.id)">
            <!-- Completed Check -->
            <svg *ngIf="getStageStatus(stage.id) === 'COMPLETED'" 
                 class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
            
            <!-- Failed X -->
            <svg *ngIf="getStageStatus(stage.id) === 'FAILED'" 
                 class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
            
            <!-- Loading Spinner -->
            <svg *ngIf="getStageStatus(stage.id) === 'STARTED'" 
                 class="animate-spin w-4 h-4 text-white" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            
            <!-- Step Number -->
            <span *ngIf="getStageStatus(stage.id) === 'PENDING'" class="step-number">{{ i + 1 }}</span>
          </div>
          
          <!-- Step Content -->
          <div class="step-content">
            <div class="step-title">{{ stage.name }}</div>
            <div class="step-description">{{ stage.description }}</div>
            
            <!-- Error Message -->
            <div *ngIf="hasStageError(stage.id)" class="step-error">
              <div class="error-content">
                <svg class="w-4 h-4 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <div class="error-text">
                  <p class="error-label">Error Details:</p>
                  <p class="error-message">{{ getStageErrorMessage(stage.id) }}</p>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Connector Line -->
          <div *ngIf="i < stages.length - 1" class="step-connector" [class]="getConnectorClass(stage.id)"></div>
        </div>
      </div>
    </div>
  `,
  styleUrls: ['./pipeline-progress.component.scss']
})
export class PipelineProgressComponent {
  @Input() stages: PipelineStage[] = [];
  @Input() stageStatuses: { [key: string]: string } = {};
  @Input() stageErrorMessages: { [key: string]: string } = {};

  getStageStatus(stageId: string): string {
    return this.stageStatuses[stageId] || 'PENDING';
  }

  hasStageError(stageId: string): boolean {
    return this.getStageStatus(stageId) === 'FAILED' && !!this.stageErrorMessages[stageId];
  }

  getStageErrorMessage(stageId: string): string {
    return this.stageErrorMessages[stageId] || '';
  }

  getCompletedStages(): number {
    return Object.values(this.stageStatuses).filter(status => status === 'COMPLETED').length;
  }

  getStepClass(stageId: string): string {
    const status = this.getStageStatus(stageId);
    switch (status) {
      case 'COMPLETED': return 'step-completed';
      case 'STARTED': return 'step-active';
      case 'FAILED': return 'step-failed';
      default: return 'step-pending';
    }
  }

  getStepIndicatorClass(stageId: string): string {
    const status = this.getStageStatus(stageId);
    switch (status) {
      case 'COMPLETED': return 'indicator-completed';
      case 'STARTED': return 'indicator-active';
      case 'FAILED': return 'indicator-failed';
      default: return 'indicator-pending';
    }
  }

  getConnectorClass(stageId: string): string {
    const status = this.getStageStatus(stageId);
    return status === 'COMPLETED' ? 'connector-completed' : 'connector-pending';
  }
}

