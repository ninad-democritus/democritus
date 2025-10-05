/**
 * Query Service
 * HTTP and WebSocket client for communicating with backend Query Service API
 */

import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError, Subject, BehaviorSubject } from 'rxjs';
import { catchError, finalize } from 'rxjs/operators';
import {
  ChartGenerationRequest,
  ChartGenerationResult,
  ChartGenerationInitiated,
  WSProgressMessage,
  WSSQLGeneratedMessage,
  WSCompletedMessage,
  WSErrorMessage,
  WebSocketMessage,
  QueryServiceError
} from '../models/query-service.model';

@Injectable({
  providedIn: 'root'
})
export class QueryService {
  private apiUrl = '/api/v1/query-service';
  private wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  private wsBaseUrl = `${this.wsProtocol}//${window.location.host}`;

  // Active WebSocket connections by queryId
  private activeConnections = new Map<string, WebSocket>();

  constructor(private http: HttpClient) {}

  /**
   * Generate chart from natural language query (Async flow)
   * Returns queryId and WebSocket URL immediately
   */
  initiateChartGeneration(request: ChartGenerationRequest): Observable<ChartGenerationInitiated> {
    return this.http.post<ChartGenerationInitiated>(
      `${this.apiUrl}/generate-chart`,
      request
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Connect to WebSocket for real-time query progress
   * Returns Observable that emits progress messages
   */
  connectToQueryProgress(queryId: string, websocketUrl: string): Observable<WebSocketMessage> {
    const subject = new Subject<WebSocketMessage>();

    // Full WebSocket URL
    const wsUrl = `${this.wsBaseUrl}${websocketUrl}`;

    console.log(`[QueryService] Connecting to WebSocket: ${wsUrl}`);

    // Create WebSocket connection
    const ws = new WebSocket(wsUrl);

    // Store connection
    this.activeConnections.set(queryId, ws);

    ws.onopen = () => {
      console.log(`[QueryService] WebSocket connected for query ${queryId}`);
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        console.log(`[QueryService] Received message:`, message);
        subject.next(message);

        // Auto-close on completion or error
        if (message.type === 'COMPLETED' || message.type === 'ERROR') {
          ws.close();
        }
      } catch (error) {
        console.error('[QueryService] Failed to parse WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('[QueryService] WebSocket error:', error);
      subject.error(new Error('WebSocket connection error'));
    };

    ws.onclose = () => {
      console.log(`[QueryService] WebSocket closed for query ${queryId}`);
      this.activeConnections.delete(queryId);
      subject.complete();
    };

    return subject.asObservable();
  }

  /**
   * Close WebSocket connection for a query
   */
  closeConnection(queryId: string): void {
    const ws = this.activeConnections.get(queryId);
    if (ws) {
      ws.close();
      this.activeConnections.delete(queryId);
    }
  }

  /**
   * Complete workflow: Initiate query and connect to WebSocket
   * Returns Observable that emits all progress messages and final result
   */
  generateChartWithProgress(request: ChartGenerationRequest): Observable<WebSocketMessage> {
    const progressSubject = new Subject<WebSocketMessage>();

    // Step 1: Initiate query
    this.initiateChartGeneration(request).subscribe({
      next: (initiated) => {
        // Step 2: Connect to WebSocket
        this.connectToQueryProgress(initiated.queryId, initiated.websocketUrl).subscribe({
          next: (message) => progressSubject.next(message),
          error: (error) => progressSubject.error(error),
          complete: () => progressSubject.complete()
        });
      },
      error: (error) => {
        progressSubject.error(error);
      }
    });

    return progressSubject.asObservable();
  }

  /**
   * Regenerate chart with different constraints
   */
  regenerateChart(
    originalQuery: string,
    newConstraints: ChartGenerationRequest['constraints']
  ): Observable<WebSocketMessage> {
    return this.generateChartWithProgress({
      naturalLanguageQuery: originalQuery,
      constraints: newConstraints
    });
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

  /**
   * Clean up all active connections
   */
  ngOnDestroy(): void {
    this.activeConnections.forEach((ws) => ws.close());
    this.activeConnections.clear();
  }
}
