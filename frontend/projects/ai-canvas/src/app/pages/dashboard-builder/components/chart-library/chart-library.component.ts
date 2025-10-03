/**
 * Chart Library Component
 * Left panel displaying draggable chart types
 */

import { Component } from '@angular/core';
import { CdkDragStart } from '@angular/cdk/drag-drop';
import { CHART_TYPES, ChartType } from '../../../../models/chart-type.model';

@Component({
  selector: 'app-chart-library',
  templateUrl: './chart-library.component.html',
  styleUrl: './chart-library.component.scss'
})
export class ChartLibraryComponent {
  chartTypes = CHART_TYPES;

  // Track which chart is being dragged
  draggedChartType: ChartType | null = null;

  onDragStarted(event: CdkDragStart, chartType: ChartType): void {
    this.draggedChartType = chartType;
  }

  onDragEnded(): void {
    // Small delay to allow drop event to complete
    setTimeout(() => {
      this.draggedChartType = null;
    }, 100);
  }

  getChartIcon(iconName: string): string {
    const icons: Record<string, string> = {
      'chart-bar': 'M3 3v18h18M7 12h2v7H7v-7zm4-5h2v12h-2V7zm4 7h2v5h-2v-5z',
      'chart-line': 'M3 21l7-7 5 5 7-7M16 8l-5 5-5-5-3 3',
      'chart-pie': 'M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm0 18c-4.411 0-8-3.589-8-8s3.589-8 8-8',
      'chart-area': 'M3 21V3l7 5 5-3 7 3v13H3z',
      'chart-scatter': 'M5 9a2 2 0 100-4 2 2 0 000 4zM11 15a2 2 0 100-4 2 2 0 000 4zM19 11a2 2 0 100-4 2 2 0 000 4z',
      'table': 'M4 6h16v2H4V6zm0 5h16v2H4v-2zm0 5h16v2H4v-2z',
      'chart-kpi': 'M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z',
      'chart-heatmap': 'M4 4h4v4H4V4zm6 0h4v4h-4V4zm6 0h4v4h-4V4zM4 10h4v4H4v-4zm6 0h4v4h-4v-4zm6 0h4v4h-4v-4z'
    };
    return icons[iconName] || icons['chart-bar'];
  }

  getChartsByCategory(category: string): ChartType[] {
    return this.chartTypes.filter(ct => ct.category === category);
  }
}

