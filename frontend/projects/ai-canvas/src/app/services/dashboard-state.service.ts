import { Injectable, NgZone } from '@angular/core';
import { BehaviorSubject, Observable, Subject } from 'rxjs';

export interface DashboardMetadata {
  id: string;
  name: string;
  visibility: 'private' | 'public';
  dashboardType: 'static' | 'dynamic';
}

@Injectable({ providedIn: 'root' })
export class DashboardStateService {
  private saveTriggered$ = new Subject<void>();
  private hasUnsavedChangesSubject = new BehaviorSubject<boolean>(false);
  private currentDashboardSubject = new BehaviorSubject<DashboardMetadata | null>(null);
  
  constructor(private zone: NgZone) {}
  
  /**
   * Trigger save from header button
   * Ensures emission happens in Angular zone for proper change detection
   */
  triggerSave() {
    console.log('Dashboard State Service: Triggering save');
    this.zone.run(() => {
      this.saveTriggered$.next();
    });
  }
  
  /**
   * Listen for save trigger in dashboard builder
   */
  onSaveTriggered(): Observable<void> {
    return this.saveTriggered$.asObservable();
  }
  
  /**
   * Set unsaved changes state
   * Ensures emission happens in Angular zone for proper change detection
   */
  setUnsavedChanges(hasChanges: boolean) {
    this.zone.run(() => {
      this.hasUnsavedChangesSubject.next(hasChanges);
    });
  }
  
  /**
   * Observable for unsaved changes
   */
  get hasUnsavedChanges$(): Observable<boolean> {
    return this.hasUnsavedChangesSubject.asObservable();
  }
  
  /**
   * Set current dashboard metadata (for edit mode)
   */
  setCurrentDashboard(metadata: DashboardMetadata | null) {
    this.zone.run(() => {
      this.currentDashboardSubject.next(metadata);
    });
  }
  
  /**
   * Get current dashboard metadata
   */
  getCurrentDashboard(): DashboardMetadata | null {
    return this.currentDashboardSubject.value;
  }
  
  /**
   * Observable for current dashboard
   */
  get currentDashboard$(): Observable<DashboardMetadata | null> {
    return this.currentDashboardSubject.asObservable();
  }
}

