/**
 * Dashboard Builder Component
 * Main container for the three-panel dashboard builder interface
 */

import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { takeUntil } from 'rxjs/operators';
import { ChartDataService } from '../../services/chart-data.service';
import { AIChatService } from '../../services/ai-chat.service';
import { DashboardStateService } from '../../services/dashboard-state.service';
import { DashboardApiService, SaveDashboardRequest } from '../../services/dashboard-api.service';
import { BaseComponent } from '../../core/base-component';
import { DashboardItem } from '../../models/dashboard-item.model';
import { CHART_TYPES, ChartType } from '../../models/chart-type.model';

@Component({
  selector: 'app-dashboard-builder',
  templateUrl: './dashboard-builder.component.html',
  styleUrl: './dashboard-builder.component.scss'
})
export class DashboardBuilderComponent extends BaseComponent implements OnInit, OnDestroy {
  showSaveModal = false;
  editMode = false;
  currentDashboardId?: string;
  isLoadingDashboard = false;

  constructor(
    cdr: ChangeDetectorRef,
    private route: ActivatedRoute,
    private router: Router,
    private chartDataService: ChartDataService,
    private aiChatService: AIChatService,
    private dashboardState: DashboardStateService,
    private dashboardApi: DashboardApiService
  ) {
    super(cdr);
    this.router.events.subscribe(event => {
      console.log('Router Event:', event, this.router.routerState.snapshot);
    });
  }

  ngOnInit() {
    // Check if editing existing dashboard
    this.route.params
      .pipe(
        this.detectChanges(),
        takeUntil(this.destroy$)
      )
      .subscribe(params => {
        const dashboardId = params['id'];
        if (dashboardId) {
          this.loadDashboardForEditing(dashboardId);
        }
      });

    // Listen for save trigger from header with auto change detection
    this.dashboardState.onSaveTriggered()
      .pipe(
        this.detectChanges(), // Auto-triggers CD after emission
        takeUntil(this.destroy$)
      )
      .subscribe(() => {
        this.handleSave();
      });

    // Track changes for unsaved indicator
    this.chartDataService.dashboardItems$
      .pipe(
        takeUntil(this.destroy$)
      )
      .subscribe(items => {
        this.dashboardState.setUnsavedChanges(items.length > 0);
      });
  }

