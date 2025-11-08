# Angular & TailwindCSS - Lern-Dokumentation

**Projekt**: Vector Database Benchmark Frontend
**Zweck**: Live-Dashboard für Benchmark-Ergebnisse mit Echtzeit-Updates
**Stack**: Angular 20 (Standalone Components) + TailwindCSS + Plotly.js + Server-Sent Events

---

## 📑 Inhaltsverzeichnis

1. [Angular Grundkonzepte](#angular-grundkonzepte)
2. [Standalone Components (Angular 14+)](#standalone-components)
3. [Services und Dependency Injection](#services-und-dependency-injection)
4. [RxJS und Observables](#rxjs-und-observables)
5. [Server-Sent Events (SSE)](#server-sent-events)
6. [TailwindCSS Utility-First CSS](#tailwindcss-utility-first-css)
7. [Plotly.js Integration](#plotlyjs-integration)
8. [Component Lifecycle](#component-lifecycle)
9. [Projektstruktur](#projektstruktur)
10. [Wichtige Code-Stellen](#wichtige-code-stellen)

---

## Angular Grundkonzepte

### Was ist Angular?

Angular ist ein **TypeScript-basiertes Web-Framework** von Google für Single-Page Applications (SPAs).

**Kern-Prinzipien:**
- **Component-based Architecture**: UI aufgeteilt in wiederverwendbare Components
- **Dependency Injection**: Services werden automatisch bereitgestellt
- **Reaktive Programmierung**: RxJS Observables für asynchrone Datenströme
- **TypeScript**: Typsicherheit und moderne JavaScript-Features

### MVC-Pattern in Angular

```
Model (Data) ←→ Component (Controller) ←→ Template (View)
     ↓                    ↓                      ↓
TypeScript          TypeScript Class          HTML + CSS
Interfaces          Business Logic            User Interface
```

---

## Standalone Components

### Was sind Standalone Components?

**Neu in Angular 14+** - Components ohne NgModule!

**Vorher (mit NgModule):**
```typescript
// Altes Pattern - NICHT mehr nötig!
@NgModule({
  declarations: [MyComponent],
  imports: [CommonModule, FormsModule],
  exports: [MyComponent]
})
export class MyModule {}
```

**Jetzt (Standalone):**
```typescript
@Component({
  selector: 'app-my-component',
  standalone: true,  // ← Das ist neu!
  imports: [CommonModule, FormsModule],  // Direkt im Component
  template: `<div>...</div>`
})
export class MyComponent {}
```

**Vorteile:**
- ✅ Weniger Boilerplate Code
- ✅ Einfacheres Dependency Management
- ✅ Bessere Tree-Shaking (kleinere Bundle-Größen)
- ✅ Einfachere Testbarkeit

### Im Projekt verwendet

Alle unsere Components sind standalone:

```typescript
// frontend/src/app/components/benchmark-config/benchmark-config.component.ts
@Component({
  selector: 'app-benchmark-config',
  standalone: true,
  imports: [CommonModule, FormsModule],  // Nur was wir brauchen
  template: `...`
})
export class BenchmarkConfigComponent {}
```

---

## Services und Dependency Injection

### Was sind Services?

Services sind **Singleton-Klassen** die:
- Business-Logik kapseln
- API-Kommunikation handhaben
- State zwischen Components teilen
- In Components via Dependency Injection injiziert werden

### BenchmarkService - Unser Haupt-Service

**Datei**: `frontend/src/app/services/benchmark.service.ts`

```typescript
@Injectable({
  providedIn: 'root'  // ← Singleton für gesamte App
})
export class BenchmarkService {
  constructor(private http: HttpClient) {}  // ← DI: HttpClient wird automatisch injiziert

  startBenchmark(config: BenchmarkConfig): Observable<BenchmarkStartResponse> {
    return this.http.post<BenchmarkStartResponse>(
      `${this.apiUrl}/benchmark/start`,
      config
    );
  }
}
```

**Dependency Injection in Action:**

```typescript
// In Component:
export class BenchmarkConfigComponent {
  constructor(private benchmarkService: BenchmarkService) {
    // Angular erstellt automatisch eine Instanz und injiziert sie!
  }
}
```

**Warum DI?**
- ✅ Keine `new BenchmarkService()` nötig
- ✅ Einfach zu mocken in Tests
- ✅ Automatisches Lifecycle Management
- ✅ Singleton-Pattern ohne manuellen Code

---

## RxJS und Observables

### Was ist RxJS?

**Reactive Extensions for JavaScript** - Bibliothek für reaktive Programmierung.

### Observable Pattern

Ein Observable ist ein **Stream von Daten über Zeit**:

```
Timeline ————————————————————————————→
          |    |    |    |    |
          v1   v2   v3   v4   v5

Observer subscribt → erhält alle Werte automatisch
```

### Im Projekt verwendet

**1. HTTP Requests sind Observables:**

```typescript
// Service
startBenchmark(config: BenchmarkConfig): Observable<BenchmarkStartResponse> {
  return this.http.post<BenchmarkStartResponse>(url, config);
}

// Component
this.benchmarkService.startBenchmark(this.config).subscribe({
  next: (response) => {
    // Erfolg: Handle response
    console.log(response);
  },
  error: (error) => {
    // Fehler: Handle error
    console.error(error);
  },
  complete: () => {
    // Optional: Wird aufgerufen wenn Observable fertig ist
  }
});
```

**2. Subject für SSE-Updates:**

```typescript
// Service
private progressSubject = new Subject<BenchmarkProgress>();
public progress$ = this.progressSubject.asObservable();

// Emittiere neue Werte
this.progressSubject.next(newProgress);

// Component subscribt
this.benchmarkService.progress$.subscribe({
  next: (progress) => {
    // Jedes Update kommt hier an!
    this.updateUI(progress);
  }
});
```

**Subject vs. Observable:**
- **Observable**: Nur lesen (subscribe)
- **Subject**: Lesen UND schreiben (next + subscribe)

### ⚠️ Wichtig: Memory Leaks vermeiden!

**Problem**: Subscription läuft weiter, auch wenn Component zerstört wird

**Lösung**: Immer unsubscribe in `ngOnDestroy()`:

```typescript
export class LiveDashboardComponent implements OnInit, OnDestroy {
  private progressSubscription?: Subscription;

  ngOnInit(): void {
    this.progressSubscription = this.benchmarkService.progress$.subscribe(...);
  }

  ngOnDestroy(): void {
    // WICHTIG: Cleanup!
    this.progressSubscription?.unsubscribe();
  }
}
```

---

## Server-Sent Events

### Was sind SSE?

**Server-Sent Events** = Unidirektionale Kommunikation vom Server zum Client.

```
Client                    Server
  |                         |
  |---- HTTP GET (SSE) ---->|
  |                         |
  |<------ Event 1 ---------|
  |<------ Event 2 ---------|
  |<------ Event 3 ---------|
  |         ...             |
```

### SSE vs. WebSockets vs. Polling

| Feature | SSE | WebSockets | Polling |
|---------|-----|------------|---------|
| Richtung | Uni (Server→Client) | Bi (↔) | Uni (Client→Server) |
| Protokoll | HTTP | WS | HTTP |
| Reconnect | Automatisch | Manuell | - |
| Browser-Support | Native EventSource | Native WebSocket | Immer |
| Use Case | Live-Updates | Chat, Gaming | Legacy |

**Warum SSE für uns?**
- ✅ Backend pushed Updates wenn verfügbar
- ✅ Einfacher als WebSockets
- ✅ Automatische Reconnection
- ✅ HTTP/2 kompatibel

### SSE Implementation

**Backend** (`app/benchmark_streaming.py`):

```python
async def event_generator() -> AsyncGenerator[str, None]:
    while True:
        # Warte auf neue Daten
        data = get_new_benchmark_data()

        # Sende als SSE Event
        yield f"data: {json.dumps(data)}\n\n"

        await asyncio.sleep(0.5)

return StreamingResponse(
    event_generator(),
    media_type="text/event-stream"
)
```

**Frontend** (`services/benchmark.service.ts`):

```typescript
connectToStream(benchmarkId: string): void {
  // EventSource = Native Browser API
  this.eventSource = new EventSource(
    `http://localhost:8000/benchmark/stream/${benchmarkId}`
  );

  // Handler für eingehende Events
  this.eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    this.progressSubject.next(data);  // Verteile an alle Subscriber
  };

  this.eventSource.onerror = (error) => {
    console.error('SSE Error:', error);
    this.disconnectStream();
  };
}
```

---

## TailwindCSS Utility-First CSS

### Was ist TailwindCSS?

Ein **Utility-First CSS Framework** - statt vordefinierter Components gibt es kleine Utility-Klassen.

**Traditional CSS:**
```css
.button {
  background-color: #3b82f6;
  color: white;
  padding: 0.5rem 1.5rem;
  border-radius: 0.375rem;
}
```

**TailwindCSS:**
```html
<button class="bg-blue-600 text-white px-6 py-2 rounded-md">
  Button
</button>
```

### Vorteile

- ✅ Kein Context-Switching zwischen HTML und CSS
- ✅ Konsistentes Design System
- ✅ Kleinere Bundle-Größen (Purging unused CSS)
- ✅ Responsive Design mit Breakpoints

### Tailwind Config

**Datei**: `frontend/tailwind.config.js`

```javascript
module.exports = {
  content: [
    "./src/**/*.{html,ts}",  // Scanne alle HTML/TS Dateien
  ],
  theme: {
    extend: {},  // Custom Theme Extensions
  },
  plugins: [],
}
```

**Einbindung in Angular:**

1. `tailwind.config.js` erstellt
2. Directives in `src/styles.css`:
   ```css
   @tailwind base;
   @tailwind components;
   @tailwind utilities;
   ```
3. Angular CLI kompiliert automatisch

### Wichtige Utility-Klassen im Projekt

#### Layout & Spacing

```html
<!-- Container: Zentriert Content, setzt max-width -->
<div class="container mx-auto">

<!-- Padding: p-6 = 1.5rem (24px) -->
<div class="p-6">

<!-- Margin: mt-4 = margin-top 1rem, mx-auto = horizontal center -->
<div class="mt-4 mx-auto">

<!-- Gap: Abstand zwischen Flex/Grid Items -->
<div class="flex gap-4">
```

#### Colors

```html
<!-- Background -->
<div class="bg-white">        <!-- Weiß -->
<div class="bg-gray-100">     <!-- Sehr helles Grau -->
<div class="bg-blue-600">     <!-- Blau -->

<!-- Text -->
<p class="text-gray-700">     <!-- Dunkelgrau -->
<p class="text-red-800">      <!-- Dunkelrot -->
```

**Color Scale**: 50, 100, 200, ..., 900 (hell → dunkel)

#### Typography

```html
<!-- Font Size -->
<h1 class="text-3xl">         <!-- 1.875rem -->
<p class="text-sm">           <!-- 0.875rem -->

<!-- Font Weight -->
<span class="font-bold">      <!-- 700 -->
<span class="font-medium">    <!-- 500 -->
```

#### Borders & Shadows

```html
<!-- Rounded Corners -->
<div class="rounded-md">      <!-- 0.375rem -->
<div class="rounded-lg">      <!-- 0.5rem -->

<!-- Shadow -->
<div class="shadow-md">       <!-- Medium shadow -->
<div class="shadow-sm">       <!-- Small shadow -->

<!-- Border -->
<div class="border border-gray-300">
```

#### Flexbox & Grid

```html
<!-- Flexbox -->
<div class="flex items-center justify-between">
  <!-- items-center = vertical center -->
  <!-- justify-between = space between items -->
</div>

<!-- Grid -->
<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
  <!-- 1 column auf mobile, 2 auf large screens -->
</div>
```

#### Responsive Design

```html
<!-- Breakpoints: sm, md, lg, xl, 2xl -->
<div class="grid grid-cols-1 lg:grid-cols-2">
  <!-- Mobile: 1 Spalte -->
  <!-- Large (1024px+): 2 Spalten -->
</div>

<div class="text-sm md:text-base lg:text-lg">
  <!-- Größer werdende Text-Size -->
</div>
```

#### Interactive States

```html
<!-- Hover -->
<button class="bg-blue-600 hover:bg-blue-700">

<!-- Focus -->
<input class="focus:ring-2 focus:ring-blue-500">

<!-- Disabled -->
<button class="disabled:bg-gray-400 disabled:cursor-not-allowed">
```

### TailwindCSS im Projekt

**Benchmark Config Component:**

```html
<div class="container mx-auto p-6">
  <div class="bg-white rounded-lg shadow-md p-6">
    <h2 class="text-2xl font-bold mb-6 text-gray-800">
      Benchmark Konfiguration
    </h2>

    <input
      class="w-full px-4 py-2 border border-gray-300 rounded-md
             focus:ring-2 focus:ring-blue-500 focus:border-transparent"
    />

    <button
      class="px-6 py-2 bg-blue-600 text-white rounded-md
             hover:bg-blue-700 disabled:bg-gray-400
             disabled:cursor-not-allowed transition-colors"
    >
      Start
    </button>
  </div>
</div>
```

**Erklärung Zeile für Zeile:**

```
container mx-auto    → Zentrierter Container mit max-width
p-6                  → Padding 24px auf allen Seiten
bg-white             → Weißer Hintergrund
rounded-lg           → Abgerundete Ecken (8px)
shadow-md            → Medium shadow für Tiefe
text-2xl font-bold   → Große, fette Schrift
mb-6                 → Margin-bottom 24px
w-full               → Width 100%
px-4 py-2            → Padding horizontal 16px, vertical 8px
border border-gray-300 → 1px Border in hellgrau
focus:ring-2         → Bei Focus: 2px Ring
hover:bg-blue-700    → Bei Hover: Dunkleres Blau
transition-colors    → Smooth Color Transitions
```

---

## Plotly.js Integration

### Was ist Plotly.js?

**JavaScript Charting Library** für interaktive, wissenschaftliche Visualisierungen.

### Setup

**1. CDN in `index.html`:**

```html
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
```

**2. TypeScript Declaration:**

```typescript
declare const Plotly: any;  // Macht Plotly global verfügbar
```

### Plotly API

**Neuen Chart erstellen:**

```typescript
Plotly.newPlot('chart-id', data, layout, config);
```

**Bestehenden Chart updaten (performanter!):**

```typescript
Plotly.react('chart-id', data, layout, config);
```

### Im Projekt verwendet

**Live Dashboard Component** (`components/live-dashboard/live-dashboard.component.ts`):

```typescript
// 1. Leere Charts initialisieren
initCharts(): void {
  Plotly.newPlot('ingest-chart', [], {
    xaxis: { title: 'API-Spezifikation' },
    yaxis: { title: 'Schreibzeit (ms)' },
    title: 'Ingest Performance'
  });
}

// 2. Charts mit Daten updaten
updateIngestChart(grouped: Map<string, BenchmarkResult[]>): void {
  const apis = Array.from(grouped.keys());

  // Daten aufbereiten
  const pgData = apis.map(api => {
    const results = grouped.get(api)!;
    return results.reduce((sum, r) => sum + r.pg_write_ms, 0) / results.length;
  });

  const chromaData = apis.map(api => {
    const results = grouped.get(api)!;
    return results.reduce((sum, r) => sum + r.chroma_write_ms, 0) / results.length;
  });

  // Plotly Traces = Datenreihen
  const traces = [
    {
      x: apis,
      y: pgData,
      type: 'bar',
      name: 'PgVector',
      marker: { color: '#1f77b4' }  // Blau
    },
    {
      x: apis,
      y: chromaData,
      type: 'bar',
      name: 'ChromaDB',
      marker: { color: '#ff7f0e' }  // Orange
    }
  ];

  // Update Chart (behält Interaktivität)
  Plotly.react('ingest-chart', traces, layout);
}
```

**Chart Types:**
- `'bar'` - Balkendiagramm
- `'scatter'` - Streudiagramm
- `'box'` - Boxplot
- `'violin'` - Violin Plot
- und viele mehr...

**Interaktivität:**
- Zoom & Pan
- Hover-Tooltips
- Legend Toggle
- Export als PNG

---

## Component Lifecycle

### Lifecycle Hooks

Angular Components haben einen definierten Lifecycle mit Hooks:

```
Konstructor
    ↓
ngOnInit       ← Initialization (einmalig)
    ↓
ngOnChanges    ← Input Properties ändern sich
    ↓
ngDoCheck      ← Change Detection
    ↓
ngAfterViewInit ← View initialisiert
    ↓
... Component läuft ...
    ↓
ngOnDestroy    ← Cleanup (einmalig)
```

### Wichtigste Hooks

**1. ngOnInit()**

```typescript
ngOnInit(): void {
  // HIER: Initialisierung
  // - API Calls
  // - Subscriptions
  // - Event Listeners

  this.progressSubscription = this.benchmarkService.progress$.subscribe(...);
  this.initCharts();
}
```

**Warum nicht Constructor?**
- Constructor = TypeScript/JavaScript
- ngOnInit = Angular Lifecycle (Input Properties verfügbar)

**2. ngOnDestroy()**

```typescript
ngOnDestroy(): void {
  // HIER: Cleanup
  // - Subscriptions beenden
  // - Event Listeners entfernen
  // - Timers clearen

  this.progressSubscription?.unsubscribe();
  this.benchmarkService.disconnectStream();
}
```

**⚠️ WICHTIG**: Immer cleanup um Memory Leaks zu vermeiden!

---

## Projektstruktur

```
frontend/
├── src/
│   ├── app/
│   │   ├── components/
│   │   │   ├── benchmark-config/          # Konfiguration Component
│   │   │   │   └── benchmark-config.component.ts
│   │   │   └── live-dashboard/            # Dashboard Component
│   │   │       └── live-dashboard.component.ts
│   │   ├── services/
│   │   │   └── benchmark.service.ts       # API & SSE Service
│   │   ├── models/
│   │   │   └── benchmark.types.ts         # TypeScript Interfaces
│   │   ├── app.ts                         # Root Component
│   │   ├── app.html                       # Root Template
│   │   ├── app.config.ts                  # App Configuration
│   │   └── app.routes.ts                  # Routing (falls benötigt)
│   ├── styles.css                         # Global Styles (+ Tailwind)
│   ├── index.html                         # HTML Entry Point
│   └── main.ts                            # Angular Bootstrap
├── tailwind.config.js                     # Tailwind Config
├── angular.json                           # Angular CLI Config
├── package.json                           # Dependencies
└── ANGULAR_TAILWIND_NOTES.md             # Diese Datei!
```

---

## Wichtige Code-Stellen

### 1. TypeScript Models (`models/benchmark.types.ts`)

**Zweck**: Type Safety für Daten zwischen Backend und Frontend

```typescript
export interface BenchmarkConfig {
  runs: number;
  categories: string[];
}

export interface BenchmarkProgress {
  benchmark_id: string;
  status: 'running' | 'completed' | 'failed';
  progress: number;
  total: number;
  last_message: string;
  timestamp: string;
}
```

**Warum TypeScript Interfaces?**
- Compile-Time Type Checking
- IntelliSense in IDE
- Refactoring Safety

### 2. BenchmarkService (`services/benchmark.service.ts`)

**Kernfunktionen:**

```typescript
// HTTP POST: Benchmark starten
startBenchmark(config: BenchmarkConfig): Observable<...>

// SSE: Live-Updates empfangen
connectToStream(benchmarkId: string): void

// Observable Stream für Components
public progress$: Observable<BenchmarkProgress>
```

### 3. Benchmark Config Component

**Template-driven Forms mit [(ngModel)]:**

```typescript
// Two-Way Data Binding
config: BenchmarkConfig = { runs: 3, categories: [] };
```

```html
<input [(ngModel)]="config.runs" />
<!-- Ändert config.runs automatisch bei User Input -->
```

**Event Handling:**

```html
<button (click)="startBenchmark()">
<!-- Ruft TypeScript Methode auf -->
```

### 4. Live Dashboard Component

**Observable Subscription:**

```typescript
this.benchmarkService.progress$.subscribe({
  next: (progress) => this.handleProgressUpdate(progress)
});
```

**Plotly.react() für Live-Updates:**

```typescript
// Effizient: Nur Daten updaten, nicht neu rendern
Plotly.react('chart-id', newData, layout);
```

---

## Best Practices

### ✅ DO

- **Immer unsubscribe in ngOnDestroy()**
- **Type Safety nutzen** (Interfaces, keine `any`)
- **Standalone Components** verwenden
- **TailwindCSS Utility-Klassen** statt Custom CSS
- **RxJS Operators** für komplexe Streams
- **SSE für Live-Updates** (nicht Polling)
- **Plotly.react()** für Updates (nicht newPlot)

### ❌ DON'T

- Subscriptions nicht cleanen (Memory Leaks!)
- `any` Type verwenden (Type Safety verloren)
- NgModules verwenden (veraltet)
- Inline Styles schreiben (nutze Tailwind)
- Synchronen Code für Async Operations
- HTTP Polling für Live-Updates
- `Plotly.newPlot()` für jedes Update

---

## Debugging Tipps

### Angular DevTools

**Chrome Extension**: Angular DevTools

- Component Tree visualisieren
- Change Detection profilen
- Dependency Injection Graph

### Console Logging

```typescript
// Entwicklung
console.log('Benchmark started:', response);

// SSE Debugging
this.eventSource.onmessage = (event) => {
  console.log('SSE Event:', event.data);
  const data = JSON.parse(event.data);
  console.log('Parsed:', data);
};
```

### RxJS Debugging

```typescript
// tap() Operator für Side Effects
this.benchmarkService.progress$.pipe(
  tap(progress => console.log('Progress:', progress))
).subscribe(...);
```

### TailwindCSS Debugging

**Problem**: Klassen funktionieren nicht

**Checkliste:**
1. `tailwind.config.js` content richtig?
2. `@tailwind` Directives in `styles.css`?
3. Angular Dev Server neugestartet?
4. Browser Cache geleert?

---

## Deployment

### Development Server

```bash
cd frontend
npm install          # Dependencies installieren
ng serve            # Dev Server starten (Port 4200)
```

### Production Build

```bash
ng build --configuration production
# Output: dist/frontend/
```

### Docker (kommt später)

```dockerfile
# Multi-Stage Build
FROM node:20 AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist/frontend /usr/share/nginx/html
```

---

## Weitere Ressourcen

### Offizielle Docs

- **Angular**: https://angular.dev
- **RxJS**: https://rxjs.dev
- **TailwindCSS**: https://tailwindcss.com
- **Plotly.js**: https://plotly.com/javascript/

### Wichtige Konzepte zum Vertiefen

- **RxJS Operators**: `map`, `filter`, `switchMap`, `debounceTime`
- **Angular Signals**: Neues Reactivity System (Angular 16+)
- **Lazy Loading**: Code-Splitting für große Apps
- **Guards & Interceptors**: Auth und HTTP Interceptors

---

## Zusammenfassung

**Was du gelernt hast:**

1. ✅ **Angular Standalone Components** - Moderne Component-Architektur
2. ✅ **Services & DI** - Separation of Concerns
3. ✅ **RxJS Observables** - Reaktive Programmierung
4. ✅ **Server-Sent Events** - Echtzeit-Updates ohne Polling
5. ✅ **TailwindCSS** - Utility-First CSS Framework
6. ✅ **Plotly.js** - Interaktive Charts
7. ✅ **Lifecycle Hooks** - Proper Initialization & Cleanup

**Nächste Schritte:**

- Frontend lokal testen
- Docker-Setup (kommt als nächstes)
- Weitere Features hinzufügen

---

**Erstellt für**: WAB Projekt - Vector Database Comparison
**Autor**: Claude (mit Liebe zum Detail) 🤖
