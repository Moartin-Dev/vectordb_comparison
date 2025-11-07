# 🚀 Benchmark Quickstart Guide

Schnelleinstieg für die Performance-Analyse im Rahmen der wissenschaftlichen Arbeit.

## ✅ Voraussetzungen

1. **Docker Services laufen:**
   ```bash
   cd /home/martin/Dokumente/Dev/vectordb_comparison
   docker compose ps
   ```
   Alle Services sollten "Up" sein.

2. **API ist erreichbar:**
   ```bash
   curl http://localhost:8000/health
   # Erwartete Ausgabe: {"status":"ok"}
   ```

## 📦 Setup (Einmalig)

```bash
# In das Benchmark-Verzeichnis wechseln
cd /home/martin/Dokumente/Dev/vectordb_comparison/benchmark

# Virtual Environment erstellen
python3 -m venv venv

# Aktivieren
source venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt
```

## 🧪 Test-Lauf (empfohlen vor vollständigem Benchmark)

```bash
# Kleiner Test mit nur 2 APIs, 3 Durchläufe
python benchmark.py --runs 3 --categories small

# Sollte ~2-5 Minuten dauern
# Output: benchmark_results.csv
```

**Erwartete Ausgabe:**
```
🚀 Starting Vector Database Benchmark Suite
📊 API URL: http://localhost:8000
🔁 Runs per spec: 3

================================================================================
Benchmarking: JSONPlaceholder (small)
...
✅ Benchmark complete! Total results: 15
```

## 🔬 Vollständiger Benchmark für die Arbeit

```bash
# Alle APIs, 20 Durchläufe (empfohlen für statistische Signifikanz)
python benchmark.py --runs 20 --output thesis_results.csv

# Dauert ca. 30-60 Minuten, abhängig von:
# - Anzahl und Größe der APIs
# - Netzwerkgeschwindigkeit (API-Specs herunterladen)
# - Systemleistung
```

**Tipp:** Lass den Benchmark über Nacht laufen:
```bash
nohup python benchmark.py --runs 20 --output thesis_results.csv > benchmark.log 2>&1 &
# Fortschritt verfolgen:
tail -f benchmark.log
```

## 📊 Ergebnisse visualisieren

```bash
# Plots erstellen (300 DPI, publikationsreif)
python visualize.py thesis_results.csv --output-dir thesis_plots

# Erstellt im Verzeichnis thesis_plots/:
# - ingest_comparison.png
# - query_comparison.png
# - category_comparison.png
# - database_size_comparison.png
# - statistical_summary.png
# - statistical_summary.csv (für Tabellen in der Arbeit)
```

## 📈 Ergebnisse für die Arbeit verwenden

### 1. Tabellen

**Datei:** `thesis_plots/statistical_summary.csv`

Öffne in Excel/LibreOffice und kopiere in deine Arbeit. Enthält:
- Durchschnittswerte
- Standardabweichungen
- Anzahl Durchläufe

### 2. Abbildungen

**Dateien:** Alle `.png` Dateien in `thesis_plots/`

- 300 DPI (druckqualität)
- Professionelle Seaborn-Themes
- Beschriftete Achsen
- Legende

**Beispiel-Bildunterschriften:**

> **Abbildung 1:** Vergleich der Ingest-Performance zwischen PgVector und ChromaDB für verschiedene API-Kategorien. Boxplot zeigt Median, Quartile und Ausreißer über 20 Durchläufe.

> **Abbildung 2:** Query-Latenz-Verteilung (Violin Plot) für PgVector und ChromaDB. Breitere Bereiche indizieren höhere Varianz.

### 3. Statistische Auswertung

**Rohdaten:** `thesis_results.csv`

Importiere in Python/R für weitere Analysen:
- T-Tests
- ANOVA
- Effektstärken
- Konfidenzintervalle

