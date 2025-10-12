/**
 * Zone Operators
 * RxJS operators that ensure observables run within Angular's zone
 * for proper change detection in Module Federation environments
 */

import { MonoTypeOperatorFunction, Observable } from 'rxjs';
import { NgZone } from '@angular/core';

/**
 * RxJS operator that ensures observable emissions run inside Angular zone
 * This triggers change detection automatically for Module Federation remote apps
 * 
 * @param zone - Angular's NgZone instance
 * @returns Observable that runs emissions in Angular zone
 * 
 * @example
 * ```typescript
 * this.service.getData()
 *   .pipe(
 *     runInZone(this.zone),
 *     takeUntil(this.destroy$)
 *   )
 *   .subscribe(data => {
 *     this.data = data; // Change detection will trigger automatically
 *   });
 * ```
 */
export function runInZone<T>(zone: NgZone): MonoTypeOperatorFunction<T> {
  return (source: Observable<T>) => {
    return new Observable(subscriber => {
      return source.subscribe({
        next: (value) => {
          // If already in Angular zone, just emit
          // Otherwise, run in zone to trigger change detection
          if (NgZone.isInAngularZone()) {
            subscriber.next(value);
          } else {
            zone.run(() => subscriber.next(value));
          }
        },
        error: (error) => {
          if (NgZone.isInAngularZone()) {
            subscriber.error(error);
          } else {
            zone.run(() => subscriber.error(error));
          }
        },
        complete: () => {
          if (NgZone.isInAngularZone()) {
            subscriber.complete();
          } else {
            zone.run(() => subscriber.complete());
          }
        }
      });
    });
  };
}

/**
 * Helper function to check if code is running in Angular zone
 * Useful for debugging zone-related issues
 */
export function logZoneStatus(context: string): void {
  const inZone = NgZone.isInAngularZone();
  console.log(`[Zone Check] ${context}: ${inZone ? 'IN' : 'OUT OF'} Angular zone`);
}

