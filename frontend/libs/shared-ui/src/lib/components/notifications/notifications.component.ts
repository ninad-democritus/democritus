import { Component, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

interface Notification {
  id: number;
  message: string;
  time: string;
  read: boolean;
  type?: 'success' | 'warning' | 'error' | 'info';
}

@Component({
  selector: 'lib-notifications',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './notifications.component.html',
  styleUrls: ['./notifications.component.scss']
})
export class NotificationsComponent {
  constructor(private sanitizer: DomSanitizer) {}
  isOpen = false;
  
  notifications: Notification[] = [
    { 
      id: 1, 
      message: 'Pipeline completed successfully', 
      time: '5m ago', 
      read: false,
      type: 'success'
    },
    { 
      id: 2, 
      message: 'New schema approval required', 
      time: '1h ago', 
      read: false,
      type: 'warning'
    },
    { 
      id: 3, 
      message: 'Data ingestion started', 
      time: '2h ago', 
      read: true,
      type: 'info'
    }
  ];

  get unreadCount(): number {
    return this.notifications.filter(n => !n.read).length;
  }

  toggleDropdown(): void {
    this.isOpen = !this.isOpen;
  }

  closeDropdown(): void {
    this.isOpen = false;
  }

  markAsRead(notification: Notification): void {
    notification.read = true;
  }

  markAllAsRead(): void {
    this.notifications.forEach(n => n.read = true);
  }

  getBellIcon(): SafeHtml {
    const svg = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path>
    </svg>`;
    return this.sanitizer.bypassSecurityTrustHtml(svg);
  }

  @HostListener('document:click', ['$event'])
  onClickOutside(event: MouseEvent): void {
    const target = event.target as HTMLElement;
    const clickedInside = target.closest('.notifications-container');
    
    if (!clickedInside && this.isOpen) {
      this.closeDropdown();
    }
  }
}

