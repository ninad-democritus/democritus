import { Component, inject, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router, ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';

// Import new modular components
import { FileSelectorComponent } from './components/file-selector/file-selector.component';
import { FileListComponent } from './components/file-list/file-list.component';
import { FileRowComponent } from './components/file-row/file-row.component';
import { UploadProgressComponent } from './components/upload-progress/upload-progress.component';

interface FileInfo {
  file: File;
  fileName: string;
  fileType: string;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  source: 'direct' | 'folder' | 'zip';
  path?: string;
}

@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [
    CommonModule, 
    FileSelectorComponent, 
    FileListComponent, 
    FileRowComponent, 
    UploadProgressComponent
  ],
  templateUrl: './upload.component.html',
  styleUrls: ['./upload.component.scss']
})
export class UploadComponent implements OnInit {
  private http = inject(HttpClient);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  // State Management
  selectedFiles: FileInfo[] = [];
  isUploading = false;
  uploadProgress = 0;

  ngOnInit() {
    // Check if we have status-related query parameters that should redirect to status page
    // Only redirect if we're actually on the root route and not already navigating
    this.route.queryParams.subscribe(params => {
      const jobId = params['jobId'];
      const workflowId = params['workflowId'];
      const runId = params['runId'];
      
      // Only redirect if we have status params and we're on the root route
      if ((jobId || workflowId || runId) && this.router.url.startsWith('/?')) {
        // Use runId first, then fallback to jobId or workflowId
        const statusRunId = runId || jobId || workflowId;
        console.log('Upload component: Redirecting to status page with runId:', statusRunId);
        this.router.navigate(['/ingestion-status'], { 
          queryParams: { runId: statusRunId },
          replaceUrl: true  // Replace the current URL in history
        });
      }
    });
  }

  // Event Handlers for File Selector
  onFilesSelected(files: FileInfo[]) {
    this.selectedFiles.push(...files);
  }

  // Event Handlers for File List
  onRemoveFile(fileInfo: FileInfo) {
    const index = this.selectedFiles.indexOf(fileInfo);
    if (index > -1) {
      this.selectedFiles.splice(index, 1);
    }
  }

  onClearAllFiles() {
    this.selectedFiles = [];
  }

  // Event Handlers for Upload Progress
  onStartUpload() {
    this.startUpload();
  }

  onCancelUpload() {
    this.isUploading = false;
    // Reset any files that are still uploading back to pending
    this.selectedFiles.forEach(file => {
      if (file.status === 'uploading') {
        file.status = 'pending';
      }
    });
    this.uploadProgress = 0;
  }

  onProceedNext() {
    this.proceedToSchemaApproval();
  }

  // Upload Logic
  async startUpload() {
    if (this.selectedFiles.length === 0 || this.isUploading) return;

    this.isUploading = true;
    this.uploadProgress = 0;

    try {
      // Step 1: Get batch upload URLs
      console.log('Getting batch upload URLs...');
      const batchResponse = await this.http.post<any>('/v1/files/batch-upload-urls', {
        files: this.selectedFiles.map(f => ({
          fileName: f.fileName,
          fileType: f.fileType
        }))
      }).toPromise();

      if (!batchResponse.jobId || !batchResponse.uploads) {
        throw new Error('Failed to get batch upload URLs');
      }

      console.log('Got batch upload URLs for job:', batchResponse.jobId);

      // Step 2: Upload all files to their presigned URLs
      const totalFiles = this.selectedFiles.length;
      let completedFiles = 0;

      for (let i = 0; i < this.selectedFiles.length; i++) {
        const fileInfo = this.selectedFiles[i];
        const uploadInfo = batchResponse.uploads[i];
        
        if (!this.isUploading) break; // Check for cancellation

        fileInfo.status = 'uploading';
        
        try {
          await this.uploadFileToPresignedUrl(fileInfo, uploadInfo.uploadUrl);
          fileInfo.status = 'completed';
          completedFiles++;
        } catch (error) {
          console.error('Error uploading file:', fileInfo.fileName, error);
          fileInfo.status = 'error';
        }

        this.uploadProgress = (completedFiles / totalFiles) * 100;
      }

      if (this.isUploading && completedFiles === totalFiles) {
        console.log('All files uploaded successfully');
        await this.triggerWorkflow(batchResponse.jobId);
      }

    } catch (error) {
      console.error('Upload process failed:', error);
      alert('Upload failed. Please try again.');
    } finally {
      this.isUploading = false;
    }
  }

  private async uploadFileToPresignedUrl(fileInfo: FileInfo, uploadUrl: string): Promise<void> {
    return new Promise((resolve, reject) => {
      console.log(`Uploading ${fileInfo.fileName} to presigned URL`);
      this.http.put(uploadUrl, fileInfo.file, {
        headers: {
          'Content-Type': fileInfo.file.type || 'application/octet-stream'
        }
      }).subscribe({
        next: (response) => {
          console.log('File uploaded successfully:', fileInfo.fileName);
          resolve();
        },
        error: (error) => {
          console.error('File upload error:', fileInfo.fileName, error);
          reject(error);
        }
      });
    });
  }

  private async triggerWorkflow(jobId: string): Promise<void> {
    try {
      console.log('Triggering agentic workflow for job:', jobId);
      
      const response = await this.http.post<any>('/v1/workflows/start-job', {
        jobId: jobId,
        sourceType: 'upload'
      }).toPromise();

      console.log('Workflow triggered successfully:', response);
      
      if (response?.workflowId) {
        // Store the workflow run ID for tracking
        sessionStorage.setItem('workflowRunId', response.workflowId);
        sessionStorage.setItem('jobId', jobId);
      }
      
    } catch (error) {
      console.error('Failed to trigger workflow:', error);
      // Don't block progression - user can proceed to schema approval
    }
  }

  private proceedToSchemaApproval(): void {
    console.log('Proceeding to schema approval...');
    const jobId = sessionStorage.getItem('jobId');
    const workflowId = sessionStorage.getItem('workflowRunId');
    
    if (jobId && workflowId) {
      this.router.navigate(['/schema-approval'], {
        queryParams: {
          jobId: jobId,
          workflowId: workflowId
        }
      });
    } else {
      // Fallback navigation without parameters
      this.router.navigate(['/schema-approval']);
    }
  }

  // Computed Properties for Template
  get completedFiles(): number {
    return this.selectedFiles.filter(f => f.status === 'completed').length;
  }

  get errorCount(): number {
    return this.selectedFiles.filter(f => f.status === 'error').length;
  }

  get totalFiles(): number {
    return this.selectedFiles.length;
  }

  get hasFiles(): boolean {
    return this.selectedFiles.length > 0;
  }

  get isCompleted(): boolean {
    return this.completedFiles === this.totalFiles && this.totalFiles > 0 && !this.isUploading;
  }
}