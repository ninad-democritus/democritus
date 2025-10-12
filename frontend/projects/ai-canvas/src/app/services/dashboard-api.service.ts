import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface SaveDashboardRequest {
  name: string;
  owner_id: string;
  visibility: 'private' | 'public';
  dashboard_type: 'static' | 'dynamic';
  gridster_config?: any;
  widgets: WidgetData[];
}

export interface WidgetData {
  grid_x: number;
  grid_y: number;
  grid_cols: number;
  grid_rows: number;
  chart_config: any;
  metadata: any;
  nl_query?: string;
}

export interface DashboardResponse {
  id: string;
  name: string;
  owner_id: string;
  visibility: string;
  dashboard_type: string;
  gridster_config: any;
  created_at: string;
  updated_at: string;
  widgets: any[];
}

export interface DashboardListItem {
  id: string;
  name: string;
  visibility: string;
  dashboard_type: string;
  widget_count: number;
  created_at: string;
  updated_at: string;
}

export interface WidgetPreview {
  id: string;
  name: string;
  chart_type: string;
  position: { x: number; y: number };
  size: { cols: number; rows: number };
}

export interface DashboardViewItem {
  id: string;
  name: string;
  owner_id: string;
  visibility: 'private' | 'public';
  dashboard_type: 'static' | 'dynamic';
  created_at: string;
  updated_at: string;
  widget_count: number;
  widgets_preview: WidgetPreview[];
}

export type DashboardScope = 'my' | 'public' | 'all';

@Injectable({ providedIn: 'root' })
export class DashboardApiService {
  private baseUrl = '/api/v1/dashboards';

  constructor(private http: HttpClient) {}

  /**
   * Create new dashboard
   */
  createDashboard(request: SaveDashboardRequest): Observable<DashboardResponse> {
    return this.http.post<DashboardResponse>(this.baseUrl, request);
  }

  /**
   * List user's dashboards
   */
  listDashboards(ownerId: string): Observable<DashboardListItem[]> {
    return this.http.get<DashboardListItem[]>(`${this.baseUrl}?owner_id=${ownerId}`);
  }

  /**
   * View dashboards with widget preview (optimized for dashboard list page)
   */
  viewDashboards(
    scope: DashboardScope = 'all',
    search: string = ''
  ): Observable<DashboardViewItem[]> {
    const params = new HttpParams()
      .set('scope', scope)
      .set('search', search)
      .set('owner_id', this.getTempUserId());
    
    return this.http.get<DashboardViewItem[]>(
      `${this.baseUrl}/view`,
      { params }
    );
  }

  /**
   * Get dashboard by ID
   */
  getDashboard(dashboardId: string, ownerId: string): Observable<DashboardResponse> {
    return this.http.get<DashboardResponse>(`${this.baseUrl}/${dashboardId}?owner_id=${ownerId}`);
  }

  /**
   * Update dashboard
   */
  updateDashboard(
    dashboardId: string,
    ownerId: string,
    updates: Partial<SaveDashboardRequest>
  ): Observable<DashboardResponse> {
    return this.http.put<DashboardResponse>(
      `${this.baseUrl}/${dashboardId}?owner_id=${ownerId}`,
      updates
    );
  }

  /**
   * Delete dashboard
   */
  deleteDashboard(dashboardId: string, ownerId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${dashboardId}?owner_id=${ownerId}`);
  }

  /**
   * Get or create temporary user ID
   */
  getTempUserId(): string {
    let userId = localStorage.getItem('tempUserId');
    if (!userId) {
      userId = `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('tempUserId', userId);
    }
    return userId;
  }
}

