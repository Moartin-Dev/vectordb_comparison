# Vector Database Benchmark Suite

Vollständiges Benchmark-System für die Performance-Analyse von PgVector vs. ChromaDB im Rahmen der wissenschaftlichen Arbeit.

## 📁 Inhalt

- `api_specs_list.json` - Kuratierte Liste von OpenAPI-Spezifikationen (small/medium/large)
- `benchmark.py` - Haupt-Benchmark-Skript
- `visualize.py` - Visualisierungs-Skript für Ergebnisse
- `requirements.txt` - Python-Dependencies für Benchmark-Tools

## 🚀 Schnellstart

### 1. Installation

```bash
cd benchmark
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 2. API starten

Stelle sicher, dass die Vector Database API läuft:

```bash
cd ..
docker compose up -d
```

### 3. Benchmark ausführen

**Kleiner Test (nur small APIs, 3 Runs):**
```bash
python benchmark.py --runs 3 --categories small
```

**Vollständiger Benchmark (alle APIs, 10 Runs):**
```bash
python benchmark.py --runs 10
```

**Nur bestimmte Kategorien:**
```bash
python benchmark.py --runs 10 --categories medium large
```

**Custom API-URL:**
```bash
python benchmark.py --api-url http://192.168.1.100:8000 --runs 5
```

### 4. Ergebnisse visualisieren

```bash
python visualize.py benchmark_results.csv --output-dir plots
```

Dies erstellt folgende Plots im `plots/` Verzeichnis:
- `ingest_comparison.png` - Vergleich der Ingest-Performance
- `query_comparison.png` - Vergleich der Query-Performance
- `category_comparison.png` - Performance nach API-Kategorie
- `database_size_comparison.png` - Speicherplatz-Vergleich
- `statistical_summary.png` - Statistische Zusammenfassung als Tabelle
- `statistical_summary.csv` - Zusammenfassung als CSV

## 📊 Benchmark-Optionen

```bash
python benchmark.py --help
```

**Optionen:**
- `--api-url` - API Base URL (default: http://localhost:8000)
- `--runs` - Anzahl Durchläufe pro Spec (default: 10)
- `--specs-file` - Pfad zur Specs-Liste (default: api_specs_list.json)
- `--output` - Output CSV-Datei (default: benchmark_results.csv)
- `--categories` - Kategorien zum Testen (default: alle)

## 📈 Visualisierungs-Optionen

```bash
python visualize.py --help
```

**Optionen:**
- `csv_file` - Pfad zur Benchmark-CSV (required)
- `--output-dir` - Output-Verzeichnis für Plots (default: plots)

## 🔬 Was wird gemessen?

Für jede API-Spezifikation und jeden Durchlauf:

**Ingest-Metriken:**
- `embed_ms` - Zeit für Embedding-Erstellung (Ollama)
- `pg_write_ms` - Schreibzeit in PgVector
- `chroma_write_ms` - Schreibzeit in ChromaDB
- `num_chunks` - Anzahl der erzeugten Chunks

**Query-Metriken:**
- `query_embed_ms` - Zeit für Query-Embedding
- `pg_query_ms` - Suchzeit in PgVector
- `chroma_query_ms` - Suchzeit in ChromaDB
- `pg_num_results` - Anzahl Ergebnisse (PgVector)
- `chroma_num_results` - Anzahl Ergebnisse (ChromaDB)

**Speicher-Metriken:**
- `db_size_pg_mb` - Datenbankgröße PgVector (MB)
- `db_size_chroma_mb` - Datenbankgröße ChromaDB (MB)

## 📝 API-Spezifikationen anpassen

Bearbeite `api_specs_list.json`, um eigene APIs hinzuzufügen:

```json
{
  "categories": {
    "custom": {
      "description": "Eigene Test-APIs",
      "specs": [
        {
          "name": "Meine API",
          "url": "https://example.com/openapi.yaml",
          "provider": "Mein Provider",
          "estimated_loc": 1000
        }
      ]
    }
  }
}
```

## 🎯 Verwendung für wissenschaftliche Arbeit

### Empfohlenes Vorgehen:

1. **Testlauf:**
   ```bash
   python benchmark.py --runs 3 --categories small
   ```

2. **Vollständiger Benchmark:**
   ```bash
   python benchmark.py --runs 20 --output results_main.csv
   ```
   - Mindestens 10-20 Runs für statistische Signifikanz
   - Alle Kategorien testen

3. **Visualisierung:**
   ```bash
   python visualize.py results_main.csv --output-dir thesis_plots
   ```

4. **Ergebnisse analysieren:**
   - `thesis_plots/statistical_summary.csv` für Tabellen in der Arbeit
   - PNG-Dateien für Abbildungen
   - Rohdaten in `results_main.csv` für weitere Analysen

### Wichtig für Reproduzierbarkeit:

- Dokumentiere die exakte Version aller Tools (`docker compose version`, `python --version`)
- Notiere Systemspezifikationen (CPU, RAM, SSD/HDD)
- Führe Benchmarks mehrmals durch und verwende Durchschnittswerte
- Schließe alle anderen Anwendungen während des Benchmarks

## 🛠️ Troubleshooting

**Problem: "Connection refused"**
```bash
# API prüfen
curl http://localhost:8000/health

# Container-Status prüfen
docker compose ps

# Logs ansehen
docker compose logs api
```

**Problem: "No module named 'pandas'"**
```bash
# Requirements installieren
pip install -r requirements.txt
```

**Problem: "API spec download failed"**
- Überprüfe Internet-Verbindung
- URL in `api_specs_list.json` könnte veraltet sein
- Teste URL manuell im Browser

**Problem: Benchmark dauert sehr lange**
- Reduziere `--runs` Parameter
- Teste nur eine Kategorie: `--categories small`
- Verwende kleinere API-Specs

## 📚 Weitere Ressourcen

- **API-Dokumentation:** `../CLAUDE.md`
- **OpenAPI-Specs:** [apis.guru](https://apis.guru/)
- **Stripe OpenAPI:** [github.com/stripe/openapi](https://github.com/stripe/openapi)
- **GitHub OpenAPI:** [github.com/github/rest-api-description](https://github.com/github/rest-api-description)
