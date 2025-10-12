import { Component, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

interface MenuItem {
  label: string;
  icon: SafeHtml;
  action: () => void;
  divider?: boolean;
}

interface User {
  name: string;
  email: string;
  avatar: string;
}

@Component({
  selector: 'lib-user-menu',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './user-menu.component.html',
  styleUrls: ['./user-menu.component.scss']
})
export class UserMenuComponent {
  isOpen = false;
  
  user: User = {
    name: 'John Doe',
    email: 'john.doe@example.com',
    avatar: 'JD' // Initials for now
  };

  menuItems: MenuItem[];

  constructor(private sanitizer: DomSanitizer) {
    this.menuItems = [
      { 
        label: 'Profile', 
        icon: this.getUserIcon(),
        action: () => this.goToProfile()
      },
      { 
        label: 'Settings', 
        icon: this.getSettingsIcon(),
        action: () => this.goToSettings()
      },
      { 
        label: 'Help', 
        icon: this.getHelpIcon(),
        action: () => this.openHelp()
      },
      { 
        label: 'Logout', 
        icon: this.getLogoutIcon(),
        action: () => this.logout(),
        divider: true
      }
    ];
  }

  toggleDropdown(): void {
    this.isOpen = !this.isOpen;
  }

  closeDropdown(): void {
    this.isOpen = false;
  }

  handleMenuItemClick(item: MenuItem): void {
    item.action();
    this.closeDropdown();
  }

  goToProfile(): void {
    console.log('Navigate to profile');
    // TODO: Implement navigation
  }

  goToSettings(): void {
    console.log('Navigate to settings');
    // TODO: Implement navigation
  }

  openHelp(): void {
    console.log('Open help');
    // TODO: Implement help modal or navigation
  }

  logout(): void {
    console.log('Logging out...');
    // TODO: Implement logout logic
  }

  private getUserIcon(): SafeHtml {
    const svg = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
    </svg>`;
    return this.sanitizer.bypassSecurityTrustHtml(svg);
  }

  private getSettingsIcon(): SafeHtml {
    const svg = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
    </svg>`;
    return this.sanitizer.bypassSecurityTrustHtml(svg);
  }

  private getHelpIcon(): SafeHtml {
    const svg = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
    </svg>`;
    return this.sanitizer.bypassSecurityTrustHtml(svg);
  }

  private getLogoutIcon(): SafeHtml {
    const svg = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path>
    </svg>`;
    return this.sanitizer.bypassSecurityTrustHtml(svg);
  }

  @HostListener('document:click', ['$event'])
  onClickOutside(event: MouseEvent): void {
    const target = event.target as HTMLElement;
    const clickedInside = target.closest('.user-menu-container');
    
    if (!clickedInside && this.isOpen) {
      this.closeDropdown();
    }
  }
}

