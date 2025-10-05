/**
 * Chart Widget Component
 * Individual chart display within the grid
 */

import { Component, Input, Output, EventEmitter, OnChanges, SimpleChanges, ChangeDetectorRef } from '@angular/core';
import { DashboardItem } from '../../../../../../models/dashboard-item.model';

@Component({
  selector: 'app-chart-widget',
  templateUrl: './chart-widget.component.html',
  styleUrl: './chart-widget.component.scss'
})
export class ChartWidgetComponent implements OnChanges {
  @Input() dashboardItem!: DashboardItem;
  @Output() chartClick = new EventEmitter<void>();
  @Output() removeChart = new EventEmitter<void>();

  // ECharts instance
  chartInstance: any;

  constructor(private cdr: ChangeDetectorRef) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['dashboardItem']) {
      console.log('[ChartWidget] Dashboard item changed:', {
        chartId: this.dashboardItem.id,
        hasQuery: !!this.dashboardItem.config.naturalLanguageQuery,
        hasTimestamp: !!this.dashboardItem.config.queryTimestamp,
        change: changes['dashboardItem']
      });
      
      // Trigger change detection to update the empty overlay
      this.cdr.detectChanges();
      
      if (this.chartInstance) {
        // Update chart when data changes
        this.updateChart();
      }
    }
  }

  onChartInit(ec: any): void {
    this.chartInstance = ec;
    this.updateChart();
  }

  private updateChart(): void {
    if (this.chartInstance && this.dashboardItem.config.echartsOptions) {
      console.log('[ChartWidget] Updating chart with options:', JSON.stringify(this.dashboardItem.config.echartsOptions, null, 2));
      this.chartInstance.setOption(this.dashboardItem.config.echartsOptions, true);
      this.chartInstance.resize();
    }
  }

  onChartClick(): void {
    this.chartClick.emit();
  }

  onRemove(event: Event): void {
    event.stopPropagation();
    this.removeChart.emit();
  }

  hasData(): boolean {
    // Chart has data if it has a natural language query and a query timestamp
    // This ensures the chart was populated via AI, not just a placeholder
    const hasQuery = !!this.dashboardItem.config.naturalLanguageQuery;
    const hasTimestamp = !!this.dashboardItem.config.queryTimestamp;
    const hasOptions = !!this.dashboardItem.config.echartsOptions;
    const result = hasQuery && hasTimestamp;
    
    console.log('[ChartWidget] hasData check:', {
      chartId: this.dashboardItem.id,
      hasQuery,
      hasTimestamp,
      hasOptions,
      result,
      naturalLanguageQuery: this.dashboardItem.config.naturalLanguageQuery,
      queryTimestamp: this.dashboardItem.config.queryTimestamp,
      configKeys: Object.keys(this.dashboardItem.config)
    });
    
    return result;
  }

  getLastUpdated(): string {
    if (!this.dashboardItem.config.queryTimestamp) {
      return 'Not yet populated';
    }
    const date = new Date(this.dashboardItem.config.queryTimestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  }
}

