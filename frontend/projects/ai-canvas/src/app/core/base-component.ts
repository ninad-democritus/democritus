/**
 * Base Component for Module Federation Change Detection
 * 
 * All ai-canvas components should extend this to automatically
 * handle change detection issues in Module Federation environment.
 * 
 * Usage:
 * ```typescript
 * export class MyComponent extends BaseComponent implements OnInit {
 *   constructor(cdr: ChangeDetectorRef) {
 *     super(cdr);
 *   }
 * }
 * ```
 */

import { ChangeDetectorRef, Directive, OnDestroy } from '@angular/core';
import { Subject, Observable, OperatorFunction } from 'rxjs';
import { tap } from 'rxjs/operators';

@Directive()
export abstract class BaseComponent implements OnDestroy {
  protected destroy$ = new Subject<void>();

  constructor(protected cdr: ChangeDetectorRef) {}

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * RxJS operator that automatically triggers change detection after emission
   * Use in pipe() instead of manual detectChanges()
   * 
   * @example
   * this.service.data$
   *   .pipe(
   *     this.detectChanges(),
   *     takeUntil(this.destroy$)
   *   )
   *   .subscribe(data => this.data = data);
   */
  protected detectChanges<T>(): OperatorFunction<T, T> {
    return tap(() => {
      this.cdr.detectChanges();
    });
  }

  /**
   * Mark component for check (lighter than detectChanges)
   */
  protected markForCheck(): void {
    this.cdr.markForCheck();
  }

  /**
   * Force immediate change detection
   */
  protected forceChangeDetection(): void {
    this.cdr.detectChanges();
  }

  /**
   * Subscribe and auto-trigger change detection
   * Alternative to using the detectChanges() operator
   * 
   * @example
   * this.autoDetectSubscribe(
   *   this.service.data$,
   *   data => this.data = data
   * );
   */
  protected autoDetectSubscribe<T>(
    observable: Observable<T>,
    next: (value: T) => void,
    error?: (error: any) => void,
    complete?: () => void
  ): void {
    observable
      .pipe(
        tap(() => this.cdr.detectChanges()),
        takeUntil(this.destroy$)
      )
      .subscribe({
        next,
        error: error ? (err) => {
          error(err);
          this.cdr.detectChanges();
        } : undefined,
        complete: complete ? () => {
          complete();
          this.cdr.detectChanges();
        } : undefined
      });
  }
}

// Helper import for takeUntil
import { takeUntil } from 'rxjs/operators';

