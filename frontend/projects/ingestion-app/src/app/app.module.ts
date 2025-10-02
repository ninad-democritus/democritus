import { NgModule } from '@angular/core';
import { RouterModule } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { AppComponent } from './app.component';
import { routes } from './app.routes';

// Import all feature components
import { UploadComponent } from './upload/upload.component';
import { IngestionStatusComponent } from './ingestion-status/ingestion-status.component';
import { ErDiagramComponent } from './er-diagram/er-diagram.component';
import { SchemaApprovalComponent } from './schema-approval/schema-approval.component';

// Import upload sub-components
import { FileSelectorComponent } from './upload/components/file-selector/file-selector.component';
import { FileListComponent } from './upload/components/file-list/file-list.component';
import { FileRowComponent } from './upload/components/file-row/file-row.component';
import { UploadProgressComponent } from './upload/components/upload-progress/upload-progress.component';

// Import status sub-components
import { ConnectionStatusComponent } from './ingestion-status/components/connection-status/connection-status.component';
import { PipelineProgressComponent } from './ingestion-status/components/pipeline-progress/pipeline-progress.component';
import { StatusSummaryComponent } from './ingestion-status/components/status-summary/status-summary.component';
import { UploadSummaryComponent } from './ingestion-status/components/upload-summary/upload-summary.component';

// Import diagram sub-components
import { ZoomControlsComponent } from './er-diagram/components/zoom-controls/zoom-controls.component';

@NgModule({
  declarations: [
    AppComponent,
    UploadComponent,
    IngestionStatusComponent,
    ErDiagramComponent,
    SchemaApprovalComponent,
    // Upload components
    FileSelectorComponent,
    FileListComponent,
    FileRowComponent,
    UploadProgressComponent,
    // Status components
    ConnectionStatusComponent,
    PipelineProgressComponent,
    StatusSummaryComponent,
    UploadSummaryComponent,
    // Diagram components
    ZoomControlsComponent
  ],
  imports: [
    CommonModule,
    HttpClientModule,
    FormsModule,
    RouterModule.forChild(routes)
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }

