import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { takeUntil } from 'rxjs/operators';
import { DashboardApiService, DashboardViewItem, DashboardScope } from '../../services/dashboard-api.service';
import { BaseComponent } from '../../core/base-component';

@Component({
  selector: 'app-dashboard-list',
  templateUrl: './dashboard-list.component.html',
  styleUrl: './dashboard-list.component.scss'
})
export class DashboardListComponent extends BaseComponent implements OnInit {
  dashboards: DashboardViewItem[] = [];

  // Filter state
  activeScope: DashboardScope = 'all';
  searchQuery = '';

  // UI state
  loading = false;
  error: string | null = null;

  constructor(
    cdr: ChangeDetectorRef,
    private dashboardApi: DashboardApiService,
    private router: Router,
    private route: ActivatedRoute
  ) {
    super(cdr);
    this.router.events.subscribe(event => {
      console.log('Router Event:', event, this.router.routerState.snapshot);
    });

  }

  ngOnInit() {
    this.loadDashboards();
  }

  loadDashboards() {
    this.loading = true;
    this.error = null;

    this.dashboardApi.viewDashboards(this.activeScope, this.searchQuery)
      .pipe(
        this.detectChanges(),
        takeUntil(this.destroy$)
      )
      .subscribe({
        next: (dashboards) => {
          this.dashboards = dashboards || [];
          this.loading = false;
          this.forceChangeDetection();
        },
        error: (error) => {
          this.loading = false;
          this.dashboards = [];
          console.error('Failed to load dashboards:', error);

          if (error.status === 0) {
            this.error = 'Cannot connect to dashboard service. Please ensure the service is running.';
          } else {
            this.error = error.error?.message || 'Failed to load dashboards. Please try again.';
          }

          this.forceChangeDetection();
        }
      });
  }

  onScopeChange(scope: DashboardScope) {
    this.activeScope = scope;
    this.loadDashboards();
  }

  onSearchChange(query: string) {
    this.searchQuery = query;
    this.loadDashboards();
  }

  createNewDashboard() {
    const browserPath = window.location.pathname;
    const basePath = browserPath.includes('/ai-canvas') ? '/ai-canvas' : '';
    // this.router.navigate([`${basePath}/create`]);
    this.router.navigateByUrl(`${basePath}/create`);
  }

  viewDashboard(event: Event, dashboardId: string) {
    event.stopPropagation();
    const browserPath = window.location.pathname;
    const basePath = browserPath.includes('/ai-canvas') ? '/ai-canvas' : '';
    // this.router.navigate([`${basePath}/view`, dashboardId]);
    /* this.router.navigateByUrl(`${basePath}/view/${dashboardId}`); */
    this.router.navigate(['view', dashboardId]);
    // this.router.navigate(['view', dashboardId], { relativeTo: this.route.parent ?? this.route });
  }

  editDashboard(event: Event, dashboardId: string) {
    event.stopPropagation();
    const browserPath = window.location.pathname;
    const basePath = browserPath.includes('/ai-canvas') ? '/ai-canvas' : '';
    // this.router.navigateByUrl(`${basePath}/edit/${dashboardId}`);
    this.router.navigate(['edit',dashboardId]);
  }

  deleteDashboard(event: Event, dashboardId: string) {
    event.stopPropagation();

    if (!confirm('Are you sure you want to delete this dashboard?')) {
      return;
    }

    const userId = this.dashboardApi.getTempUserId();

    this.dashboardApi.deleteDashboard(dashboardId, userId)
      .pipe(
        this.detectChanges(),
        takeUntil(this.destroy$)
      )
      .subscribe({
        next: () => {
          this.loadDashboards();
        },
        error: (error) => {
          console.error('Failed to delete dashboard:', error);
          alert('Failed to delete dashboard. Please try again.');
        }
      });
  }

  getChartIcon(chartType: string): string {
    const icons: Record<string, string> = {
      'bar': 'M3 13h2v7H3v-7zm4-3h2v10H7V10zm4-4h2v14h-2V6zm4 2h2v12h-2V8z',
      'line': 'M3 17l4-4 4 4 6-6 4 4',
      'pie': 'M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 0V3m0 9l6.36 6.36',
      'kpi': 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
      'area': 'M7 21l4-4 4 4 6-6v7H3v-7l4-4z',
      'scatter': 'M5 12h.01M12 12h.01M19 12h.01M6 8h.01M12 8h.01M18 8h.01M6 16h.01M12 16h.01M18 16h.01',
      'table': 'M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z',
      'heatmap': 'M4 5h4v4H4V5zm6 0h4v4h-4V5zm6 0h4v4h-4V5zM4 11h4v4H4v-4zm6 0h4v4h-4v-4zm6 0h4v4h-4v-4z'
    };
    return icons[chartType] || icons['bar'];
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
  }
}
