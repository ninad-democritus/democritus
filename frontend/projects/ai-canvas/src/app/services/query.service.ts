/**
 * Query Service
 * HTTP client for communicating with backend Query Service API
 */

import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError, of } from 'rxjs';
import { catchError, delay } from 'rxjs/operators';
import { ChartGenerationRequest, ChartGenerationResult } from '../models/query-service.model';

@Injectable({
  providedIn: 'root'
})
export class QueryService {
  private apiUrl = '/api/v1/query-service';

  constructor(private http: HttpClient) {}

  /**
   * Generate chart from natural language query
   * Handles both Workflow A (with constraints) and Workflow B (without constraints)
   */
  generateChart(request: ChartGenerationRequest): Observable<ChartGenerationResult> {
    // TODO: Replace with actual HTTP call when backend is ready
    // return this.http.post<ChartGenerationResult>(
    //   `${this.apiUrl}/generate-chart`,
    //   request
    // ).pipe(
    //   catchError(this.handleError)
    // );

    // MOCK IMPLEMENTATION for development
    return this.mockGenerateChart(request);
  }

  /**
   * Regenerate chart with different constraints
   */
  regenerateChart(
    originalQuery: string,
    newConstraints: ChartGenerationRequest['constraints']
  ): Observable<ChartGenerationResult> {
    return this.generateChart({
      naturalLanguageQuery: originalQuery,
      constraints: newConstraints
    });
  }

  /**
   * MOCK: Simulate backend chart generation
   * This will be replaced with actual HTTP call
   */
  private mockGenerateChart(request: ChartGenerationRequest): Observable<ChartGenerationResult> {
    // Simulate network delay
    const mockResponse: ChartGenerationResult = {
      success: true,
      data: this.generateMockData(request),
      chartConfig: {
        type: request.constraints?.chartType || this.recommendChartType(request.naturalLanguageQuery),
        title: this.generateTitle(request.naturalLanguageQuery),
        echartsOptions: this.generateMockEChartsOptions(request),
        size: request.constraints?.chartSize || { cols: 6, rows: 3 }
      },
      metadata: {
        sqlQuery: `SELECT * FROM data WHERE condition = '${request.naturalLanguageQuery}'`,
        dataSchema: { field1: 'string', field2: 'number' },
        recommendedChartType: request.constraints?.chartType ? undefined : 'bar',
        confidence: 0.92
      },
      naturalLanguageQuery: request.naturalLanguageQuery
    };

    return of(mockResponse).pipe(delay(1500)); // Simulate 1.5s backend processing
  }

  /**
   * MOCK: Generate sample data based on query
   */
  private generateMockData(request: ChartGenerationRequest): any[] {
    const query = request.naturalLanguageQuery.toLowerCase();
    
    if (query.includes('region')) {
      return [
        { region: 'North', value: 45000 },
        { region: 'South', value: 38000 },
        { region: 'East', value: 52000 },
        { region: 'West', value: 41000 }
      ];
    } else if (query.includes('trend') || query.includes('time') || query.includes('month')) {
      return [
        { month: 'Jan', value: 30000 },
        { month: 'Feb', value: 35000 },
        { month: 'Mar', value: 42000 },
        { month: 'Apr', value: 38000 },
        { month: 'May', value: 45000 },
        { month: 'Jun', value: 50000 }
      ];
    } else {
      return [
        { category: 'Category A', value: 65 },
        { category: 'Category B', value: 45 },
        { category: 'Category C', value: 85 },
        { category: 'Category D', value: 55 }
      ];
    }
  }

  /**
   * MOCK: Recommend chart type based on query
   */
  private recommendChartType(query: string): string {
    query = query.toLowerCase();
    if (query.includes('trend') || query.includes('time') || query.includes('over')) {
      return 'line';
    } else if (query.includes('proportion') || query.includes('percentage')) {
      return 'pie';
    } else {
      return 'bar';
    }
  }

  /**
   * MOCK: Generate title from query
   */
  private generateTitle(query: string): string {
    return query.charAt(0).toUpperCase() + query.slice(1);
  }

  /**
   * MOCK: Generate ECharts options
   */
  private generateMockEChartsOptions(request: ChartGenerationRequest): any {
    const data = this.generateMockData(request);
    const chartType = request.constraints?.chartType || this.recommendChartType(request.naturalLanguageQuery);

    const xAxisData = data.map(d => d.region || d.month || d.category);
    const seriesData = data.map(d => d.value);

    if (chartType === 'pie') {
      return {
        tooltip: { trigger: 'item' },
        series: [{
          type: 'pie',
          radius: '60%',
          data: data.map(d => ({
            name: d.region || d.month || d.category,
            value: d.value
          })),
          itemStyle: {
            borderRadius: 4
          }
        }]
      };
    } else if (chartType === 'line') {
      return {
        tooltip: { trigger: 'axis' },
        xAxis: {
          type: 'category',
          data: xAxisData,
          axisLabel: { color: '#64748b' }
        },
        yAxis: {
          type: 'value',
          axisLabel: { color: '#64748b' }
        },
        series: [{
          type: 'line',
          data: seriesData,
          smooth: true,
          itemStyle: { color: '#14b8a6' },
          areaStyle: { color: 'rgba(20, 184, 166, 0.1)' }
        }],
        grid: { left: '10%', right: '10%', bottom: '15%', top: '10%' }
      };
    } else {
      // Default to bar chart
      return {
        tooltip: { trigger: 'axis' },
        xAxis: {
          type: 'category',
          data: xAxisData,
          axisLabel: { color: '#64748b' }
        },
        yAxis: {
          type: 'value',
          axisLabel: { color: '#64748b' }
        },
        series: [{
          type: 'bar',
          data: seriesData,
          itemStyle: {
            color: '#14b8a6',
            borderRadius: [4, 4, 0, 0]
          }
        }],
        grid: { left: '10%', right: '10%', bottom: '15%', top: '10%' }
      };
    }
  }

  /**
   * Handle HTTP errors
   */
  private handleError(error: HttpErrorResponse): Observable<never> {
    console.error('Query Service Error:', error);
    let errorMessage = 'An error occurred while processing your query.';
    
    if (error.error instanceof ErrorEvent) {
      // Client-side error
      errorMessage = `Error: ${error.error.message}`;
    } else {
      // Server-side error
      errorMessage = error.error?.error || errorMessage;
    }
    
    return throwError(() => new Error(errorMessage));
  }
}

