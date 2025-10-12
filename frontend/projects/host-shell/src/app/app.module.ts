import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { CommonModule } from '@angular/common';
import { RouterModule, RouteReuseStrategy } from '@angular/router';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { AppHeaderComponent, AppSidebarComponent } from 'shared-ui';
import { NoReuseStrategy } from './route-reuse-strategy';

@NgModule({
  declarations: [
    AppComponent
  ],
  imports: [
    BrowserModule,
    CommonModule,
    RouterModule,
    AppRoutingModule,
    AppHeaderComponent,
    AppSidebarComponent
  ],
  providers: [
    { provide: RouteReuseStrategy, useClass: NoReuseStrategy }
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