**Python-Beispiel:**
```python
import pandas as pd
from scipy import stats

df = pd.read_csv('thesis_results.csv')

# Vergleiche PgVector vs ChromaDB Ingest-Zeit
pg_ingest = df['pg_write_ms']
chroma_ingest = df['chroma_write_ms']

# T-Test
t_stat, p_value = stats.ttest_rel(pg_ingest, chroma_ingest)
print(f"T-Statistik: {t_stat:.4f}")
print(f"P-Wert: {p_value:.4f}")
```

## 🔧 Anpassungen

### Eigene APIs hinzufügen

Bearbeite `api_specs_list.json`:

```json
{
  "categories": {
    "medium": {
      "specs": [
        {
          "name": "TARDIS Internal API",
          "url": "https://your-company.com/api/openapi.yaml",
          "provider": "Your Company",
          "estimated_loc": 2000
        }
      ]
    }
  }
}
```

**Wichtig:** URL muss öffentlich zugänglich sein!

### Nur bestimmte APIs testen

```bash
# Nur medium und large
python benchmark.py --categories medium large --runs 10
```

### Weniger Queries pro API

Bearbeite `benchmark.py`, Zeile 86 (Funktion `generate_queries`):
```python
def generate_queries(self, api_name: str, category: str) -> List[str]:
    return [
        f"API endpoints for {api_name}",
        # Weitere Queries auskommentieren für schnellere Tests
    ]
```

## 🐛 Troubleshooting

### Problem: "Connection refused"

```bash
# API-Status prüfen
docker compose logs api | tail -20

# API neu starten
cd /home/martin/Dokumente/Dev/vectordb_comparison
docker compose restart api

# Warten bis ready
sleep 10
curl http://localhost:8000/health
```

### Problem: Benchmark sehr langsam

**Ursachen:**
1. Große API-Specs werden heruntergeladen → Erste Durchläufe dauern länger
2. Ollama lädt Embedding-Model beim ersten Mal → Retry-Mechanismus greift
3. Viele Chunks → Mehr Embedding-Zeit

**Lösung:**
```bash
# Nur kleine APIs testen
python benchmark.py --categories small --runs 5

# Oder weniger Durchläufe
python benchmark.py --runs 5
```

### Problem: "ModuleNotFoundError: No module named 'pandas'"

```bash
# Sicherstellen, dass venv aktiviert ist
source venv/bin/activate

# Requirements nochmal installieren
pip install -r requirements.txt
```

### Problem: API-Spec Download schlägt fehl

**Beispiel-Error:**
```
❌ Failed to download: HTTP 404
```

**Lösung:**
1. URL im Browser testen
2. In `api_specs_list.json` aktualisieren oder API entfernen
3. Alternativ: Nur funktionierende Kategorien testen:
   ```bash
   python benchmark.py --categories small
   ```

## 💡 Best Practices

### Für reproduzierbare Ergebnisse:

1. **Keine anderen Anwendungen laufen lassen** während Benchmark
2. **Laptop am Netzteil** (keine Energiespar-Modi)
3. **Stabile Internet-Verbindung** (für API-Spec Downloads)
4. **Mehrere Durchläufe**: Mind. 10, besser 20
5. **Dokumentieren**:
   - System-Specs (CPU, RAM, SSD)
   - Docker-Versionen (`docker --version`, `docker compose version`)
   - Datum und Uhrzeit der Benchmarks

### Beispiel-Dokumentation für Arbeit:

> **Testumgebung:**
> - **System:** Dell XPS 15 (Intel i7-11800H, 16GB RAM, NVMe SSD)
> - **OS:** Ubuntu 24.04 LTS
> - **Docker:** Version 24.0.7, Compose v2.23.0
> - **Datum:** 2025-01-15
> - **Durchläufe:** 20 pro API-Spezifikation
> - **APIs getestet:** 8 (2 small, 3 medium, 3 large)

## 📚 Weiterführende Informationen

- **Detaillierte Dokumentation:** `README.md`
- **API-Dokumentation:** `../CLAUDE.md`
- **Projekt-Übersicht:** `../README.md`

## ✨ Viel Erfolg bei deiner Arbeit!

Bei Fragen oder Problemen: Dokumentation lesen oder Claude Code um Hilfe fragen 😊
