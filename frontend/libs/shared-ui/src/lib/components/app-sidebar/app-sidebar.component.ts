import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

interface NavItem {
  label: string;
  route: string;
  icon: SafeHtml;
  ariaLabel: string;
}

@Component({
  selector: 'lib-app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './app-sidebar.component.html',
  styleUrls: ['./app-sidebar.component.scss']
})
export class AppSidebarComponent {
  navItems: NavItem[];

  constructor(private sanitizer: DomSanitizer) {
    this.navItems = [
      {
        label: 'Ingest',
        route: '/ingestion',
        icon: this.getDatabaseIcon(),
        ariaLabel: 'Navigate to Data Ingestion'
      },
      {
        label: 'Canvas',
        route: '/ai-canvas',
        icon: this.getCanvasIcon(),
        ariaLabel: 'Navigate to AI Canvas'
      }
    ];
  }

  private getDatabaseIcon(): SafeHtml {
    const svg = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path>
    </svg>`;
    return this.sanitizer.bypassSecurityTrustHtml(svg);
  }

  private getCanvasIcon(): SafeHtml {
    const svg = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
    </svg>`;
    return this.sanitizer.bypassSecurityTrustHtml(svg);
  }
}

