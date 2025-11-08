/**
 * TypeScript Types und Interfaces für Benchmark-Daten
 *
 * Diese Datei definiert alle Typen die zwischen Backend und Frontend
 * ausgetauscht werden
 */

export interface BenchmarkConfig {
  runs: number;
  categories: string[];
}

export interface BenchmarkStartResponse {
  benchmark_id: string;
  status: string;
  message: string;
}

export interface BenchmarkProgress {
  benchmark_id?: string;  // Included in final message for result fetching
  status: 'running' | 'completed' | 'failed';
  progress: number;
  total: number;
  last_message: string;
  timestamp: string;
  message?: string;  // Optional message field
  // results NOT included in SSE - fetch via /status endpoint instead
}

export interface BenchmarkResult {
  api_name: string;
  api_category: string;
  run_number: number;
  num_chunks: number;
  embed_ms: number;
  pg_write_ms: number;
  chroma_write_ms: number;
  pg_query_ms: number;
  chroma_query_ms: number;
  pg_result_count: number;
  chroma_result_count: number;
  db_size_pg_mb: number;
  db_size_chroma_mb: number;
}

export interface AggregatedResults {
  api_name: string;
  category: string;
  pg_ingest_avg: number;
  pg_ingest_std: number;
  chroma_ingest_avg: number;
  chroma_ingest_std: number;
  pg_query_avg: number;
  pg_query_std: number;
  chroma_query_avg: number;
  chroma_query_std: number;
}

export interface ChartData {
  x: (string | number)[];
  y: number[];
  type: string;
  name: string;
  marker?: { color: string };
}
