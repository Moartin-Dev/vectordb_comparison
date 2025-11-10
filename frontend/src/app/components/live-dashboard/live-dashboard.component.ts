/**
 * Live Dashboard Component
 *
 * Angular Component Lifecycle:
 * - ngOnInit(): Wird beim Initialisieren aufgerufen
 * - ngOnDestroy(): Wird beim Zerstören aufgerufen (Cleanup!)
 *
 * Observable Subscriptions:
 * - subscribe() registriert einen Listener
 * - WICHTIG: Immer unsubscribe() in ngOnDestroy() !
 * - Verhindert Memory Leaks
 *
 * Plotly.js Integration:
 * - Plotly.newPlot() erstellt neuen Chart
 * - Plotly.react() updated bestehenden Chart (performanter!)
 * - Layout definiert Achsen, Titel, Styling
 */

import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { BenchmarkService } from '../../services/benchmark.service';
import { BenchmarkProgress, BenchmarkResult } from '../../models/benchmark.types';
import html2canvas from 'html2canvas';

// Plotly.js Import
declare const Plotly: any;

// Detailed Performance Statistics Interface
interface DetailedPerformanceStats {
  api: string;  // z.B. "Petstore"
  implementation: string;  // z.B. "PG Ingest", "Chroma Query"
  min: number;
  max: number;
  mean: number;
  percentile_25: number;
  median: number;
  percentile_75: number;
  iqr: number;
}

