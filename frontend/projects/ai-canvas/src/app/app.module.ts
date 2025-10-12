import { NgModule } from '@angular/core';
import { RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { DragDropModule } from '@angular/cdk/drag-drop';
import { GridsterModule } from 'angular-gridster2';
import { NgxEchartsModule } from 'ngx-echarts';
import { routes } from './app.routes';
import { AppComponent } from './app.component';
import { ChangeDetectionInterceptor } from './core/change-detection.interceptor';

// Dashboard Builder components
import { DashboardBuilderComponent } from './pages/dashboard-builder/dashboard-builder.component';
import { ChartLibraryComponent } from './pages/dashboard-builder/components/chart-library/chart-library.component';
import { DashboardGridComponent } from './pages/dashboard-builder/components/dashboard-grid/dashboard-grid.component';
import { ChartWidgetComponent } from './pages/dashboard-builder/components/dashboard-grid/components/chart-widget/chart-widget.component';
import { AIChatComponent } from './pages/dashboard-builder/components/ai-chat/ai-chat.component';
import { SaveDashboardModalComponent } from './pages/dashboard-builder/components/save-dashboard-modal/save-dashboard-modal.component';
import { DashboardListComponent } from './pages/dashboard-list/dashboard-list.component';
import { DashboardViewComponent } from './pages/dashboard-view/dashboard-view.component';

@NgModule({
  declarations: [
    AppComponent,
    DashboardBuilderComponent,
    ChartLibraryComponent,
    DashboardGridComponent,
    ChartWidgetComponent,
    AIChatComponent,
    SaveDashboardModalComponent,
    DashboardListComponent,
    DashboardViewComponent
  ],
  imports: [
    CommonModule,
    NoopAnimationsModule,
    FormsModule,
    ReactiveFormsModule,
    HttpClientModule,
    DragDropModule,
    GridsterModule,
    RouterModule.forChild(routes),
    NgxEchartsModule.forRoot({
      echarts: () => import('echarts')
    })
  ],
  providers: [
    {
      provide: HTTP_INTERCEPTORS,
      useClass: ChangeDetectionInterceptor,
      multi: true
    }
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
