/**
 * BenchmarkService - Kommunikation mit Backend via HTTP und SSE
 *
 * Angular Service Pattern:
 * - Services sind Singleton-Instanzen (providedIn: 'root')
 * - Werden via Dependency Injection bereitgestellt
 * - Kapseln Business-Logik und API-Kommunikation
 *
 * Server-Sent Events (SSE):
 * - Unidirektionale Kommunikation vom Server zum Client
 * - EventSource API für native Browser-Unterstützung
 * - Perfekt für Live-Updates während Benchmark-Läufen
 *
 * RxJS Observables:
 * - Angular nutzt RxJS für reaktive Programmierung
 * - Observables = Streams von Daten über Zeit
 * - Subscriber erhalten Updates automatisch
 */

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, Subject } from 'rxjs';
import {
  BenchmarkConfig,
  BenchmarkStartResponse,
  BenchmarkProgress,
  BenchmarkResult
} from '../models/benchmark.types';

@Injectable({
  providedIn: 'root'  // Singleton Service für gesamte App
})
export class BenchmarkService {
  // Nutze nginx Reverse Proxy statt direkter Backend-URL
  private readonly apiUrl = '/api';
  private eventSource: EventSource | null = null;

  // Subject = Observable + Observer (kann Werte emittieren UND subscribt werden)
  private progressSubject = new Subject<BenchmarkProgress>();

  // Public Observable für Components
  public progress$ = this.progressSubject.asObservable();

  constructor(private http: HttpClient) {}

  /**
   * Startet einen neuen Benchmark
   *
   * HTTP POST Request an Backend
   * @returns Observable mit benchmark_id
   */
  startBenchmark(config: BenchmarkConfig): Observable<BenchmarkStartResponse> {
    return this.http.post<BenchmarkStartResponse>(
      `${this.apiUrl}/benchmark/start`,
      config
    );
  }

  /**
   * Emittiert initialen Progress-State sofort nach Benchmark-Start
   * Verhindert Race Condition zwischen SSE-Connect und ersten Updates
   */
  emitInitialProgress(progress: BenchmarkProgress): void {
    this.progressSubject.next(progress);
  }

  /**
   * Verbindet zu SSE Stream für Live-Updates
   *
   * EventSource API:
   * - Browser-native für SSE
   * - Automatische Reconnection
   * - text/event-stream MIME type
   *
   * @param benchmarkId - ID des gestarteten Benchmarks
   */
  connectToStream(benchmarkId: string): void {
    // Schließe alte Verbindung falls vorhanden
    this.disconnectStream();

    // Neue SSE-Verbindung erstellen
    this.eventSource = new EventSource(
      `${this.apiUrl}/benchmark/stream/${benchmarkId}`
    );

    // Event-Handler für eingehende Nachrichten
    this.eventSource.onmessage = (event) => {
      try {
        const data: BenchmarkProgress = JSON.parse(event.data);
        console.log('SSE received:', data);
        // Emittiere Update an alle Subscriber
        this.progressSubject.next(data);

        // Schließe Verbindung nach Completion/Failure
        if (data.status === 'completed' || data.status === 'failed') {
          console.log('Benchmark finished, closing SSE connection');
          setTimeout(() => {
            this.disconnectStream();
          }, 100); // Kleine Verzögerung um sicherzustellen dass alle Subscriber verarbeitet haben
        }
      } catch (error) {
        console.error('Error parsing SSE data:', error);
      }
    };

    // Error-Handler - nur loggen, nicht disconnecten
    this.eventSource.onerror = (error) => {
      console.log('SSE connection closed or error occurred');
      // Nicht mehr disconnecten, das passiert bereits in onmessage
    };
  }

  /**
   * Schließt SSE-Verbindung
   * Wichtig: Immer aufräumen um Memory Leaks zu vermeiden!
   */
  disconnectStream(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  /**
   * Holt Status eines laufenden Benchmarks via HTTP
   * Alternative zu SSE für einmalige Abfragen
   */
  getBenchmarkStatus(benchmarkId: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/benchmark/status/${benchmarkId}`);
  }

  /**
   * Cleanup beim Zerstören des Services
   * Angular Lifecycle Hook
   */
  ngOnDestroy(): void {
    this.disconnectStream();
  }
}
