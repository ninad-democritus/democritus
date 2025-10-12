/**
 * Chart Data Service
 * Manages dashboard items and chart selection state
 */

import { Injectable, NgZone } from '@angular/core';
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

  constructor(private zone: NgZone) {}

  /**
   * Get current dashboard items
   */
  getDashboardItems(): DashboardItem[] {
    return this.dashboardItemsSubject.value;
  }

  /**
   * Add a new chart to the dashboard
   * Ensures emission happens in Angular zone for proper change detection
   */
  addChart(item: DashboardItem): void {
    this.zone.run(() => {
      const items = this.dashboardItemsSubject.value;
      this.dashboardItemsSubject.next([...items, item]);
    });
  }

  /**
   * Remove a chart from the dashboard
   * Ensures emission happens in Angular zone for proper change detection
   */
  removeChart(id: string): void {
    this.zone.run(() => {
      const items = this.dashboardItemsSubject.value.filter(item => item.id !== id);
      this.dashboardItemsSubject.next(items);
      
      // Clear selection if removed chart was selected
      if (this.selectedChartIdSubject.value === id) {
        this.selectChart(null);
      }
    });
  }

  /**
   * Update a chart's properties
   * Ensures emission happens in Angular zone for proper change detection
   */
  updateChart(id: string, updates: Partial<DashboardItem>): void {
    this.zone.run(() => {
      const items = this.dashboardItemsSubject.value.map(item => {
        if (item.id === id) {
          // Deep merge config if it exists in updates
          if (updates.config) {
            const merged = {
              ...item,
              ...updates,
              config: {
                ...item.config,
                ...updates.config
              }
            };
            console.log('[ChartDataService] Updating chart:', {
              chartId: id,
              oldConfig: item.config,
              newConfig: updates.config,
              mergedConfig: merged.config
            });
            return merged;
          }
          return { ...item, ...updates };
        }
        return item;
      });
      this.dashboardItemsSubject.next(items);
    });
  }

  /**
   * Select a chart for AI context
   * Ensures emission happens in Angular zone for proper change detection
   */
  selectChart(id: string | null): void {
    this.zone.run(() => {
      // Update selection state on items
      const items = this.dashboardItemsSubject.value.map(item => ({
        ...item,
        isSelected: item.id === id
      }));
      this.dashboardItemsSubject.next(items);
      this.selectedChartIdSubject.next(id);
    });
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
   * Ensures emission happens in Angular zone for proper change detection
   */
  clearDashboard(): void {
    this.zone.run(() => {
      this.dashboardItemsSubject.next([]);
      this.selectedChartIdSubject.next(null);
    });
  }

  /**
   * Load dashboard items (from backend or storage)
   * Ensures emission happens in Angular zone for proper change detection
   */
  loadDashboard(items: DashboardItem[]): void {
    this.zone.run(() => {
      this.dashboardItemsSubject.next(items);
    });
  }

  /**
   * Generate unique ID for new charts
   */
  generateId(): string {
    return `chart-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Highlight a chart with animation (for newly created/updated charts)
   * Ensures emission happens in Angular zone for proper change detection
   */
  highlightChart(id: string): void {
    this.zone.run(() => {
      // Select the chart
      this.selectChart(id);
      
      // Add temporary highlight class
      const items = this.dashboardItemsSubject.value.map(item => ({
        ...item,
        isHighlighted: item.id === id
      }));
      this.dashboardItemsSubject.next(items);
      
      // Remove highlight after 3 seconds (setTimeout is auto-patched by zone.js)
      setTimeout(() => {
        this.zone.run(() => {
          const items = this.dashboardItemsSubject.value.map(item => ({
            ...item,
            isHighlighted: false
          }));
          this.dashboardItemsSubject.next(items);
        });
      }, 3000);
    });
  }
}

