/**
 * Change Detection HTTP Interceptor
 * 
 * Automatically triggers change detection after every HTTP response
 * in Module Federation environment where zone patches may not work properly.
 * 
 * This eliminates the need for manual detectChanges() calls after HTTP requests.
 */

import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent, HttpResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { ApplicationRef } from '@angular/core';

@Injectable()
export class ChangeDetectionInterceptor implements HttpInterceptor {
  constructor(private appRef: ApplicationRef) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    return next.handle(req).pipe(
      tap(event => {
        // Trigger change detection on HTTP response
        if (event instanceof HttpResponse) {
          // Use setTimeout to avoid "Expression has changed after it was checked" errors
          setTimeout(() => {
            this.appRef.tick();
          }, 0);
        }
      })
    );
  }
}

