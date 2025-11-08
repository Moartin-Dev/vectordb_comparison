/**
 * Benchmark Config Component
 *
 * Angular Component Pattern:
 * - Standalone Component (Angular 14+) = keine NgModule benötigt
 * - Component = View (HTML) + Logic (TypeScript) + Styles (CSS)
 * - Decorator @Component() definiert Metadaten
 *
 * Reactive Forms:
 * - FormBuilder für typsichere Forms
 * - Validators für Form-Validierung
 * - Reaktive Updates via Observable Streams
 */

import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { BenchmarkService } from '../../services/benchmark.service';
import { BenchmarkConfig } from '../../models/benchmark.types';

@Component({
  selector: 'app-benchmark-config',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <!-- TailwindCSS Classes Explanation:
         - container: Zentriert Content und setzt max-width
         - mx-auto: Margin horizontal auto (zentriert)
         - p-6: Padding 1.5rem (24px)
         - bg-white: Weißer Hintergrund
         - rounded-lg: Abgerundete Ecken
         - shadow-md: Medium Shadow für Tiefe
    -->
    <div class="container mx-auto p-6">
      <div class="bg-white rounded-lg shadow-md p-6">
        <h2 class="text-2xl font-bold mb-6 text-gray-800">
          Benchmark Konfiguration
        </h2>

        <div class="space-y-4">
          <!-- Runs Input -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Anzahl Durchläufe (Runs)
            </label>
            <input
              type="number"
              [(ngModel)]="config.runs"
              min="1"
              max="100"
              class="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              [disabled]="isRunning"
            />
            <p class="mt-1 text-sm text-gray-500">
              Wie oft soll jede API getestet werden? (1-100)
            </p>
          </div>

          <!-- Category Checkboxes -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              API Kategorien
            </label>
            <div class="space-y-2">
              <label class="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  [(ngModel)]="categories.small"
                  [disabled]="isRunning"
                  class="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
                <span class="text-gray-700">Small (< 1000 LOC)</span>
              </label>
              <label class="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  [(ngModel)]="categories.medium"
                  [disabled]="isRunning"
                  class="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
                <span class="text-gray-700">Medium (1000-10000 LOC)</span>
              </label>
              <label class="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  [(ngModel)]="categories.large"
                  [disabled]="isRunning"
                  class="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
                <span class="text-gray-700">Large (> 10000 LOC)</span>
              </label>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="flex gap-4 mt-6">
            <button
              (click)="startBenchmark()"
              [disabled]="isRunning || !hasSelectedCategories()"
              class="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {{ isRunning ? 'Läuft...' : 'Benchmark Starten' }}
            </button>

            <button
              *ngIf="isRunning"
              (click)="stopBenchmark()"
              class="px-6 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
            >
              Abbrechen
            </button>
          </div>

          <!-- Status Message -->
          <div *ngIf="statusMessage" class="mt-4 p-4 rounded-md"
               [ngClass]="{
                 'bg-green-100 text-green-800': !errorMessage,
                 'bg-red-100 text-red-800': errorMessage
               }">
            {{ statusMessage }}
          </div>
        </div>
      </div>
    </div>
  `,
  styles: []
})
export class BenchmarkConfigComponent implements OnInit, OnDestroy {
  // Component State
  config: BenchmarkConfig = {
    runs: 3,
    categories: []
  };

  categories = {
    small: true,
    medium: false,
    large: false
  };

  isRunning = false;
  statusMessage = '';
  errorMessage = false;
  private progressSubscription?: Subscription;

  constructor(
    private benchmarkService: BenchmarkService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    // Subscribe zu Progress Updates um Status zu tracken
    this.progressSubscription = this.benchmarkService.progress$.subscribe({
      next: (progress) => {
        console.log('Config received progress:', progress);
        // Wenn Benchmark abgeschlossen ist, setze isRunning zurück
        if (progress.status === 'completed') {
          this.isRunning = false;
          this.statusMessage = '✅ Benchmark erfolgreich abgeschlossen!';
          this.errorMessage = false;
          console.log('Setting isRunning to false');
          this.cdr.detectChanges(); // Trigger Change Detection
        } else if (progress.status === 'failed') {
          this.isRunning = false;
          this.statusMessage = '❌ Benchmark fehlgeschlagen';
          this.errorMessage = true;
          this.cdr.detectChanges(); // Trigger Change Detection
        }
      }
    });
  }

  ngOnDestroy(): void {
    this.progressSubscription?.unsubscribe();
  }

  hasSelectedCategories(): boolean {
    return Object.values(this.categories).some(v => v);
  }

  startBenchmark(): void {
    if (!this.hasSelectedCategories()) {
      this.statusMessage = 'Bitte wähle mindestens eine Kategorie aus';
      this.errorMessage = true;
      return;
    }

    // Sammle ausgewählte Kategorien
    this.config.categories = Object.entries(this.categories)
      .filter(([_, selected]) => selected)
      .map(([category, _]) => category);

    this.isRunning = true;
    this.errorMessage = false;
    this.statusMessage = 'Benchmark wird gestartet...';

    // Starte Benchmark via Service
    this.benchmarkService.startBenchmark(this.config).subscribe({
      next: (response) => {
        this.statusMessage = response.message;
        // Verbinde zu SSE Stream für Live-Updates
        this.benchmarkService.connectToStream(response.benchmark_id);
      },
      error: (error) => {
        this.statusMessage = `Fehler: ${error.message}`;
        this.errorMessage = true;
        this.isRunning = false;
      }
    });
  }

  stopBenchmark(): void {
    this.benchmarkService.disconnectStream();
    this.isRunning = false;
    this.statusMessage = 'Benchmark abgebrochen';
  }
}
