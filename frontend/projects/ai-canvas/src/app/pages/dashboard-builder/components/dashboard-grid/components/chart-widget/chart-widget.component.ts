/**
 * Chart Widget Component
 * Individual chart display within the grid
 */

import { Component, Input, Output, EventEmitter, OnChanges, SimpleChanges } from '@angular/core';
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

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['dashboardItem'] && this.chartInstance) {
      // Update chart when data changes
      this.updateChart();
    }
  }

  onChartInit(ec: any): void {
    this.chartInstance = ec;
    this.updateChart();
  }

  private updateChart(): void {
    if (this.chartInstance && this.dashboardItem.config.echartsOptions) {
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
    return !!this.dashboardItem.config.naturalLanguageQuery;
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