@Component({
  selector: 'app-live-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="container mx-auto p-6">
      <!-- Progress Card -->
      <div *ngIf="isActive" class="bg-white rounded-lg shadow-md p-6 mb-6">
        <h3 class="text-xl font-bold mb-4 text-gray-800">Fortschritt</h3>

        <!-- Progress Bar -->
        <div class="w-full bg-gray-200 rounded-full h-4 mb-2">
          <div
            class="bg-blue-600 h-4 rounded-full transition-all duration-500"
            [style.width.%]="progressPercent"
          ></div>
        </div>

        <div class="flex justify-between text-sm text-gray-600">
          <span>{{ currentProgress.progress }} / {{ currentProgress.total }}</span>
          <span>{{ currentProgress.overall_progress_pct !== undefined ? (currentProgress.overall_progress_pct | number:'1.1-1') : (progressPercent | number:'1.0-0') }}%</span>
        </div>

        <p class="mt-2 text-sm text-gray-700 font-medium">
          {{ currentProgress.last_message }}
        </p>

        <!-- Phase Indicator (optional) -->
        <p *ngIf="currentProgress.phase" class="mt-1 text-xs text-gray-500 italic">
          Phase: {{ currentProgress.phase }}
        </p>

        <div class="mt-4">
          <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium"
                [ngClass]="{
                  'bg-yellow-100 text-yellow-800': currentProgress.status === 'running',
                  'bg-green-100 text-green-800': currentProgress.status === 'completed',
                  'bg-red-100 text-red-800': currentProgress.status === 'failed'
                }">
            {{ currentProgress.status === 'running' ? 'Läuft' :
               currentProgress.status === 'completed' ? 'Abgeschlossen' : 'Fehler' }}
          </span>
        </div>
      </div>

      <!-- Charts - One per row for better readability -->
      <div class="space-y-6">
        <!-- Ingest Performance Boxplot -->
        <div class="bg-white rounded-lg shadow-md p-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-bold text-gray-800">
              Ingest Performance (Boxplot)
            </h3>
            <button
              *ngIf="results.length > 0"
              (click)="downloadChart('ingest-chart', 'ingest_boxplot.png')"
              class="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 transition-colors">
              Download PNG
            </button>
          </div>
          <div id="ingest-chart" class="h-[600px]"></div>
        </div>

        <!-- Query Performance Boxplot -->
        <div class="bg-white rounded-lg shadow-md p-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-bold text-gray-800">
              Query Performance (Boxplot)
            </h3>
            <button
              *ngIf="results.length > 0"
              (click)="downloadChart('query-chart', 'query_boxplot.png')"
              class="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 transition-colors">
              Download PNG
            </button>
          </div>
          <div id="query-chart" class="h-[600px]"></div>
        </div>

        <!-- Ingest Performance Violin Plot -->
        <div class="bg-white rounded-lg shadow-md p-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-bold text-gray-800">
              Ingest Performance (Violin Plot)
            </h3>
            <button
              *ngIf="results.length > 0"
              (click)="downloadChart('ingest-violin-chart', 'ingest_violin.png')"
              class="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 transition-colors">
              Download PNG
            </button>
          </div>
          <div id="ingest-violin-chart" class="h-[600px]"></div>
        </div>

        <!-- Query Performance Violin Plot -->
        <div class="bg-white rounded-lg shadow-md p-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-bold text-gray-800">
              Query Performance (Violin Plot)
            </h3>
            <button
              *ngIf="results.length > 0"
              (click)="downloadChart('query-violin-chart', 'query_violin.png')"
              class="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 transition-colors">
              Download PNG
            </button>
          </div>
          <div id="query-violin-chart" class="h-[600px]"></div>
        </div>

        <!-- Database Size Chart -->
        <div class="bg-white rounded-lg shadow-md p-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-bold text-gray-800">
              Datenbankgröße
            </h3>
            <button
              *ngIf="results.length > 0"
              (click)="downloadChart('size-chart', 'database_size.png')"
              class="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 transition-colors">
              Download PNG
            </button>
          </div>
          <div id="size-chart" class="h-[600px]"></div>
        </div>

        <!-- Results Count Chart -->
        <div class="bg-white rounded-lg shadow-md p-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-bold text-gray-800">
              Anzahl Ergebnisse
            </h3>
            <button
              *ngIf="results.length > 0"
              (click)="downloadChart('results-chart', 'results_count.png')"
              class="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 transition-colors">
              Download PNG
            </button>
          </div>
          <div id="results-chart" class="h-[600px]"></div>
        </div>
      </div>

      <!-- Statistical Summary Table (shown only when benchmark is completed) -->
      <div *ngIf="showStatisticalSummary()" class="mt-6 bg-white rounded-lg shadow-md p-6">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold text-gray-800">
            Statistische Zusammenfassung
          </h3>
          <button
            (click)="downloadTable()"
            class="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 transition-colors">
            Download PNG
          </button>
        </div>
        <div id="statistical-table" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-indigo-900">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-bold text-white uppercase">API</th>
                <th class="px-4 py-3 text-left text-xs font-bold text-white uppercase">Category</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">LOC</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">Runs (N)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">Chunks (avg)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">PG Ingest Total (ms)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">Chroma Ingest Total (ms)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">PG Query per Search (ms)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">Chroma Query per Search (ms)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">PG Size (MB)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">Chroma Size (MB)</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              <tr *ngFor="let stat of statisticalSummary; let i = index"
                  [ngClass]="{'bg-gray-50': i % 2 === 1, 'bg-white': i % 2 === 0}"
                  class="hover:bg-blue-50">
                <td class="px-4 py-3 text-sm font-medium text-gray-900">{{ stat.api }}</td>
                <td class="px-4 py-3 text-sm text-gray-700">{{ stat.category }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ stat.loc | number:'1.0-0' }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ stat.runs }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ stat.chunks_avg | number:'1.0-0' }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ stat.pg_ingest }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ stat.chroma_ingest }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ stat.pg_query }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ stat.chroma_query }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ stat.db_size_pg | number:'1.2-2' }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ stat.db_size_chroma | number:'1.2-2' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- API Specs Analysis Table -->
      <div class="mt-6 bg-white rounded-lg shadow-md p-6">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold text-gray-800">
            API-Spezifikationen Analyse
          </h3>
          <div class="flex gap-2">
            <button
              *ngIf="specsAnalysis.length > 0"
              (click)="downloadSpecsAnalysisTable()"
              class="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 transition-colors">
              Download PNG
            </button>
            <button
              (click)="loadSpecsAnalysis()"
              [disabled]="specsAnalysisLoading"
              class="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors disabled:bg-gray-400">
              {{ specsAnalysisLoading ? 'Lädt...' : specsAnalysis.length > 0 ? 'Neu laden' : 'Analyse laden' }}
            </button>
          </div>
        </div>
        <div *ngIf="specsAnalysis.length > 0" id="specs-analysis-table" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-indigo-900">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-bold text-white uppercase">API</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">LOC</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">Gesamte Chars</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">Extrahierte Chars</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">Extraktion (%)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">Chunks</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              <tr *ngFor="let spec of specsAnalysis; let i = index"
                  [ngClass]="{'bg-gray-50': i % 2 === 1, 'bg-white': i % 2 === 0}"
                  class="hover:bg-blue-50">
                <td class="px-4 py-3 text-sm font-medium text-gray-900">{{ spec.api }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ spec.loc | number:'1.0-0' }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ spec.raw_chars | number:'1.0-0' }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ spec.extracted_chars | number:'1.0-0' }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ spec.extraction_ratio }}%</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ spec.num_chunks }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div *ngIf="specsAnalysis.length === 0 && !specsAnalysisLoading" class="text-center text-gray-500 py-4">
          Klicken Sie auf "Analyse laden", um die API-Spezifikationen zu analysieren.
        </div>
      </div>

      <!-- Detailed Performance Statistics Table -->
      <div *ngIf="showStatisticalSummary() && detailedPerformanceStats.length > 0" class="mt-6 bg-white rounded-lg shadow-md p-6">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold text-gray-800">
            Detaillierte Performance-Statistiken
          </h3>
          <button
            (click)="downloadPerformanceTable()"
            class="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 transition-colors">
            Download PNG
          </button>
        </div>
        <div id="performance-stats-table" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-indigo-900">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-bold text-white uppercase">API</th>
                <th class="px-4 py-3 text-left text-xs font-bold text-white uppercase">Implementation</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">Min (ms)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">Max (ms)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">Mean (ms)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">25<sup>th</sup> Percentile (ms)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">Median (ms)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">75<sup>th</sup> Percentile (ms)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">Inter-quartile range (ms)</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              <tr *ngFor="let stat of detailedPerformanceStats; let i = index"
                  [ngClass]="{'bg-gray-50': i % 2 === 1, 'bg-white': i % 2 === 0}"
                  class="hover:bg-blue-50">
                <td class="px-4 py-3 text-sm font-medium text-gray-900">{{ stat.api }}</td>
                <td class="px-4 py-3 text-sm text-gray-700">{{ stat.implementation }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ stat.min | number:'1.2-2' }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ stat.max | number:'1.2-2' }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ stat.mean | number:'1.2-2' }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ stat.percentile_25 | number:'1.2-2' }}</td>
                <td class="px-4 py-3 text-sm text-center font-bold text-gray-900">{{ stat.median | number:'1.2-2' }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ stat.percentile_75 | number:'1.2-2' }}</td>
                <td class="px-4 py-3 text-sm text-center text-gray-700">{{ stat.iqr | number:'1.2-2' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Live Stats Table (recent runs) -->
      <div *ngIf="results.length > 0" class="mt-6 bg-white rounded-lg shadow-md p-6">
        <h3 class="text-lg font-bold mb-4 text-gray-800">
          Letzte Durchläufe (Live)
        </h3>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead>
              <tr>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">API</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Run</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">PG Ingest (ms)</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Chroma Ingest (ms)</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">PG Query (ms)</th>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Chroma Query (ms)</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              <tr *ngFor="let result of results.slice(-10)" class="hover:bg-gray-50">
                <td class="px-4 py-2 text-sm">{{ result.api_name }}</td>
                <td class="px-4 py-2 text-sm">{{ result.run_number }}</td>
                <td class="px-4 py-2 text-sm">{{ result.pg_write_ms | number:'1.2-2' }}</td>
                <td class="px-4 py-2 text-sm">{{ result.chroma_write_ms | number:'1.2-2' }}</td>
                <td class="px-4 py-2 text-sm">{{ result.pg_query_ms | number:'1.2-2' }}</td>
                <td class="px-4 py-2 text-sm">{{ result.chroma_query_ms | number:'1.2-2' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `,
  styles: []
})
export class LiveDashboardComponent implements OnInit, OnDestroy {
  // Component State
  isActive = false;
  currentProgress: BenchmarkProgress = {
    benchmark_id: '',
    status: 'running',
    progress: 0,
    total: 0,
    last_message: '',
    timestamp: ''
  };

  results: BenchmarkResult[] = [];
  progressPercent = 0;
  statisticalSummary: any[] = [];
  detailedPerformanceStats: DetailedPerformanceStats[] = [];
  benchmarkCompleted = false;

  // API Specs Analysis
  specsAnalysis: any[] = [];
  specsAnalysisLoading = false;

  // Subscription für Cleanup
  private progressSubscription?: Subscription;

  // Plotly Chart Config
  private readonly layout = {
    autosize: true,
    margin: { t: 60, r: 20, b: 60, l: 80 },  // Mehr Platz für größere Schrift
    showlegend: true,
    legend: { orientation: 'h', y: -0.2 },
    font: {
      family: 'Arial, sans-serif',
      size: 12
    },
    yaxis: {
      gridcolor: '#d1d5db',  // Dunkleres Grau (TailwindCSS gray-300)
      gridwidth: 1.5,        // Etwas dicker
      title: {
        font: {
          size: 14,
          family: 'Arial, sans-serif',
          color: '#000000'
        },
        standoff: 15
      },
      tickfont: {
        size: 12
      }
    },
    xaxis: {
      gridcolor: '#e5e7eb',  // Helleres Grau für x-Achse (TailwindCSS gray-200)
      gridwidth: 1,
      title: {
        font: {
          size: 14,
          family: 'Arial, sans-serif',
          color: '#000000'
        },
        standoff: 15
      },
      tickfont: {
        size: 12
      }
    }
  };

  private readonly colors = {
    pgvector: '#1f77b4',  // Blau
    chromadb: '#ff7f0e'   // Orange
  };

  // LOC Mapping basierend auf api_specs_list.json
  private readonly apiLocMapping: Record<string, number> = {
    'Ably Platform API': 1275,
    'Apache Airflow Stable API': 4800,
    'Shutterstock API': 21500,
    'Slack Web API': 49500,
    'Stripe API': 150000,
    'GitHub REST API': 236000
  };

  constructor(
    private benchmarkService: BenchmarkService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    // Subscribe zu Progress Updates
    this.progressSubscription = this.benchmarkService.progress$.subscribe({
      next: (progress) => {
        this.handleProgressUpdate(progress);
      },
      error: (error) => {
        console.error('Progress stream error:', error);
      }
    });

    // Initial Charts rendern
    this.initCharts();
  }

  ngOnDestroy(): void {
    // WICHTIG: Cleanup!
    this.progressSubscription?.unsubscribe();
  }

  handleProgressUpdate(progress: BenchmarkProgress): void {
    this.isActive = true;
    this.currentProgress = progress;

    // Use overall_progress_pct if available (granular), otherwise calculate from progress/total
    if (progress.overall_progress_pct !== undefined) {
      this.progressPercent = progress.overall_progress_pct;
    } else if (progress.total > 0) {
      this.progressPercent = (progress.progress / progress.total) * 100;
    }

    // Update Charts mit aktuellen Daten
    this.updateCharts();

    // WICHTIG: Trigger Change Detection manuell, da SSE außerhalb von Angular Zone läuft
    this.cdr.detectChanges();

    // Bei Completion - hole Results via HTTP
    if (progress.status === 'completed' && progress.benchmark_id) {
      console.log('Benchmark completed, fetching results...');
      this.benchmarkService.getBenchmarkStatus(progress.benchmark_id).subscribe({
        next: (status) => {
          if (status.results && status.results.length > 0) {
            this.results = status.results;
            console.log('Fetched benchmark results:', this.results.length, 'rows');
            this.benchmarkCompleted = true;
            this.calculateStatistics();
            console.log('Statistical summary calculated:', this.statisticalSummary.length, 'entries');
            this.updateCharts();
            this.cdr.detectChanges(); // Trigger Change Detection für Tabelle
          }
        },
        error: (error) => {
          console.error('Failed to fetch benchmark results:', error);
        }
      });
      setTimeout(() => {
        this.isActive = false;
      }, 5000);
    }
  }

  showStatisticalSummary(): boolean {
    return this.benchmarkCompleted && this.statisticalSummary.length > 0;
  }

  /**
   * Formatiert API-Namen mit LOC-Angabe
   * z.B. "Petstore" -> "Petstore (830 LOC)"
   */
  private formatApiNameWithLoc(apiName: string): string {
    const loc = this.apiLocMapping[apiName];
    if (loc) {
      // Formatiere große Zahlen mit Tausender-Trennzeichen
      const locFormatted = loc >= 1000
        ? (loc / 1000).toFixed(0) + 'k'
        : loc.toString();
      return `${apiName} (${locFormatted} LOC)`;
    }
    return apiName;
  }

  calculateStatistics(): void {
    if (this.results.length === 0) return;

    // Gruppiere Ergebnisse nach API-Name
    const grouped = new Map<string, BenchmarkResult[]>();
    this.results.forEach(r => {
      if (!grouped.has(r.api_name)) {
        grouped.set(r.api_name, []);
      }
      grouped.get(r.api_name)!.push(r);
    });

    // Berechne Statistiken für jede API
    this.statisticalSummary = Array.from(grouped.entries()).map(([apiName, apiResults]) => {
      const pgIngestValues = apiResults.map(r => r.pg_write_ms);
      const chromaIngestValues = apiResults.map(r => r.chroma_write_ms);
      const pgQueryValues = apiResults.map(r => r.pg_query_ms);
      const chromaQueryValues = apiResults.map(r => r.chroma_query_ms);
      const chunksValues = apiResults.map(r => r.num_chunks);

      const loc = this.apiLocMapping[apiName] || 0;
      // Database sizes - use the last result's values (they should be consistent)
      const dbSizePg = apiResults[apiResults.length - 1].db_size_pg_mb;
      const dbSizeChroma = apiResults[apiResults.length - 1].db_size_chroma_mb;

      return {
        api: apiName,
        category: apiResults[0].api_category,
        loc: loc,
        runs: apiResults.length,
        chunks_avg: this.mean(chunksValues),
        pg_ingest: this.formatStat(pgIngestValues),
        chroma_ingest: this.formatStat(chromaIngestValues),
        pg_query: this.formatStat(pgQueryValues),
        chroma_query: this.formatStat(chromaQueryValues),
        db_size_pg: dbSizePg,
        db_size_chroma: dbSizeChroma
      };
    });

    console.log('Statistical summary calculated:', this.statisticalSummary);

    // Berechne detaillierte Performance-Statistiken pro API
    this.detailedPerformanceStats = [];

    Array.from(grouped.entries()).forEach(([apiName, apiResults]) => {
      const pgIngestValues = apiResults.map(r => r.pg_write_ms);
      const chromaIngestValues = apiResults.map(r => r.chroma_write_ms);
      const pgQueryValues = apiResults.map(r => r.pg_query_ms);
      const chromaQueryValues = apiResults.map(r => r.chroma_query_ms);

      // Füge 4 Zeilen pro API hinzu (PG Ingest, Chroma Ingest, PG Query, Chroma Query)
      this.detailedPerformanceStats.push(
        {
          api: apiName,
          implementation: 'PG Ingest',
          min: this.min(pgIngestValues),
          max: this.max(pgIngestValues),
          mean: this.mean(pgIngestValues),
          percentile_25: this.percentile(pgIngestValues, 25),
          median: this.median(pgIngestValues),
          percentile_75: this.percentile(pgIngestValues, 75),
          iqr: this.iqr(pgIngestValues)
        },
        {
          api: apiName,
          implementation: 'Chroma Ingest',
          min: this.min(chromaIngestValues),
          max: this.max(chromaIngestValues),
          mean: this.mean(chromaIngestValues),
          percentile_25: this.percentile(chromaIngestValues, 25),
          median: this.median(chromaIngestValues),
          percentile_75: this.percentile(chromaIngestValues, 75),
          iqr: this.iqr(chromaIngestValues)
        },
        {
          api: apiName,
          implementation: 'PG Query',
          min: this.min(pgQueryValues),
          max: this.max(pgQueryValues),
          mean: this.mean(pgQueryValues),
          percentile_25: this.percentile(pgQueryValues, 25),
          median: this.median(pgQueryValues),
          percentile_75: this.percentile(pgQueryValues, 75),
          iqr: this.iqr(pgQueryValues)
        },
        {
          api: apiName,
          implementation: 'Chroma Query',
          min: this.min(chromaQueryValues),
          max: this.max(chromaQueryValues),
          mean: this.mean(chromaQueryValues),
          percentile_25: this.percentile(chromaQueryValues, 25),
          median: this.median(chromaQueryValues),
          percentile_75: this.percentile(chromaQueryValues, 75),
          iqr: this.iqr(chromaQueryValues)
        }
      );
    });

    console.log('Detailed performance stats calculated:', this.detailedPerformanceStats);
  }

  private mean(values: number[]): number {
    return values.reduce((sum, val) => sum + val, 0) / values.length;
  }

  private median(values: number[]): number {
    const sorted = [...values].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 === 0
      ? (sorted[mid - 1] + sorted[mid]) / 2
      : sorted[mid];
  }

  private percentile(values: number[], p: number): number {
    const sorted = [...values].sort((a, b) => a - b);
    const index = (p / 100) * (sorted.length - 1);
    const lower = Math.floor(index);
    const upper = Math.ceil(index);
    const weight = index - lower;
    return sorted[lower] * (1 - weight) + sorted[upper] * weight;
  }

  private min(values: number[]): number {
    return Math.min(...values);
  }

  private max(values: number[]): number {
    return Math.max(...values);
  }

  private iqr(values: number[]): number {
    const q25 = this.percentile(values, 25);
    const q75 = this.percentile(values, 75);
    return q75 - q25;
  }

  private std(values: number[]): number {
    const avg = this.mean(values);
    const squaredDiffs = values.map(val => Math.pow(val - avg, 2));
    const variance = this.mean(squaredDiffs);
    return Math.sqrt(variance);
  }

  private formatStat(values: number[]): string {
    const med = this.median(values);
    const iqrValue = this.iqr(values);
    return `${med.toFixed(1)} ± ${iqrValue.toFixed(1)}`;
  }

  initCharts(): void {
    // Plotly.newPlot erstellt leere Charts
    const emptyData: any[] = [];

    Plotly.newPlot('ingest-chart', emptyData, {
      ...this.layout,
      xaxis: {
        ...this.layout.xaxis,
        title: '<b>API</b>'
      },
      yaxis: {
        ...this.layout.yaxis,
        title: '<b>Gesamtschreibzeit für alle Chunks (ms)</b>'
      },
      title: {
        text: '<b>Ingest Performance</b>',
        font: { size: 16 }
      }
    });

    Plotly.newPlot('query-chart', emptyData, {
      ...this.layout,
      xaxis: {
        ...this.layout.xaxis,
        title: '<b>API</b>'
      },
      yaxis: {
        ...this.layout.yaxis,
        title: '<b>Abfragezeit pro Query (ms)</b>'
      },
      title: {
        text: '<b>Query Performance</b>',
        font: { size: 16 }
      }
    });

    Plotly.newPlot('ingest-violin-chart', emptyData, {
      ...this.layout,
      xaxis: {
        ...this.layout.xaxis,
        title: '<b>API</b>'
      },
      yaxis: {
        ...this.layout.yaxis,
        title: '<b>Zeit (ms)</b>'
      },
      title: {
        text: '<b>Ingest Performance (Violin)</b>',
        font: { size: 16 }
      }
    });

    Plotly.newPlot('query-violin-chart', emptyData, {
      ...this.layout,
      xaxis: {
        ...this.layout.xaxis,
        title: '<b>API</b>'
      },
      yaxis: {
        ...this.layout.yaxis,
        title: '<b>Zeit (ms)</b>'
      },
      title: {
        text: '<b>Query Performance (Violin)</b>',
        font: { size: 16 }
      }
    });

    Plotly.newPlot('size-chart', emptyData, {
      ...this.layout,
      xaxis: {
        ...this.layout.xaxis,
        title: '<b>API</b>'
      },
      yaxis: {
        ...this.layout.yaxis,
        title: '<b>Größe (MB)</b>'
      },
      title: {
        text: '<b>Datenbankgröße</b>',
        font: { size: 16 }
      }
    });

    Plotly.newPlot('results-chart', emptyData, {
      ...this.layout,
      xaxis: {
        ...this.layout.xaxis,
        title: '<b>API</b>'
      },
      yaxis: {
        ...this.layout.yaxis,
        title: '<b>Anzahl</b>'
      },
      title: {
        text: '<b>Gefundene Ergebnisse</b>',
        font: { size: 16 }
      }
    });
  }

  updateCharts(): void {
    if (this.results.length === 0) return;

    // Gruppiere Daten nach API
    const grouped = this.groupByApi();

    // Update all charts
    this.updateIngestChart(grouped);
    this.updateQueryChart(grouped);
    this.updateIngestViolinChart(grouped);
    this.updateQueryViolinChart(grouped);
    this.updateSizeChart(grouped);
    this.updateResultsChart(grouped);
  }

  private groupByApi(): Map<string, BenchmarkResult[]> {
    const map = new Map<string, BenchmarkResult[]>();
    this.results.forEach(r => {
      if (!map.has(r.api_name)) {
        map.set(r.api_name, []);
      }
      map.get(r.api_name)!.push(r);
    });
    return map;
  }

  private updateIngestChart(grouped: Map<string, BenchmarkResult[]>): void {
    const apis = Array.from(grouped.keys());

    // Boxplot Version
    const pgTraces = apis.map(api => {
      const results = grouped.get(api)!;
      const values = results.map(r => r.pg_write_ms);
      return {
        y: values,
        type: 'box',
        name: `${api} - PgVector`,
        marker: { color: this.colors.pgvector }
      };
    });

    const chromaTraces = apis.map(api => {
      const results = grouped.get(api)!;
      const values = results.map(r => r.chroma_write_ms);
      return {
        y: values,
        type: 'box',
        name: `${api} - ChromaDB`,
        marker: { color: this.colors.chromadb }
      };
    });

    const traces = [...pgTraces, ...chromaTraces];

    Plotly.react('ingest-chart', traces, {
      ...this.layout,
      yaxis: {
        ...this.layout.yaxis,
        title: '<b>Gesamtschreibzeit für alle Chunks (ms)</b>'
      },
      title: {
        text: '<b>Ingest Performance (Boxplot)</b>',
        font: { size: 16 }
      },
      showlegend: true
    });
  }

  private updateIngestViolinChart(grouped: Map<string, BenchmarkResult[]>): void {
    const apis = Array.from(grouped.keys());

    // Violin Plot Version
    const pgTraces = apis.map(api => {
      const results = grouped.get(api)!;
      const values = results.map(r => r.pg_write_ms);
      return {
        y: values,
        type: 'violin',
        name: `${api} - PgVector`,
        marker: { color: this.colors.pgvector },
        box: { visible: true },
        meanline: { visible: true }
      };
    });

    const chromaTraces = apis.map(api => {
      const results = grouped.get(api)!;
      const values = results.map(r => r.chroma_write_ms);
      return {
        y: values,
        type: 'violin',
        name: `${api} - ChromaDB`,
        marker: { color: this.colors.chromadb },
        box: { visible: true },
        meanline: { visible: true }
      };
    });

    const traces = [...pgTraces, ...chromaTraces];

    Plotly.react('ingest-violin-chart', traces, {
      ...this.layout,
      yaxis: {
        ...this.layout.yaxis,
        title: '<b>Gesamtschreibzeit für alle Chunks (ms)</b>'
      },
      title: {
        text: '<b>Ingest Performance (Violin Plot)</b>',
        font: { size: 16 }
      },
      showlegend: true
    });
  }

  private updateQueryChart(grouped: Map<string, BenchmarkResult[]>): void {
    const apis = Array.from(grouped.keys());

    // Boxplot Version
    const pgTraces = apis.map(api => {
      const results = grouped.get(api)!;
      const values = results.map(r => r.pg_query_ms);
      return {
        y: values,
        type: 'box',
        name: `${api} - PgVector`,
        marker: { color: this.colors.pgvector }
      };
    });

    const chromaTraces = apis.map(api => {
      const results = grouped.get(api)!;
      const values = results.map(r => r.chroma_query_ms);
      return {
        y: values,
        type: 'box',
        name: `${api} - ChromaDB`,
        marker: { color: this.colors.chromadb }
      };
    });

    const traces = [...pgTraces, ...chromaTraces];

    Plotly.react('query-chart', traces, {
      ...this.layout,
      yaxis: {
        ...this.layout.yaxis,
        title: '<b>Abfragezeit pro Query (ms)</b>'
      },
      title: {
        text: '<b>Query Performance (Boxplot)</b>',
        font: { size: 16 }
      },
      showlegend: true
    });
  }

  private updateQueryViolinChart(grouped: Map<string, BenchmarkResult[]>): void {
    const apis = Array.from(grouped.keys());

    // Violin Plot Version
    const pgTraces = apis.map(api => {
      const results = grouped.get(api)!;
      const values = results.map(r => r.pg_query_ms);
      return {
        y: values,
        type: 'violin',
        name: `${api} - PgVector`,
        marker: { color: this.colors.pgvector },
        box: { visible: true },
        meanline: { visible: true }
      };
    });

    const chromaTraces = apis.map(api => {
      const results = grouped.get(api)!;
      const values = results.map(r => r.chroma_query_ms);
      return {
        y: values,
        type: 'violin',
        name: `${api} - ChromaDB`,
        marker: { color: this.colors.chromadb },
        box: { visible: true },
        meanline: { visible: true }
      };
    });

    const traces = [...pgTraces, ...chromaTraces];

    Plotly.react('query-violin-chart', traces, {
      ...this.layout,
      yaxis: {
        ...this.layout.yaxis,
        title: '<b>Abfragezeit pro Query (ms)</b>'
      },
      title: {
        text: '<b>Query Performance (Violin Plot)</b>',
        font: { size: 16 }
      },
      showlegend: true
    });
  }

  private updateSizeChart(grouped: Map<string, BenchmarkResult[]>): void {
    const apis = Array.from(grouped.keys());

    const pgData = apis.map(api => grouped.get(api)![0].db_size_pg_mb);
    const chromaData = apis.map(api => grouped.get(api)![0].db_size_chroma_mb);

    const traces = [
      {
        x: apis,
        y: pgData,
        type: 'bar',
        name: 'PgVector',
        marker: { color: this.colors.pgvector },
        text: pgData.map(val => val.toFixed(2)),
        textposition: 'outside',
        textfont: { size: 12 }
      },
      {
        x: apis,
        y: chromaData,
        type: 'bar',
        name: 'ChromaDB',
        marker: { color: this.colors.chromadb },
        text: chromaData.map(val => val.toFixed(2)),
        textposition: 'outside',
        textfont: { size: 12 }
      }
    ];

    Plotly.react('size-chart', traces, {
      ...this.layout,
      xaxis: {
        ...this.layout.xaxis,
        title: '<b>API-Spezifikation</b>'
      },
      yaxis: {
        ...this.layout.yaxis,
        title: '<b>Datenbankgröße (MB)</b>'
      },
      title: {
        text: '<b>Datenbankgröße-Vergleich</b>',
        font: { size: 16 }
      }
    });
  }

  private updateResultsChart(grouped: Map<string, BenchmarkResult[]>): void {
    const apis = Array.from(grouped.keys());

    const pgData = apis.map(api => {
      const results = grouped.get(api)!;
      return results.reduce((sum, r) => sum + r.pg_result_count, 0) / results.length;
    });
    const chromaData = apis.map(api => {
      const results = grouped.get(api)!;
      return results.reduce((sum, r) => sum + r.chroma_result_count, 0) / results.length;
    });

    const traces = [
      { x: apis, y: pgData, type: 'bar', name: 'PgVector', marker: { color: this.colors.pgvector } },
      { x: apis, y: chromaData, type: 'bar', name: 'ChromaDB', marker: { color: this.colors.chromadb } }
    ];

    Plotly.react('results-chart', traces, {
      ...this.layout,
      xaxis: {
        ...this.layout.xaxis,
        title: '<b>API-Spezifikation</b>'
      },
      yaxis: {
        ...this.layout.yaxis,
        title: '<b>Anzahl Ergebnisse</b>'
      },
      title: {
        text: '<b>Durchschnittliche Anzahl Ergebnisse</b>',
        font: { size: 16 }
      }
    });
  }

  /**
   * Downloads a Plotly chart as PNG using Plotly's built-in functionality
   * @param chartId - The DOM ID of the chart element
   * @param filename - The filename for the downloaded PNG
   */
  downloadChart(chartId: string, filename: string): void {
    Plotly.downloadImage(chartId, {
      format: 'png',
      width: 1920,
      height: 1080,
      filename: filename.replace('.png', '')
    });
  }

  /**
   * Downloads the statistical summary table as PNG using html2canvas
   */
  async downloadTable(): Promise<void> {
    const element = document.getElementById('statistical-table');
    if (!element) {
      console.error('Statistical table element not found');
      return;
    }

    try {
      const canvas = await html2canvas(element, {
        scale: 2,  // Higher resolution
        backgroundColor: '#ffffff',
        logging: false
      });

      // Convert canvas to blob and trigger download
      canvas.toBlob((blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = 'statistical_summary.png';
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
        }
      });
    } catch (error) {
      console.error('Failed to download table:', error);
    }
  }

  async downloadPerformanceTable(): Promise<void> {
    const element = document.getElementById('performance-stats-table');
    if (!element) {
      console.error('Performance stats table element not found');
      return;
    }

    try {
      const canvas = await html2canvas(element, {
        scale: 2,  // Higher resolution
        backgroundColor: '#ffffff',
        logging: false
      });

      // Convert canvas to blob and trigger download
      canvas.toBlob((blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = 'detailed_performance_stats.png';
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
        }
      });
    } catch (error) {
      console.error('Failed to download performance table:', error);
    }
  }

  /**
   * Lädt die API-Spezifikationen-Analyse vom Backend
   */
  async loadSpecsAnalysis(): Promise<void> {
    this.specsAnalysisLoading = true;
    try {
      const response = await fetch('http://localhost:8000/analyze-specs');
      const data = await response.json();
      this.specsAnalysis = data.specs || [];
      console.log('Loaded specs analysis:', this.specsAnalysis);
    } catch (error) {
      console.error('Failed to load specs analysis:', error);
      alert('Fehler beim Laden der API-Analyse. Siehe Console für Details.');
    } finally {
      this.specsAnalysisLoading = false;
    }
  }

  /**
   * Downloads the API specs analysis table as PNG using html2canvas
   */
  async downloadSpecsAnalysisTable(): Promise<void> {
    const element = document.getElementById('specs-analysis-table');
    if (!element) {
      console.error('Specs analysis table element not found');
      return;
    }

    try {
      const canvas = await html2canvas(element, {
        scale: 2,  // Higher resolution
        backgroundColor: '#ffffff',
        logging: false
      });

      // Convert canvas to blob and trigger download
      canvas.toBlob((blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = 'api_specs_analysis.png';
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
        }
      });
    } catch (error) {
      console.error('Failed to download specs analysis table:', error);
    }
  }
}
