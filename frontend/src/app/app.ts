import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { BenchmarkConfigComponent } from './components/benchmark-config/benchmark-config.component';
import { LiveDashboardComponent } from './components/live-dashboard/live-dashboard.component';

@Component({
  selector: 'app-root',
  imports: [
    RouterOutlet,
    BenchmarkConfigComponent,
    LiveDashboardComponent
  ],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected readonly title = 'Vector Database Benchmark';
}
