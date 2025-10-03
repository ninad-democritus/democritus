/**
 * Dashboard Grid Component
 * Center panel with gridster2 for arranging charts
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
import { CdkDragDrop } from '@angular/cdk/drag-drop';
import { Subject, takeUntil } from 'rxjs';
import { GridsterConfig, GridsterItem, GridType, DisplayGrid, CompactType } from 'angular-gridster2';
import { ChartDataService } from '../../../../services/chart-data.service';
import { DashboardItem } from '../../../../models/dashboard-item.model';
import { ChartType } from '../../../../models/chart-type.model';

@Component({
  selector: 'app-dashboard-grid',
  templateUrl: './dashboard-grid.component.html',
  styleUrl: './dashboard-grid.component.scss'
})
export class DashboardGridComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  
  dashboardItems: DashboardItem[] = [];
  gridsterOptions: GridsterConfig = {};

  constructor(private chartDataService: ChartDataService) {}

  ngOnInit(): void {
    // Configure gridster
    this.gridsterOptions = {
      gridType: GridType.Fit,
      displayGrid: DisplayGrid.OnDragAndResize,
      pushItems: true,
      swap: false,
      compactType: CompactType.None,
      draggable: {
        enabled: true
      },
      resizable: {
        enabled: true
      },
      minCols: 12,
      maxCols: 12,
      minRows: 1,
      margin: 16,
      outerMargin: true,
      mobileBreakpoint: 640,
      itemChangeCallback: this.onItemChange.bind(this),
      itemResizeCallback: this.onItemResize.bind(this)
    };

    // Subscribe to dashboard items
    this.chartDataService.dashboardItems$
      .pipe(takeUntil(this.destroy$))
      .subscribe(items => {
        this.dashboardItems = items;
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Handle drop from chart library
   */
  onDrop(event: CdkDragDrop<any>): void {
    const chartType: ChartType = event.item.data;
    
    // Calculate drop position in grid coordinates
    const dropX = 0; // TODO: Calculate based on drop position
    const dropY = this.calculateNextY();

    // Create new dashboard item
    const newItem: DashboardItem = {
      id: this.chartDataService.generateId(),
      chartType: chartType,
      x: dropX,
      y: dropY,
      cols: chartType.defaultSize.cols,
      rows: chartType.defaultSize.rows,
      config: {
        title: `New ${chartType.name}`,
        echartsOptions: this.getPlaceholderOptions()
      }
    };

    this.chartDataService.addChart(newItem);
  }

  /**
   * Handle chart selection for AI context
   */
  onChartClick(item: DashboardItem): void {
    const isCurrentlySelected = item.isSelected;
    
    if (isCurrentlySelected) {
      this.chartDataService.selectChart(null); // Deselect
    } else {
      this.chartDataService.selectChart(item.id); // Select
    }
  }

  /**
   * Remove chart from dashboard
   */
  onRemoveChart(item: DashboardItem): void {
    this.chartDataService.removeChart(item.id);
  }

  /**
   * Calculate next Y position for new items
   */
  private calculateNextY(): number {
    if (this.dashboardItems.length === 0) return 0;
    
    const maxY = Math.max(...this.dashboardItems.map(item => item.y + item.rows));
    return maxY;
  }

  /**
   * Gridster item change callback
   */
  private onItemChange(item: DashboardItem): void {
    this.chartDataService.updateChart(item.id, {
      x: item.x,
      y: item.y,
      cols: item.cols,
      rows: item.rows
    });
  }

  /**
   * Gridster item resize callback
   */
  private onItemResize(item: DashboardItem): void {
    // Trigger chart re-render on resize
    this.onItemChange(item);
  }

  /**
   * Get placeholder ECharts options for empty charts
   */
  private getPlaceholderOptions(): any {
    return {
      title: {
        text: 'No Data',
        left: 'center',
        top: 'center',
        textStyle: {
          color: '#94a3b8',
          fontSize: 14
        }
      },
      graphic: {
        type: 'text',
        left: 'center',
        top: '60%',
        style: {
          text: 'Click and ask AI to populate this chart',
          fontSize: 12,
          fill: '#cbd5e1'
        }
      }
    };
  }

  /**
   * Track by function for ngFor
   */
  trackByChartId(index: number, item: DashboardItem): string {
    return item.id;
  }
}

