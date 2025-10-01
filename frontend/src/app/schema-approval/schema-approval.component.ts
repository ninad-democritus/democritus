import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { ErDiagramComponent } from '../er-diagram/er-diagram.component';

interface UnifiedSchema {
  entities: any[];
  relationships: any[];
}

interface AgentWorkflowResponse {
  run_id: string;
  workflow_id: string;
  schema: UnifiedSchema;
  status: string;
  message: string;
}

@Component({
  selector: 'app-schema-approval',
  standalone: true,
  imports: [CommonModule, ErDiagramComponent],
  templateUrl: './schema-approval.component.html',
  styleUrls: ['./schema-approval.component.scss']
})
export class SchemaApprovalComponent implements OnInit, OnDestroy {
  private http = inject(HttpClient);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  jobId: string = '';
  workflowId: string = '';
  schemaReady = false;
  isApproving = false;
  errorMessage: string = '';
  statusMessage: string = 'Initializing...';
  unifiedSchema: UnifiedSchema | null = null;
  private pollingInterval: any;

  ngOnInit() {
    this.route.queryParams.subscribe(params => {
      this.jobId = params['jobId'] || '';
      this.workflowId = params['workflowId'] || '';
      
      if (this.jobId && this.workflowId) {
        this.pollForSchemaStatus();
      } else {
        this.errorMessage = 'Missing job ID or workflow ID. Please start from upload.';
      }
    });
  }

  ngOnDestroy() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
    }
  }

  private pollForSchemaStatus() {
    this.statusMessage = 'Waiting for AI agents to process your data...';
    
    const checkStatus = () => {
      this.http.get<AgentWorkflowResponse>(`/v1/workflows/status/${this.workflowId}`)
        .subscribe({
          next: (response) => {
            console.log('Workflow status:', response);
            
            if (response.status === 'completed' && response.schema) {
              this.unifiedSchema = response.schema;
              this.schemaReady = true;
              this.clearPolling();
            } else if (response.status === 'failed') {
              this.errorMessage = response.message || 'Workflow failed';
              this.clearPolling();
            } else {
              this.statusMessage = response.message || 'Processing...';
            }
          },
          error: (error) => {
            console.error('Error checking workflow status:', error);
            this.errorMessage = 'Failed to check workflow status. Please try again.';
            this.clearPolling();
          }
        });
    };

    // Check immediately, then every 2 seconds
    checkStatus();
    this.pollingInterval = setInterval(checkStatus, 2000);
  }

  private clearPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
  }

  onSchemaChanged(newSchema: UnifiedSchema) {
    this.unifiedSchema = newSchema;
  }

  async approveSchema() {
    if (!this.unifiedSchema) return;

    this.isApproving = true;
    
    try {
      // Start the data ingestion pipeline
      console.log('Starting data ingestion pipeline...');
      const response = await this.http.post<any>('/v1/pipelines/trigger', {
        job_id: this.jobId,
        schema_data: this.unifiedSchema
      }).toPromise();

      console.log('Pipeline started successfully:', response);
      
      const runId = response.pipelineRunId || response.run_id || this.workflowId;
      
      // Navigate to ingestion status page with the run ID
      this.router.navigate(['/ingestion-status'], {
        queryParams: {
          runId: runId,
          jobId: this.jobId,
          workflowId: this.workflowId
        }
      });
      
    } catch (error) {
      console.error('Failed to start ingestion pipeline:', error);
      this.errorMessage = 'Failed to start ingestion pipeline. Please try again.';
      this.isApproving = false;
    }
  }

  clearError() {
    this.errorMessage = '';
    this.isApproving = false;
  }

  goBack() {
    this.router.navigate(['/upload']);
  }
}