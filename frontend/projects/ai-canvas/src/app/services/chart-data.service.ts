/**
 * Chart Data Service
 * Manages dashboard items and chart selection state
 */

import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { DashboardItem } from '../models/dashboard-item.model';
import { ChartGenerationResult } from '../models/query-service.model';

@Injectable({
  providedIn: 'root'
})
export class ChartDataService {
  private dashboardItemsSubject = new BehaviorSubject<DashboardItem[]>([]);
  public dashboardItems$ = this.dashboardItemsSubject.asObservable();

  private selectedChartIdSubject = new BehaviorSubject<string | null>(null);
  public selectedChartId$ = this.selectedChartIdSubject.asObservable();

  constructor() {}

  /**
   * Get current dashboard items
   */
  getDashboardItems(): DashboardItem[] {
    return this.dashboardItemsSubject.value;
  }

  /**
   * Add a new chart to the dashboard
   */
  addChart(item: DashboardItem): void {
    const items = this.dashboardItemsSubject.value;
    this.dashboardItemsSubject.next([...items, item]);
  }

  /**
   * Remove a chart from the dashboard
   */
  removeChart(id: string): void {
    const items = this.dashboardItemsSubject.value.filter(item => item.id !== id);
    this.dashboardItemsSubject.next(items);
    
    // Clear selection if removed chart was selected
    if (this.selectedChartIdSubject.value === id) {
      this.selectChart(null);
    }
  }

  /**
   * Update a chart's properties
   */
  updateChart(id: string, updates: Partial<DashboardItem>): void {
    const items = this.dashboardItemsSubject.value.map(item =>
      item.id === id ? { ...item, ...updates } : item
    );
    this.dashboardItemsSubject.next(items);
  }

  /**
   * Select a chart for AI context
   */
  selectChart(id: string | null): void {
    // Update selection state on items
    const items = this.dashboardItemsSubject.value.map(item => ({
      ...item,
      isSelected: item.id === id
    }));
    this.dashboardItemsSubject.next(items);
    this.selectedChartIdSubject.next(id);
  }

  /**
   * Get currently selected chart
   */
  getSelectedChart(): DashboardItem | null {
    const selectedId = this.selectedChartIdSubject.value;
    if (!selectedId) return null;
    
    return this.dashboardItemsSubject.value.find(item => item.id === selectedId) || null;
  }

  /**
   * Update chart with AI-generated configuration
   */
  updateChartFromAI(id: string, result: ChartGenerationResult): void {
    const updates: Partial<DashboardItem> = {
      config: {
        title: result.chartConfig.title,
        naturalLanguageQuery: result.naturalLanguageQuery,
        queryTimestamp: new Date(),
        echartsOptions: result.chartConfig.echartsOptions,
        queryMetadata: result.metadata
      }
    };
    this.updateChart(id, updates);
  }

  /**
   * Clear all charts from dashboard
   */
  clearDashboard(): void {
    this.dashboardItemsSubject.next([]);
    this.selectedChartIdSubject.next(null);
  }

  /**
   * Load dashboard items (from backend or storage)
   */
  loadDashboard(items: DashboardItem[]): void {
    this.dashboardItemsSubject.next(items);
  }

  /**
   * Generate unique ID for new charts
   */
  generateId(): string {
    return `chart-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}