  loadDashboardForEditing(dashboardId: string) {
    this.isLoadingDashboard = true;
    this.editMode = true;
    this.currentDashboardId = dashboardId;
    
    const userId = this.dashboardApi.getTempUserId();
    
    this.dashboardApi.getDashboard(dashboardId, userId)
      .pipe(
        this.detectChanges(),
        takeUntil(this.destroy$)
      )
      .subscribe({
        next: (dashboard) => {
          // Convert to DashboardItem format
          const dashboardItems: DashboardItem[] = dashboard.widgets.map(widget => {
            // Check for hydration errors
            if (widget.chart_config.hydration_error) {
              console.error('Widget hydration failed during edit load:', widget.chart_config.hydration_error);
            }
            
            // Check for hydration metadata
            if (widget.chart_config.hydration_metadata) {
              console.log('Widget hydrated for editing:', {
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
          
          // Load into grid
          this.chartDataService.loadDashboard(dashboardItems);
          
          // Store metadata
          this.dashboardState.setCurrentDashboard({
            id: dashboard.id,
            name: dashboard.name,
            visibility: dashboard.visibility as 'private' | 'public',
            dashboardType: dashboard.dashboard_type as 'static' | 'dynamic'
          });
          
          this.isLoadingDashboard = false;
        },
        error: (error) => {
          console.error('Failed to load dashboard:', error);
          alert('Failed to load dashboard: ' + error.message);
          const browserPath = window.location.pathname;
          const basePath = browserPath.includes('/ai-canvas') ? '/ai-canvas' : '';
          this.router.navigateByUrl(`${basePath}`);
        }
      });
  }

  private getChartType(chartTypeId?: string): ChartType {
    if (!chartTypeId) return CHART_TYPES[0];
    return CHART_TYPES.find(ct => ct.id === chartTypeId) || CHART_TYPES[0];
  }

  override ngOnDestroy() {
    // Clear dashboard and chat when navigating away
    this.chartDataService.clearDashboard();
    this.aiChatService.resetChat();
    this.dashboardState.setUnsavedChanges(false);
    
    // Call parent destroy to clean up subscriptions
    super.ngOnDestroy();
  }

  handleSave() {
    if (this.editMode && this.currentDashboardId) {
      // In edit mode: directly update dashboard without modal
      this.saveExistingDashboard();
    } else {
      // In create mode: show modal to get dashboard details
      this.openSaveModal();
    }
  }

  openSaveModal() {
    this.showSaveModal = true;
    this.forceChangeDetection(); // Centralized CD
  }

  closeSaveModal() {
    this.showSaveModal = false;
    this.forceChangeDetection(); // Centralized CD
  }

  saveExistingDashboard() {
    const currentDashboard = this.dashboardState.getCurrentDashboard();
    if (!currentDashboard || !this.currentDashboardId) {
      console.error('No dashboard metadata available for update');
      return;
    }

    const dashboardItems = this.chartDataService.getDashboardItems();
    
    const updateRequest = {
      name: currentDashboard.name,
      visibility: currentDashboard.visibility,
      widgets: dashboardItems.map(item => ({
        grid_x: item.x,
        grid_y: item.y,
        grid_cols: item.cols,
        grid_rows: item.rows,
        chart_config: item.config,
        metadata: {
          ...item.config.queryMetadata,
          chartType: item.chartType.id  // Add the actual selected chart type
        },
        nl_query: item.config.naturalLanguageQuery
      }))
    };

    this.dashboardApi.updateDashboard(
      this.currentDashboardId,
      this.dashboardApi.getTempUserId(),
      updateRequest
    )
    .pipe(
      this.detectChanges(),
      takeUntil(this.destroy$)
    )
    .subscribe({
      next: () => {
        console.log('Dashboard updated successfully');
        this.dashboardState.setUnsavedChanges(false);
        alert('Dashboard updated successfully!');
        /* const browserPath = window.location.pathname;
        const basePath = browserPath.includes('/ai-canvas') ? '/ai-canvas' : '';
        this.router.navigate([`${basePath}`]); */
      },
      error: (error) => {
        console.error('Failed to update dashboard:', error);
        alert('Failed to update dashboard: ' + error.message);
      }
    });
  }

  onSaveDashboard(formData: any) {
    // This is only called from modal in CREATE mode
    const dashboardItems = this.chartDataService.getDashboardItems();
    
    const request: SaveDashboardRequest = {
      name: formData.name,
      owner_id: this.dashboardApi.getTempUserId(),
      visibility: formData.visibility,
      dashboard_type: formData.dashboardType,
      widgets: dashboardItems.map(item => ({
        grid_x: item.x,
        grid_y: item.y,
        grid_cols: item.cols,
        grid_rows: item.rows,
        chart_config: item.config,
        metadata: {
          ...item.config.queryMetadata,
          chartType: item.chartType.id  // Add the actual selected chart type
        },
        nl_query: item.config.naturalLanguageQuery
      }))
    };

    this.dashboardApi.createDashboard(request)
      .pipe(
        this.detectChanges(),
        takeUntil(this.destroy$)
      )
      .subscribe({
        next: () => {
          console.log('Dashboard created successfully');
          this.dashboardState.setUnsavedChanges(false);
          this.chartDataService.clearDashboard();
          this.aiChatService.resetChat();
          this.closeSaveModal();
          alert('Dashboard saved successfully!');
          /* const browserPath = window.location.pathname;
          const basePath = browserPath.includes('/ai-canvas') ? '/ai-canvas' : '';
          this.router.navigate([`${basePath}`]); */
        },
        error: (error) => {
          console.error('Failed to save dashboard:', error);
          alert('Failed to save dashboard: ' + error.message);
        }
      });
  }
}

