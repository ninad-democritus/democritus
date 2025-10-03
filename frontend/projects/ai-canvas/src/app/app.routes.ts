import { Routes } from '@angular/router';
import { DashboardBuilderComponent } from './pages/dashboard-builder/dashboard-builder.component';

export const routes: Routes = [
  { path: '', component: DashboardBuilderComponent },
  { path: 'dashboard-builder', component: DashboardBuilderComponent },
  { path: '**', redirectTo: '' }
];

