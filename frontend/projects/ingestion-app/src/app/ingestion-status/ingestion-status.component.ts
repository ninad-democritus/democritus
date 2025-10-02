import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

// Import new modular components
import { ConnectionStatusComponent } from './components/connection-status/connection-status.component';
import { PipelineProgressComponent } from './components/pipeline-progress/pipeline-progress.component';
import { StatusSummaryComponent } from './components/status-summary/status-summary.component';
import { UploadSummaryComponent } from './components/upload-summary/upload-summary.component';
import { API_CONFIG } from '../config/api.config';

interface StatusUpdate {
  type: string;
  run_id: string;
  stage: string;
  status: string; // STARTED, COMPLETED, FAILED
  message: string;
  timestamp: string;
  data?: any;
}

interface PipelineStage {
  id: string;
  name: string;
  description: string;
}

interface FileSummary {
  file_name: string;
  record_count: number;
  processing_time: number;
  processed_at: string;
}

interface PipelineStatus {
  run_id: string;
  status: string;
  step: string;
  message: string;
  file_summary: FileSummary[];
  total_records: number;
  total_files: number;
  duration: string;
  started_at: string;
  completed_at?: string;
  error?: string;
  timestamp: string;
}

interface UploadStats {
  total_files: number;
  total_records: number;
  file_summary: FileSummary[];
}

@Component({
  selector: 'app-ingestion-status',templateUrl: './ingestion-status.component.html',
  styleUrls: ['./ingestion-status.component.scss']
})
export class IngestionStatusComponent implements OnInit, OnDestroy {
  // Core state
  runId: string | null = null;
  websocket: WebSocket | null = null;
  connectionStatus = false;
  isConnecting = false;
  
  // Pipeline state
  pipelineStages: PipelineStage[] = [];
  stageStatuses: { [key: string]: string } = {};
  stageErrorMessages: { [key: string]: string } = {};
  
  pipelineStatus: PipelineStatus = {
    run_id: '',
    status: 'pending',
    step: 'initializing',
    message: 'Initializing pipeline...',
    file_summary: [],
    total_records: 0,
    total_files: 0,
    duration: '0s',
    started_at: '',
    timestamp: ''
  };

