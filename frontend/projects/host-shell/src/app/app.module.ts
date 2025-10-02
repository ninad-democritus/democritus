import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { AppHeaderComponent, AppSidebarComponent } from 'shared-ui';

@NgModule({
  declarations: [
    AppComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    AppHeaderComponent,
    AppSidebarComponent
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
