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
    // Configure gridster for 24x24 grid
    this.gridsterOptions = {
      gridType: GridType.Fit,
      displayGrid: DisplayGrid.Always,
      pushItems: true,
      swap: false,
      compactType: CompactType.None,
      draggable: {
        enabled: true
      },
      resizable: {
        enabled: true
      },
      minCols: 24,
      maxCols: 24,
      minRows: 24,
      margin: 4,
      outerMargin: false,
      mobileBreakpoint: 640,
      itemChangeCallback: this.onItemChange.bind(this),
      itemResizeCallback: this.onItemResize.bind(this)
    };

    // Subscribe to dashboard items
    this.chartDataService.dashboardItems$
      .pipe(takeUntil(this.destroy$))
      .subscribe(items => {
        console.log('[DashboardGrid] Dashboard items updated:', items.length);
        this.dashboardItems = items;
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Called when drag enters the grid
   */
  onDragEntered(event: any): void {
    console.log('[DashboardGrid] Drag entered grid');
  }

  /**
   * Called when drag exits the grid
   */
  onDragExited(event: any): void {
    console.log('[DashboardGrid] Drag exited grid');
  }

  /**
   * Handle drop from chart library
   * Note: We COPY items from library, not MOVE them
   */
  onDrop(event: CdkDragDrop<any>): void {
    console.log('[DashboardGrid] Drop event received:', {
      previousContainer: event.previousContainer.id,
      currentContainer: event.container.id,
      previousIndex: event.previousIndex,
      currentIndex: event.currentIndex,
      isPointerOverContainer: event.isPointerOverContainer,
      dropPoint: event.dropPoint,
      itemData: event.item.data
    });
    
    // If from different container (library), we COPY the template
    // If same container, we REORDER (but gridster handles that, so we ignore)
    if (event.previousContainer === event.container) {
      console.log('[DashboardGrid] Same container - gridster handles reordering');
      return;
    }

    // Get the chart type template from the dragged item
    const chartType: ChartType = event.item.data;
    if (!chartType) {
      console.warn('[DashboardGrid] No chart type data in drop event');
      return;
    }

    console.log('[DashboardGrid] Creating chart from template:', chartType.name);
    
    // Get gridster element and calculate grid position
    const gridsterEl = event.container.element.nativeElement;
    const rect = gridsterEl.getBoundingClientRect();
    const dropPoint = event.dropPoint;
    
    // Calculate relative position within gridster
    const relativeX = dropPoint.x - rect.left;
    const relativeY = dropPoint.y - rect.top;
    
    // Calculate grid cell size dynamically for Fit type
    const gridWidth = rect.width;
    const gridHeight = rect.height;
    const cellWidth = gridWidth / 24;
    const cellHeight = gridHeight / 24;
    
    // Convert to grid coordinates
    const gridX = Math.floor(relativeX / cellWidth);
    const gridY = Math.floor(relativeY / cellHeight);
    
    // Ensure position is within grid bounds
    const dropX = Math.max(0, Math.min(gridX, 24 - chartType.defaultSize.cols));
    const dropY = Math.max(0, Math.min(gridY, 24 - chartType.defaultSize.rows));
    
    console.log('[DashboardGrid] Position calculated:', {
      dropPoint,
      rect: { width: rect.width, height: rect.height },
      relative: { x: relativeX, y: relativeY },
      cellSize: { width: cellWidth, height: cellHeight },
      gridCoords: { x: gridX, y: gridY },
      finalPosition: { x: dropX, y: dropY }
    });

    // Create new dashboard item (COPY, not move)
    const newItem: DashboardItem = {
      id: this.chartDataService.generateId(),
      chartType: { ...chartType }, // Clone the chart type
      x: dropX,
      y: dropY,
      cols: chartType.defaultSize.cols,
      rows: chartType.defaultSize.rows,
      config: {
        title: `New ${chartType.name}`,
        echartsOptions: this.getPlaceholderOptions()
      }
    };

    // Add to grid (service will emit update)
    this.chartDataService.addChart(newItem);
    console.log('[DashboardGrid] Chart added successfully:', newItem);
    
    // IMPORTANT: Don't modify the source array (chartTypes)
    // This ensures the library item stays in place
  }

  /**
   * Handle chart selection for AI context
   * Always selects the clicked chart (no toggle)
   */
  onChartClick(item: DashboardItem): void {
    // Always select the chart - no toggle behavior
    // This ensures only one chart is selected at a time
    this.chartDataService.selectChart(item.id);
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

