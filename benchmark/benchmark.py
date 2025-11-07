#!/usr/bin/env python3
"""
Benchmark-Skript für Vektor-Datenbank Performance-Analyse
Testet PgVector vs ChromaDB mit verschiedenen OpenAPI-Spezifikationen
"""

import httpx
import asyncio
import json
import csv
import time
import statistics
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import argparse


@dataclass
class BenchmarkResult:
    """Datenklasse für einzelne Benchmark-Ergebnisse"""
    timestamp: str
    api_name: str
    api_provider: str
    api_category: str
    run_number: int
    num_chunks: int
    embed_ms: float
    pg_write_ms: float
    chroma_write_ms: float
    query_text: str
    query_embed_ms: float
    pg_query_ms: float
    chroma_query_ms: float
    pg_num_results: int
    chroma_num_results: int
    db_size_pg_mb: float
    db_size_chroma_mb: float


class VectorDBBenchmark:
    """Haupt-Benchmark-Klasse"""

    def __init__(self, api_url: str = "http://localhost:8000", runs_per_spec: int = 10):
        self.api_url = api_url
        self.runs_per_spec = runs_per_spec
        self.results: List[BenchmarkResult] = []

    async def fetch_spec(self, url: str) -> str:
        """Lädt eine OpenAPI-Spezifikation von URL"""
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    async def ingest_spec(self, source: str, text: str) -> Dict[str, Any]:
        """Speichert eine API-Spec in beide Datenbanken"""
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{self.api_url}/ingest",
                json={
                    "source": source,
                    "text": text,
                    "backend": "both"
                }
            )
            response.raise_for_status()
            return response.json()

    async def query_spec(self, query_text: str, k: int = 5) -> Dict[str, Any]:
        """Führt eine Similarity Search durch"""
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.api_url}/query",
                json={
                    "text": query_text,
                    "k": k
                }
            )
            response.raise_for_status()
            return response.json()

    async def get_db_stats(self) -> Dict[str, Any]:
        """Holt Datenbank-Statistiken (Größe, Anzahl Dokumente)"""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.api_url}/stats")
            response.raise_for_status()
            return response.json()

    async def reset_databases(self):
        """Setzt beide Datenbanken zurück"""
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.api_url}/reset")
            response.raise_for_status()
            return response.json()

    def generate_queries(self, api_name: str, category: str) -> List[str]:
        """Generiert relevante Testqueries basierend auf API-Typ"""
        base_queries = [
            f"API endpoints for {api_name}",
            f"authentication methods in {api_name}",
            f"data models and schemas",
            "rate limiting and quotas",
            "error handling and status codes"
        ]
        return base_queries

    async def run_benchmark_for_spec(self, spec_info: Dict[str, Any], category: str):
        """Führt vollständigen Benchmark für eine API-Spec durch"""
        api_name = spec_info["name"]
        api_provider = spec_info["provider"]
        url = spec_info["url"]

        print(f"\n{'='*80}")
        print(f"Benchmarking: {api_name} ({category})")
        print(f"Provider: {api_provider}")
        print(f"Runs: {self.runs_per_spec}")
        print(f"{'='*80}\n")

        # Spec herunterladen
        print(f"📥 Downloading spec from {url}...")
        try:
            spec_text = await self.fetch_spec(url)
            print(f"✅ Downloaded {len(spec_text)} characters")
        except Exception as e:
            print(f"❌ Failed to download: {e}")
            return

        # Query-Liste generieren
        queries = self.generate_queries(api_name, category)

        # Mehrere Durchläufe
        for run in range(1, self.runs_per_spec + 1):
            print(f"\n🔄 Run {run}/{self.runs_per_spec}")

            # Datenbanken zurücksetzen für saubere Messung
            print("  🗑️  Resetting databases...")
            await self.reset_databases()
            await asyncio.sleep(1)  # Kurze Pause

            # Ingest
            print(f"  📤 Ingesting {api_name}...")
            try:
                ingest_result = await self.ingest_spec(api_name, spec_text)
                print(f"     ✅ Ingested {ingest_result['num_chunks']} chunks")
                print(f"     ⏱️  Embed: {ingest_result['embed_ms']:.2f}ms")
                print(f"     ⏱️  PG Write: {ingest_result['pg_write_ms']:.2f}ms")
                print(f"     ⏱️  Chroma Write: {ingest_result['chroma_write_ms']:.2f}ms")
            except Exception as e:
                print(f"     ❌ Ingest failed: {e}")
                continue

            # DB Stats nach Ingest
            try:
                stats = await self.get_db_stats()
                db_size_pg = stats.get("pg_size_mb", 0)
                db_size_chroma = stats.get("chroma_size_mb", 0)
            except:
                db_size_pg = 0
                db_size_chroma = 0

            # Queries durchführen
            for query_text in queries:
                print(f"  🔍 Querying: '{query_text[:50]}...'")
                try:
                    query_result = await self.query_spec(query_text, k=5)

                    # Ergebnis speichern
                    result = BenchmarkResult(
                        timestamp=datetime.now().isoformat(),
                        api_name=api_name,
                        api_provider=api_provider,
                        api_category=category,
                        run_number=run,
                        num_chunks=ingest_result['num_chunks'],
                        embed_ms=ingest_result['embed_ms'],
                        pg_write_ms=ingest_result['pg_write_ms'],
                        chroma_write_ms=ingest_result['chroma_write_ms'],
                        query_text=query_text,
                        query_embed_ms=query_result['embed_ms'],
                        pg_query_ms=query_result['pg_ms'],
                        chroma_query_ms=query_result['chroma_ms'],
                        pg_num_results=len(query_result['pg_results']),
                        chroma_num_results=len(query_result['chroma_results']),
                        db_size_pg_mb=db_size_pg,
                        db_size_chroma_mb=db_size_chroma
                    )
                    self.results.append(result)

                    print(f"     ⏱️  PG Query: {query_result['pg_ms']:.2f}ms ({len(query_result['pg_results'])} results)")
                    print(f"     ⏱️  Chroma Query: {query_result['chroma_ms']:.2f}ms ({len(query_result['chroma_results'])} results)")

                except Exception as e:
                    print(f"     ❌ Query failed: {e}")
                    continue

            # Kurze Pause zwischen Runs
            if run < self.runs_per_spec:
                await asyncio.sleep(2)

    async def run_all_benchmarks(self, specs_file: Path, categories: List[str] = None):
        """Führt Benchmarks für alle Specs in der Liste durch"""
        print("🚀 Starting Vector Database Benchmark Suite")
        print(f"📊 API URL: {self.api_url}")
        print(f"🔁 Runs per spec: {self.runs_per_spec}")

        # Specs laden
        with open(specs_file, 'r') as f:
            specs_data = json.load(f)

        # Kategorien filtern
        if categories is None:
            categories = list(specs_data['categories'].keys())

        # Für jede Kategorie
        for category in categories:
            if category not in specs_data['categories']:
                print(f"⚠️  Category '{category}' not found, skipping")
                continue

            category_specs = specs_data['categories'][category]['specs']
            print(f"\n📁 Category: {category.upper()}")
            print(f"   {specs_data['categories'][category]['description']}")
            print(f"   APIs: {len(category_specs)}")

            for spec_info in category_specs:
                await self.run_benchmark_for_spec(spec_info, category)

        print(f"\n✅ Benchmark complete! Total results: {len(self.results)}")

    def save_results(self, output_file: Path):
        """Speichert Ergebnisse als CSV"""
        if not self.results:
            print("⚠️  No results to save")
            return

        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=asdict(self.results[0]).keys())
            writer.writeheader()
            for result in self.results:
                writer.writerow(asdict(result))

        print(f"💾 Results saved to: {output_file}")

    def print_summary(self):
        """Druckt Zusammenfassung der Ergebnisse"""
        if not self.results:
            print("⚠️  No results to summarize")
            return

        print("\n" + "="*80)
        print("📊 BENCHMARK SUMMARY")
        print("="*80)

        # Gruppierung nach API
        apis = {}
        for result in self.results:
            if result.api_name not in apis:
                apis[result.api_name] = []
            apis[result.api_name].append(result)

        for api_name, api_results in apis.items():
            print(f"\n{api_name}:")

            # Ingest-Zeiten
            pg_writes = [r.pg_write_ms for r in api_results]
            chroma_writes = [r.chroma_write_ms for r in api_results]

            print(f"  Ingest (avg over {len(api_results)} runs):")
            print(f"    PgVector:  {statistics.mean(pg_writes):7.2f}ms (±{statistics.stdev(pg_writes):6.2f})")
            print(f"    ChromaDB:  {statistics.mean(chroma_writes):7.2f}ms (±{statistics.stdev(chroma_writes):6.2f})")

            # Query-Zeiten
            pg_queries = [r.pg_query_ms for r in api_results]
            chroma_queries = [r.chroma_query_ms for r in api_results]

            print(f"  Query (avg over {len(api_results)} queries):")
            print(f"    PgVector:  {statistics.mean(pg_queries):7.2f}ms (±{statistics.stdev(pg_queries):6.2f})")
            print(f"    ChromaDB:  {statistics.mean(chroma_queries):7.2f}ms (±{statistics.stdev(chroma_queries):6.2f})")

            # DB Größen
            if api_results[0].db_size_pg_mb > 0:
                print(f"  Database Size:")
                print(f"    PgVector:  {api_results[0].db_size_pg_mb:.2f} MB")
                print(f"    ChromaDB:  {api_results[0].db_size_chroma_mb:.2f} MB")


async def main():
    parser = argparse.ArgumentParser(description="Vector Database Benchmark Suite")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--runs", type=int, default=10, help="Number of runs per spec")
    parser.add_argument("--specs-file", default="api_specs_list.json", help="Path to specs list JSON")
    parser.add_argument("--output", default="benchmark_results.csv", help="Output CSV file")
    parser.add_argument("--categories", nargs="+", help="Categories to test (default: all)")

    args = parser.parse_args()

    # Pfade relativ zum Skript-Verzeichnis
    script_dir = Path(__file__).parent
    specs_file = script_dir / args.specs_file
    output_file = script_dir / args.output

    # Benchmark erstellen und ausführen
    benchmark = VectorDBBenchmark(api_url=args.api_url, runs_per_spec=args.runs)

    try:
        await benchmark.run_all_benchmarks(specs_file, args.categories)
        benchmark.save_results(output_file)
        benchmark.print_summary()
    except KeyboardInterrupt:
        print("\n⚠️  Benchmark interrupted by user")
        if benchmark.results:
            benchmark.save_results(output_file)
            benchmark.print_summary()
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
