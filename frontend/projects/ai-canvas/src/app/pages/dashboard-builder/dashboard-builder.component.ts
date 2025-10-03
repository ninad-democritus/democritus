/**
 * Dashboard Builder Component
 * Main container for the three-panel dashboard builder interface
 */

import { Component } from '@angular/core';
import { ChartDataService } from '../../services/chart-data.service';
import { AIChatService } from '../../services/ai-chat.service';

@Component({
  selector: 'app-dashboard-builder',
  templateUrl: './dashboard-builder.component.html',
  styleUrl: './dashboard-builder.component.scss'
})
export class DashboardBuilderComponent {
  constructor(
    private chartDataService: ChartDataService,
    private aiChatService: AIChatService
  ) {}
}

