import { Routes } from '@angular/router';
import { DashboardBuilderComponent } from './pages/dashboard-builder/dashboard-builder.component';
import { DashboardListComponent } from './pages/dashboard-list/dashboard-list.component';
import { DashboardViewComponent } from './pages/dashboard-view/dashboard-view.component';

export const routes: Routes = [
  { path: '', component: DashboardListComponent },
  { path: 'dashboards', component: DashboardListComponent },
  { path: 'create', component: DashboardBuilderComponent },
  { path: 'edit/:id', component: DashboardBuilderComponent },
  { path: 'view/:id', component: DashboardViewComponent },
  { path: '**', redirectTo: '' }
];

