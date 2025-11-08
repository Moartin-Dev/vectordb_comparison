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

// Plotly.js Import
declare const Plotly: any;

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
          <span>{{ progressPercent | number:'1.0-0' }}%</span>
        </div>

        <p class="mt-2 text-sm text-gray-700">
          {{ currentProgress.last_message }}
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
        <!-- Ingest Performance Chart -->
        <div class="bg-white rounded-lg shadow-md p-6">
          <h3 class="text-lg font-bold mb-4 text-gray-800">
            Ingest Performance
          </h3>
          <div id="ingest-chart" class="h-[600px]"></div>
        </div>

        <!-- Query Performance Chart -->
        <div class="bg-white rounded-lg shadow-md p-6">
          <h3 class="text-lg font-bold mb-4 text-gray-800">
            Query Performance
          </h3>
          <div id="query-chart" class="h-[600px]"></div>
        </div>

        <!-- Database Size Chart -->
        <div class="bg-white rounded-lg shadow-md p-6">
          <h3 class="text-lg font-bold mb-4 text-gray-800">
            Datenbankgröße
          </h3>
          <div id="size-chart" class="h-[600px]"></div>
        </div>

        <!-- Results Count Chart -->
        <div class="bg-white rounded-lg shadow-md p-6">
          <h3 class="text-lg font-bold mb-4 text-gray-800">
            Anzahl Ergebnisse
          </h3>
          <div id="results-chart" class="h-[600px]"></div>
        </div>
      </div>

      <!-- Statistical Summary Table (shown only when benchmark is completed) -->
      <div *ngIf="showStatisticalSummary()" class="mt-6 bg-white rounded-lg shadow-md p-6">
        <h3 class="text-lg font-bold mb-4 text-gray-800">
          Statistische Zusammenfassung
        </h3>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-indigo-900">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-bold text-white uppercase">API</th>
                <th class="px-4 py-3 text-left text-xs font-bold text-white uppercase">Category</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">LOC</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">Runs (N)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">Chunks (avg)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">PG Ingest (ms)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">Chroma Ingest (ms)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">PG Query (ms)</th>
                <th class="px-4 py-3 text-center text-xs font-bold text-white uppercase">Chroma Query (ms)</th>
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
  benchmarkCompleted = false;

  // Subscription für Cleanup
  private progressSubscription?: Subscription;

  // Plotly Chart Config
  private readonly layout = {
    autosize: true,
    margin: { t: 40, r: 20, b: 40, l: 60 },
    showlegend: true,
    legend: { orientation: 'h', y: -0.2 }
  };

  private readonly colors = {
    pgvector: '#1f77b4',  // Blau
    chromadb: '#ff7f0e'   // Orange
  };

  // LOC Mapping basierend auf api_specs_list.json
  private readonly apiLocMapping: Record<string, number> = {
    'Petstore': 830,
    'AbstractAPI Geolocation': 200,
    'OpenAI API': 3500,
    'Salesloft.com API': 9900,
    'Spotify Web API': 7200,
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

    if (progress.total > 0) {
      this.progressPercent = (progress.progress / progress.total) * 100;
    }

    // Update Charts mit aktuellen Daten
    this.updateCharts();

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
      return {
        api: apiName,
        category: apiResults[0].api_category,
        loc: loc,
        runs: apiResults.length,
        chunks_avg: this.mean(chunksValues),
        pg_ingest: this.formatStat(pgIngestValues),
        chroma_ingest: this.formatStat(chromaIngestValues),
        pg_query: this.formatStat(pgQueryValues),
        chroma_query: this.formatStat(chromaQueryValues)
      };
    });

    console.log('Statistical summary calculated:', this.statisticalSummary);
  }

  private mean(values: number[]): number {
    return values.reduce((sum, val) => sum + val, 0) / values.length;
  }

  private std(values: number[]): number {
    const avg = this.mean(values);
    const squaredDiffs = values.map(val => Math.pow(val - avg, 2));
    const variance = this.mean(squaredDiffs);
    return Math.sqrt(variance);
  }

  private formatStat(values: number[]): string {
    const avg = this.mean(values);
    const stdDev = this.std(values);
    return `${avg.toFixed(1)} ± ${stdDev.toFixed(1)}`;
  }

  initCharts(): void {
    // Plotly.newPlot erstellt leere Charts
    const emptyData: any[] = [];

    Plotly.newPlot('ingest-chart', emptyData, {
      ...this.layout,
      xaxis: { title: 'API' },
      yaxis: { title: 'Zeit (ms)' },
      title: 'Ingest Performance'
    });

    Plotly.newPlot('query-chart', emptyData, {
      ...this.layout,
      xaxis: { title: 'API' },
      yaxis: { title: 'Zeit (ms)' },
      title: 'Query Performance'
    });

    Plotly.newPlot('size-chart', emptyData, {
      ...this.layout,
      xaxis: { title: 'API' },
      yaxis: { title: 'Größe (MB)' },
      title: 'Datenbankgröße'
    });

    Plotly.newPlot('results-chart', emptyData, {
      ...this.layout,
      xaxis: { title: 'API' },
      yaxis: { title: 'Anzahl' },
      title: 'Gefundene Ergebnisse'
    });
  }

  updateCharts(): void {
    if (this.results.length === 0) return;

    // Gruppiere Daten nach API
    const grouped = this.groupByApi();

    // Update Ingest Chart
    this.updateIngestChart(grouped);
    this.updateQueryChart(grouped);
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

    // Für Boxplots brauchen wir alle Werte, nicht nur den Durchschnitt
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
      yaxis: { title: 'Schreibzeit (ms)' },
      title: 'Ingest Performance (Boxplot)',
      showlegend: true
    });
  }

  private updateQueryChart(grouped: Map<string, BenchmarkResult[]>): void {
    const apis = Array.from(grouped.keys());

    // Für Boxplots brauchen wir alle Werte, nicht nur den Durchschnitt
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
      yaxis: { title: 'Abfragezeit (ms)' },
      title: 'Query Performance (Boxplot)',
      showlegend: true
    });
  }

  private updateSizeChart(grouped: Map<string, BenchmarkResult[]>): void {
    const apis = Array.from(grouped.keys());

    const pgData = apis.map(api => grouped.get(api)![0].db_size_pg_mb);
    const chromaData = apis.map(api => grouped.get(api)![0].db_size_chroma_mb);

    const traces = [
      { x: apis, y: pgData, type: 'bar', name: 'PgVector', marker: { color: this.colors.pgvector } },
      { x: apis, y: chromaData, type: 'bar', name: 'ChromaDB', marker: { color: this.colors.chromadb } }
    ];

    Plotly.react('size-chart', traces, {
      ...this.layout,
      xaxis: { title: 'API-Spezifikation' },
      yaxis: { title: 'Datenbankgröße (MB)' },
      title: 'Datenbankgröße-Vergleich'
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
      xaxis: { title: 'API-Spezifikation' },
      yaxis: { title: 'Anzahl Ergebnisse' },
      title: 'Durchschnittliche Anzahl Ergebnisse'
    });
  }
}
