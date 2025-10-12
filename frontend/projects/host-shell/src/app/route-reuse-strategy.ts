import { ActivatedRouteSnapshot, DetachedRouteHandle, RouteReuseStrategy } from '@angular/router';

/**
 * Custom Route Reuse Strategy to prevent component stacking
 * Forces Angular to destroy components instead of reusing them
 */
export class NoReuseStrategy implements RouteReuseStrategy {
  shouldDetach(route: ActivatedRouteSnapshot): boolean {
    return false;
  }

  store(route: ActivatedRouteSnapshot, detachedTree: DetachedRouteHandle): void {
    // Don't store anything
  }

  shouldAttach(route: ActivatedRouteSnapshot): boolean {
    return false;
  }

  retrieve(route: ActivatedRouteSnapshot): DetachedRouteHandle | null {
    return null;
  }

  shouldReuseRoute(future: ActivatedRouteSnapshot, curr: ActivatedRouteSnapshot): boolean {
    // Never reuse routes - always destroy and recreate components
    // This prevents component stacking in MFE architecture
    return false;
  }
}