  uploadStats: UploadStats = {
    total_files: 0,
    total_records: 0,
    file_summary: []
  };

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private http: HttpClient
  ) {}

  async ngOnInit() {
    // Get run ID from route parameters, query parameters, or session
    this.runId = this.route.snapshot.params['runId'] || 
                 this.route.snapshot.queryParams['runId'] || 
                 this.route.snapshot.queryParams['jobId'] || 
                 this.route.snapshot.queryParams['workflowId'] || 
                 sessionStorage.getItem('workflowRunId');
    
    if (this.runId) {
      console.log('Initializing status component with runId:', this.runId);
      await this.loadPipelineStages();
      this.initializeWebSocket();
    } else {
      console.warn('No run ID provided, redirecting to upload');
      const browserPath = window.location.pathname;
      const basePath = browserPath.includes('/ingestion') ? '/ingestion' : '';
      this.router.navigate([`${basePath}`]);
    }
  }

  ngOnDestroy() {
    if (this.websocket) {
      this.websocket.close();
    }
  }

  // WebSocket Management
  private initializeWebSocket() {
    if (!this.runId) return;

    this.isConnecting = true;
    const wsUrl = `ws://localhost/ws/v1/pipelines/status/${this.runId}`;
    console.log('Connecting to WebSocket:', wsUrl);

    try {
      this.websocket = new WebSocket(wsUrl);
      
      this.websocket.onopen = () => {
        console.log('✅ WebSocket connected');
        this.connectionStatus = true;
        this.isConnecting = false;
      };

      this.websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('📨 WebSocket message received:', data);
          
          if (data.type === 'status_update' && data.run_id === this.runId) {
            console.log(`🔄 Processing status update for stage: ${data.stage}, status: ${data.status}, message: ${data.message}`);
            this.updatePipelineStatus(data);
          } else if (data.type === 'connection_established') {
            console.log('✅ WebSocket connection established');
          } else {
            console.log('⚠️ Received unexpected message type or run_id mismatch:', data);
          }
        } catch (error) {
          console.error('❌ Error parsing WebSocket message:', error, 'Raw message:', event.data);
        }
      };

      this.websocket.onclose = () => {
        console.log('WebSocket disconnected');
        this.connectionStatus = false;
        this.isConnecting = false;
      };

      this.websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.connectionStatus = false;
        this.isConnecting = false;
      };

    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      this.connectionStatus = false;
      this.isConnecting = false;
    }
  }

  onRetryConnection() {
    if (this.websocket) {
      this.websocket.close();
    }
    
    setTimeout(() => {
      this.initializeWebSocket();
    }, 1000);
  }

  // Pipeline Management
  private async loadPipelineStages() {
    try {
      const response = await this.http.get<PipelineStage[]>(`${API_CONFIG.baseUrl}/v1/pipelines/stages`).toPromise();
      this.pipelineStages = response || this.getDefaultStages();
      
      // Initialize stage statuses
      this.pipelineStages.forEach(stage => {
        this.stageStatuses[stage.id] = 'PENDING';
      });
    } catch (error) {
      console.error('Failed to load pipeline stages:', error);
      this.pipelineStages = this.getDefaultStages();
    }
  }

  private getDefaultStages(): PipelineStage[] {
    return [
      { id: 'file_discovery', name: 'File Discovery', description: 'Discovering and validating uploaded files' },
      { id: 'file_validation', name: 'File Validation', description: 'Validating file formats and accessibility' },
      { id: 'schema_validation', name: 'Schema Validation', description: 'Validating and creating data schemas' },
      { id: 'entity_mapping', name: 'Entity Mapping', description: 'Mapping files to entities' },
      { id: 'data_transformation', name: 'Data Transformation', description: 'Transforming and cleaning data' },
      { id: 'table_setup', name: 'Table Setup', description: 'Creating Iceberg tables and schemas' },
      { id: 'data_ingestion', name: 'Data Ingestion', description: 'Writing data to Iceberg tables' },
      { id: 'metadata_storage', name: 'Metadata Storage', description: 'Storing schema metadata' },
      { id: 'file_cleanup', name: 'File Cleanup', description: 'Cleaning up temporary files' }
    ];
  }

  private updatePipelineStatus(update: StatusUpdate) {
    // Handle special pipeline completion/failure stages
    if (update.stage === 'pipeline_complete') {
      this.pipelineStatus.status = 'completed';
      this.pipelineStatus.step = 'completed';
      this.pipelineStatus.message = update.message;
      this.pipelineStatus.timestamp = update.timestamp;
      this.pipelineStatus.completed_at = update.timestamp;
    } else if (update.stage === 'pipeline_failed') {
      this.pipelineStatus.status = 'failed';
      this.pipelineStatus.step = 'failed';
      this.pipelineStatus.message = update.message;
      this.pipelineStatus.timestamp = update.timestamp;
      this.pipelineStatus.error = update.message;
    } else {
      // Update overall status for regular stages
      this.pipelineStatus.status = update.status === 'FAILED' ? 'failed' : 
                                   update.status === 'COMPLETED' ? this.getOverallStatus() : 'running';
      this.pipelineStatus.step = update.stage;
      this.pipelineStatus.message = update.message;
      this.pipelineStatus.timestamp = update.timestamp;
    }
    
    // Update stage-specific status
    this.mapAndUpdateStageStatus(update.stage, update.status, update.message);
    
    // Update stats from data
    if (update.data) {
      if (update.data.file_summary) {
        this.uploadStats.file_summary = update.data.file_summary;
      }
      if (update.data.total_records) {
        this.uploadStats.total_records = update.data.total_records;
      }
      if (update.data.total_files) {
        this.uploadStats.total_files = update.data.total_files;
      }
      if (update.data.duration) {
        this.pipelineStatus.duration = update.data.duration;
      }
    }
  }

  private mapAndUpdateStageStatus(backendStage: string, status: string, message?: string) {
    console.log(`🔄 Stage mapping: ${backendStage} -> ${status}${message ? ` (${message})` : ''}`);
    
    // Map backend stage names to frontend stage IDs
    const stageMapping: { [key: string]: string[] } = {
      // Direct stage mappings
      'file_discovery': ['file_discovery'],
      'file_discovery_complete': ['file_discovery'],
      'file_validation': ['file_validation'],
      'file_validation_complete': ['file_validation'],
      'schema_validation': ['schema_validation'],
      'schema_validation_complete': ['schema_validation'],
      'entity_mapping': ['entity_mapping'],
      'entity_mapping_complete': ['entity_mapping'],
      'data_transformation': ['data_transformation'],
      'data_transformation_complete': ['data_transformation'],
      'table_setup': ['table_setup'],
      'table_setup_complete': ['table_setup'],
      'table_setup_failed': ['table_setup'],
      'data_ingestion': ['data_ingestion'],
      'data_ingestion_complete': ['data_ingestion'],
      'metadata_storage': ['metadata_storage'],
      'metadata_storage_complete': ['metadata_storage'],
      'metadata_storage_failed': ['metadata_storage'],
      'file_cleanup': ['file_cleanup'],
      'file_cleanup_complete': ['file_cleanup'],
      'file_cleanup_failed': ['file_cleanup'],
      
      // Add missing cleanup sub-stages mappings
      'cleanup_preparing': ['file_cleanup'],
      'cleanup_files_found': ['file_cleanup'],
      'cleanup_files_deleted': ['file_cleanup'], 
      'cleanup_completed': ['file_cleanup'],
      
      // Legacy mappings for backwards compatibility
      'data_processing': ['data_transformation'],
      'data_processing_complete': ['data_transformation'],
      'iceberg_metadata': ['table_setup'],
      'iceberg_ingestion': ['data_ingestion'],
      
      // Handle failure stages
      'iceberg_failed': ['table_setup', 'data_ingestion'],
      'pipeline_failed': [], // This affects overall status, not individual stages
      'pipeline_complete': [] // This affects overall status, not individual stages
    };

    const targetStages = stageMapping[backendStage] || [backendStage];
    
    if (targetStages.length === 0) {
      console.log(`⚠️ No stage mapping found for backend stage: ${backendStage}`);
    }
    
    // Update the status for mapped stages
    targetStages.forEach(stageId => {
      if (this.stageStatuses.hasOwnProperty(stageId)) {
        const oldStatus = this.stageStatuses[stageId];
        
        // Special logic for different backend stage patterns
        let newStatus = status;
        
        // For cleanup sub-stages, if any are STARTED, mark main stage as STARTED
        // For cleanup completion stages, only mark as COMPLETED if it's the final completion
        if (backendStage.startsWith('cleanup_') && stageId === 'file_cleanup') {
          if (status === 'STARTED') {
            // Any cleanup sub-stage starting means file_cleanup is active
            newStatus = 'STARTED';
          } else if (backendStage === 'cleanup_completed' || backendStage === 'file_cleanup_complete') {
            // Only these stages mark file_cleanup as complete
            newStatus = 'COMPLETED';
          } else {
            // Don't change status for intermediate cleanup stages
            newStatus = oldStatus === 'PENDING' ? 'STARTED' : oldStatus;
          }
        }
        
        this.stageStatuses[stageId] = newStatus;
        console.log(`✅ Stage ${stageId}: ${oldStatus} -> ${newStatus} (from ${backendStage})`);
        
        // Store error message if status is FAILED and message is provided
        if (newStatus === 'FAILED' && message) {
          this.stageErrorMessages[stageId] = message;
        } else if (newStatus !== 'FAILED') {
          // Clear error message if stage is no longer failed
          delete this.stageErrorMessages[stageId];
        }
      } else {
        console.log(`⚠️ Frontend stage ${stageId} not found in stageStatuses`);
      }
    });

    // Special handling for failure cases
    if (status === 'FAILED') {
      if (backendStage === 'iceberg_failed') {
        // Mark table setup and data ingestion as failed
        this.stageStatuses['table_setup'] = 'FAILED';
        this.stageStatuses['data_ingestion'] = 'FAILED';
        // Also mark metadata_storage as failed since it depends on iceberg
        this.stageStatuses['metadata_storage'] = 'FAILED';
        
        // Store error messages for failed stages
        if (message) {
          this.stageErrorMessages['table_setup'] = message;
          this.stageErrorMessages['data_ingestion'] = message;
          this.stageErrorMessages['metadata_storage'] = 'Failed due to Iceberg error';
        }
      } else if (backendStage === 'pipeline_failed') {
        // Mark any remaining STARTED stages as FAILED and identify the specific failed stage
        Object.keys(this.stageStatuses).forEach(stageId => {
          if (this.stageStatuses[stageId] === 'STARTED') {
            this.stageStatuses[stageId] = 'FAILED';
            if (message) {
              this.stageErrorMessages[stageId] = message;
            }
          }
        });
        
        // If we can identify the specific stage that failed from the message, mark it
        if (message) {
          const lowerMessage = message.toLowerCase();
          if (lowerMessage.includes('table') || lowerMessage.includes('iceberg')) {
            this.stageStatuses['table_setup'] = 'FAILED';
            this.stageErrorMessages['table_setup'] = message;
          } else if (lowerMessage.includes('ingestion') || lowerMessage.includes('write')) {
            this.stageStatuses['data_ingestion'] = 'FAILED';
            this.stageErrorMessages['data_ingestion'] = message;
          } else if (lowerMessage.includes('metadata')) {
            this.stageStatuses['metadata_storage'] = 'FAILED';
            this.stageErrorMessages['metadata_storage'] = message;
          } else if (lowerMessage.includes('file') && lowerMessage.includes('discovery')) {
            this.stageStatuses['file_discovery'] = 'FAILED';
            this.stageErrorMessages['file_discovery'] = message;
          } else if (lowerMessage.includes('validation')) {
            this.stageStatuses['schema_validation'] = 'FAILED';
            this.stageErrorMessages['schema_validation'] = message;
          } else if (lowerMessage.includes('transformation') || lowerMessage.includes('transform')) {
            this.stageStatuses['data_transformation'] = 'FAILED';
            this.stageErrorMessages['data_transformation'] = message;
          }
        }
      }
    }
  }

  private getOverallStatus(): string {
    const statuses = Object.values(this.stageStatuses);
    
    // Check for failure first
    if (statuses.some(status => status === 'FAILED')) {
      return 'failed';
    }
    
    // Check if any stages are currently running
    if (statuses.some(status => status === 'STARTED')) {
      return 'running';
    }
    
    // Count completed stages
    const completedCount = statuses.filter(status => status === 'COMPLETED').length;
    const totalStages = statuses.length;
    
    // If all stages are completed, mark as completed
    if (completedCount === totalStages) {
      return 'completed';
    }
    
    // If some stages are completed but not all, still running
    if (completedCount > 0) {
      return 'running';
    }
    
    // Default to pending
    return 'pending';
  }

  // Navigation
  goBack() {
    const browserPath = window.location.pathname;
    const basePath = browserPath.includes('/ingestion') ? '/ingestion' : '';
    this.router.navigate([`${basePath}/schema-approval`]);
  }

  proceedToNext() {
    // Navigate to next step or dashboard
    console.log('Pipeline completed, proceeding to next step...');
    const browserPath = window.location.pathname;
    const basePath = browserPath.includes('/ingestion') ? '/ingestion' : '';
    this.router.navigate([`${basePath}`]);
  }
}