import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { takeUntil } from 'rxjs/operators';
import { BaseComponent } from '../../core/base-component';
import { DashboardApiService, DashboardResponse } from '../../services/dashboard-api.service';
import { DashboardItem } from '../../models/dashboard-item.model';
import { CHART_TYPES, ChartType } from '../../models/chart-type.model';
import { GridsterConfig, GridType, DisplayGrid, CompactType } from 'angular-gridster2';

@Component({
  selector: 'app-dashboard-view',
  templateUrl: './dashboard-view.component.html',
  styleUrls: ['./dashboard-view.component.scss']
})
export class DashboardViewComponent extends BaseComponent implements OnInit {
  dashboard: DashboardResponse | null = null;
  dashboardItems: DashboardItem[] = [];
  loading = false;
  error: string | null = null;
  
  gridOptions: GridsterConfig = {
    gridType: GridType.Fit,
    displayGrid: DisplayGrid.Always,
    pushItems: true,
    swap: false,
    compactType: CompactType.None,
    draggable: {
      enabled: false
    },
    resizable: {
      enabled: false
    },
    minCols: 24,
    maxCols: 24,
    minRows: 24,
    margin: 4,
    outerMargin: false,
    mobileBreakpoint: 640
  };

  constructor(
    cdr: ChangeDetectorRef,
    private route: ActivatedRoute,
    private router: Router,
    private dashboardApi: DashboardApiService
  ) {
    super(cdr);
    this.router.events.subscribe(event => {
      console.log('Router Event:', event, this.router.routerState.snapshot);
    });
  }

  ngOnInit() {
    this.route.params
      .pipe(
        this.detectChanges(),
        takeUntil(this.destroy$)
      )
      .subscribe(params => {
        const dashboardId = params['id'];
        if (dashboardId) {
          this.loadDashboard(dashboardId);
        } else {
          this.error = 'No dashboard ID provided';
          this.forceChangeDetection();
        }
      });
  }

  loadDashboard(dashboardId: string) {
    this.loading = true;
    this.error = null;
    
    const userId = this.dashboardApi.getTempUserId();
    
    this.dashboardApi.getDashboard(dashboardId, userId)
      .pipe(
        this.detectChanges(),
        takeUntil(this.destroy$)
      )
      .subscribe({
        next: (dashboard) => {
          this.dashboard = dashboard;
          
          // Convert to DashboardItem format
          this.dashboardItems = dashboard.widgets.map(widget => {
            // Check for hydration errors
            if (widget.chart_config.hydration_error) {
              console.error('Widget hydration failed:', widget.chart_config.hydration_error);
            }
            
            // Check for hydration metadata
            if (widget.chart_config.hydration_metadata) {
              console.log('Widget hydrated:', {
                widgetId: widget.id,
                hydrated_at: widget.chart_config.hydration_metadata.hydrated_at,
                row_count: widget.chart_config.hydration_metadata.row_count
              });
            }
            
            return {
              id: widget.id,
              chartType: this.getChartType(widget.metadata?.chartType),
              x: widget.grid_x,
              y: widget.grid_y,
              cols: widget.grid_cols,
              rows: widget.grid_rows,
              config: {
                title: widget.chart_config.title || 'Untitled Chart',
                echartsOptions: widget.chart_config.echartsOptions,
                naturalLanguageQuery: widget.nl_query,
                queryTimestamp: new Date(widget.created_at),
                queryMetadata: widget.metadata,
                // Pass error info to widget component
                hydration_error: widget.chart_config.hydration_error,
                hydration_metadata: widget.chart_config.hydration_metadata
              }
            };
          });
          
          this.loading = false;
          this.forceChangeDetection();
        },
        error: (error) => {
          console.error('Failed to load dashboard:', error);
          this.error = error.error?.message || 'Failed to load dashboard';
          this.loading = false;
          this.forceChangeDetection();
        }
      });
  }

  private getChartType(chartTypeId?: string): ChartType {
    if (!chartTypeId) return CHART_TYPES[0];
    return CHART_TYPES.find(ct => ct.id === chartTypeId) || CHART_TYPES[0];
  }

  goBack() {
    const browserPath = window.location.pathname;
    const basePath = browserPath.includes('/ai-canvas') ? '/ai-canvas' : '';
    this.router.navigateByUrl(`${basePath}`);
  }

  editDashboard() {
    if (this.dashboard) {
      const browserPath = window.location.pathname;
      const basePath = browserPath.includes('/ai-canvas') ? '/ai-canvas' : '';
      this.router.navigateByUrl(`${basePath}/edit/${this.dashboard.id}`);
    }
  }
}

