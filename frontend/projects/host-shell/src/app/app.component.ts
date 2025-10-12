import { Component, OnInit, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { Router, NavigationEnd, NavigationStart } from '@angular/router';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent implements OnInit, AfterViewInit {
  title = 'host-shell';

  @ViewChild('contentArea', { read: ElementRef }) contentArea: ElementRef;

  constructor(private router: Router) {}

  ngOnInit() {
    // Clear content area on navigation start to prevent stacking
    this.router.events.pipe(
      filter(event => event instanceof NavigationStart)
    ).subscribe(() => {
      if (this.contentArea && this.contentArea.nativeElement) {
        // Force clear all child nodes except router-outlet
        const element = this.contentArea.nativeElement;
        const children = Array.from(element.children);
        children.forEach((child: any) => {
          if (child.tagName !== 'ROUTER-OUTLET') {
            child.style.display = 'none';
            setTimeout(() => {
              if (child.parentNode === element) {
                element.removeChild(child);
              }
            }, 0);
          }
        });
      }
    });
  }

  ngAfterViewInit() {
    // Initial cleanup
    if (this.contentArea && this.contentArea.nativeElement) {
      console.log('Content area initialized');
    }
  }

  isAiCanvasRoute(): boolean {
    return this.router.url.startsWith('/ai-canvas');
  }

  isDashboardsRoute(): boolean {
    const url = this.router.url;
    // Active for list and view pages
    return url === '/ai-canvas' || 
           url === '/ai-canvas/' || 
           url === '/ai-canvas/dashboards' ||
           url === '/ai-canvas/dashboards/' ||
           url.includes('/ai-canvas/dashboards/view');
  }

  isCreateDashboardRoute(): boolean {
    const url = this.router.url;
    // Active for create and edit pages
    return url.includes('/ai-canvas/dashboards/create') ||
           url.includes('/ai-canvas/dashboards/edit');
  }
}
