import { Routes } from '@angular/router';
import { IngestionStatusComponent } from './ingestion-status/ingestion-status.component';
import { UploadComponent } from './upload/upload.component';
import { SchemaApprovalComponent } from './schema-approval/schema-approval.component';

export const routes: Routes = [
  { path: '', component: UploadComponent },
  { path: 'upload', component: UploadComponent },
  { path: 'schema-approval', component: SchemaApprovalComponent },
  { path: 'ingestion-status', component: IngestionStatusComponent },
  { path: '**', redirectTo: '' }
];
