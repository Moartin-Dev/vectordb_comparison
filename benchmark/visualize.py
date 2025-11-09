#!/usr/bin/env python3
"""
Visualisierungs-Skript für Benchmark-Ergebnisse
Erstellt verschiedene Plots für die wissenschaftliche Arbeit
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import argparse
import numpy as np
import json


class BenchmarkVisualizer:
    """Erstellt Visualisierungen aus Benchmark-Daten"""

    def __init__(self, csv_file: Path, output_dir: Path):
        self.csv_file = csv_file
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)

        # Daten laden
        print(f"📊 Loading data from {csv_file}...")
        self.df = pd.read_csv(csv_file)
        print(f"✅ Loaded {len(self.df)} records")

        # LOC-Mapping aus api_specs_list.json laden
        self.loc_mapping = self._load_loc_mapping()

        # Seaborn Style
        sns.set_theme(style="whitegrid")
        plt.rcParams['figure.figsize'] = (12, 6)
        plt.rcParams['font.size'] = 10

        # Konsistente Farbpalette: PgVector = Blau, ChromaDB = Orange
        self.db_colors = {
            'PgVector': '#1f77b4',  # Blau
            'ChromaDB': '#ff7f0e'   # Orange
        }
        self.palette = [self.db_colors['PgVector'], self.db_colors['ChromaDB']]

    def _load_loc_mapping(self):
        """Lädt LOC-Informationen aus api_specs_list.json"""
        specs_file = self.csv_file.parent / 'api_specs_list.json'
        if not specs_file.exists():
            print(f"   ⚠️  api_specs_list.json not found at {specs_file}, LOC will be 0")
            return {}

        try:
            with open(specs_file, 'r') as f:
                specs_data = json.load(f)

            # Mapping erstellen: API-Name -> LOC
            loc_map = {}
            for category_data in specs_data['categories'].values():
                for spec in category_data['specs']:
                    loc_map[spec['name']] = spec.get('estimated_loc', 0)

            print(f"   ✅ Loaded LOC data for {len(loc_map)} APIs")
            return loc_map
        except Exception as e:
            print(f"   ⚠️  Failed to load LOC data: {e}")
            return {}

    def create_ingest_comparison(self):
        """Vergleicht Ingest-Performance zwischen PgVector und ChromaDB"""
        print("📈 Creating ingest performance comparison...")

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Daten vorbereiten
        ingest_data = []
        for _, row in self.df.iterrows():
            ingest_data.append({
                'API': row['api_name'],
                'Category': row['api_category'],
                'Database': 'PgVector',
                'Time (ms)': row['pg_write_ms']
            })
            ingest_data.append({
                'API': row['api_name'],
                'Category': row['api_category'],
                'Database': 'ChromaDB',
                'Time (ms)': row['chroma_write_ms']
            })

        ingest_df = pd.DataFrame(ingest_data)

        # Boxplot
        sns.boxplot(
            data=ingest_df,
            x='API',
            y='Time (ms)',
            hue='Database',
            palette=self.palette,
            ax=axes[0]
        )
        axes[0].set_title('Ingest-Performance-Vergleich (Boxplot)')
        axes[0].set_xlabel('API-Spezifikation')
        axes[0].set_ylabel('Schreibzeit (ms)')
        axes[0].tick_params(axis='x', rotation=45)
        axes[0].legend(title='Datenbank')

        # Barplot mit Durchschnittswerten
        avg_ingest = ingest_df.groupby(['API', 'Database'])['Time (ms)'].mean().reset_index()
        sns.barplot(
            data=avg_ingest,
            x='API',
            y='Time (ms)',
            hue='Database',
            palette=self.palette,
            ax=axes[1]
        )
        axes[1].set_title('Durchschnittliche Ingest-Performance')
        axes[1].set_xlabel('API-Spezifikation')
        axes[1].set_ylabel('Durchschnittliche Schreibzeit (ms)')
        axes[1].tick_params(axis='x', rotation=45)
        axes[1].legend(title='Datenbank')

        plt.tight_layout()
        output_file = self.output_dir / 'ingest_comparison.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"   ✅ Saved to {output_file}")
        plt.close()

    def create_query_comparison(self):
        """Vergleicht Query-Performance zwischen PgVector und ChromaDB"""
        print("📈 Creating query performance comparison...")

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Daten vorbereiten
        query_data = []
        for _, row in self.df.iterrows():
            query_data.append({
                'API': row['api_name'],
                'Category': row['api_category'],
                'Database': 'PgVector',
                'Time (ms)': row['pg_query_ms']
            })
            query_data.append({
                'API': row['api_name'],
                'Category': row['api_category'],
                'Database': 'ChromaDB',
                'Time (ms)': row['chroma_query_ms']
            })

        query_df = pd.DataFrame(query_data)

        # Boxplot
        sns.boxplot(
            data=query_df,
            x='API',
            y='Time (ms)',
            hue='Database',
            palette=self.palette,
            ax=axes[0]
        )
        axes[0].set_title('Query-Performance-Vergleich (Boxplot)')
        axes[0].set_xlabel('API-Spezifikation')
        axes[0].set_ylabel('Abfragezeit (ms)')
        axes[0].tick_params(axis='x', rotation=45)
        axes[0].legend(title='Datenbank')

        # Violin Plot
        sns.violinplot(
            data=query_df,
            x='API',
            y='Time (ms)',
            hue='Database',
            palette=self.palette,
            ax=axes[1],
            split=True
        )
        axes[1].set_title('Query-Performance-Verteilung (Violin Plot)')
        axes[1].set_xlabel('API-Spezifikation')
        axes[1].set_ylabel('Abfragezeit (ms)')
        axes[1].tick_params(axis='x', rotation=45)
        axes[1].legend(title='Datenbank')

        plt.tight_layout()
        output_file = self.output_dir / 'query_comparison.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"   ✅ Saved to {output_file}")
        plt.close()

    def create_category_comparison(self):
        """Vergleicht Performance nach API-Kategorien (small/medium/large)"""
        print("📈 Creating category-based comparison...")

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # Daten nach Kategorie gruppieren
        category_order = ['small', 'medium', 'large']

        # 1. Ingest Time by Category
        ingest_by_cat = []
        for _, row in self.df.iterrows():
            ingest_by_cat.append({
                'Category': row['api_category'],
                'Database': 'PgVector',
                'Time (ms)': row['pg_write_ms']
            })
            ingest_by_cat.append({
                'Category': row['api_category'],
                'Database': 'ChromaDB',
                'Time (ms)': row['chroma_write_ms']
            })

        ingest_cat_df = pd.DataFrame(ingest_by_cat)
        sns.boxplot(
            data=ingest_cat_df,
            x='Category',
            y='Time (ms)',
            hue='Database',
            palette=self.palette,
            order=category_order,
            ax=axes[0, 0]
        )
        axes[0, 0].set_title('Ingest-Zeit nach API-Kategorie')
        axes[0, 0].set_xlabel('Kategorie')
        axes[0, 0].set_ylabel('Schreibzeit (ms)')
        axes[0, 0].legend(title='Datenbank')

        # 2. Query Time by Category
        query_by_cat = []
        for _, row in self.df.iterrows():
            query_by_cat.append({
                'Category': row['api_category'],
                'Database': 'PgVector',
                'Time (ms)': row['pg_query_ms']
            })
            query_by_cat.append({
                'Category': row['api_category'],
                'Database': 'ChromaDB',
                'Time (ms)': row['chroma_query_ms']
            })

        query_cat_df = pd.DataFrame(query_by_cat)
        sns.boxplot(
            data=query_cat_df,
            x='Category',
            y='Time (ms)',
            hue='Database',
            palette=self.palette,
            order=category_order,
            ax=axes[0, 1]
        )
        axes[0, 1].set_title('Query-Zeit nach API-Kategorie')
        axes[0, 1].set_xlabel('Kategorie')
        axes[0, 1].set_ylabel('Abfragezeit (ms)')
        axes[0, 1].legend(title='Datenbank')

        # 3. Chunks vs Ingest Time
        axes[1, 0].scatter(
            self.df['num_chunks'],
            self.df['pg_write_ms'],
            alpha=0.6,
            label='PgVector',
            color=self.db_colors['PgVector'],
            s=50
        )
        axes[1, 0].scatter(
            self.df['num_chunks'],
            self.df['chroma_write_ms'],
            alpha=0.6,
            label='ChromaDB',
            color=self.db_colors['ChromaDB'],
            s=50
        )
        axes[1, 0].set_title('Ingest-Zeit vs. Anzahl Chunks')
        axes[1, 0].set_xlabel('Anzahl Chunks')
        axes[1, 0].set_ylabel('Schreibzeit (ms)')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)

        # 4. Speedup Ratio
        speedup_data = self.df.groupby('api_name').agg({
            'pg_write_ms': 'mean',
            'chroma_write_ms': 'mean',
            'pg_query_ms': 'mean',
            'chroma_query_ms': 'mean'
        }).reset_index()

        speedup_data['ingest_speedup'] = speedup_data['pg_write_ms'] / speedup_data['chroma_write_ms']
        speedup_data['query_speedup'] = speedup_data['pg_query_ms'] / speedup_data['chroma_query_ms']

        x = np.arange(len(speedup_data))
        width = 0.35

        axes[1, 1].bar(x - width/2, speedup_data['ingest_speedup'], width, label='Ingest', alpha=0.8)
        axes[1, 1].bar(x + width/2, speedup_data['query_speedup'], width, label='Query', alpha=0.8)
        axes[1, 1].axhline(y=1, color='r', linestyle='--', label='Gleiche Performance')
        axes[1, 1].set_title('PgVector/ChromaDB Speedup-Verhältnis')
        axes[1, 1].set_xlabel('API')
        axes[1, 1].set_ylabel('Speedup (>1 = PgVector langsamer)')
        axes[1, 1].set_xticks(x)
        axes[1, 1].set_xticklabels(speedup_data['api_name'], rotation=45, ha='right')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        output_file = self.output_dir / 'category_comparison.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"   ✅ Saved to {output_file}")
        plt.close()

    def create_statistical_summary(self):
        """Erstellt statistische Zusammenfassung als Tabelle"""
        print("📊 Creating statistical summary...")

        # Statistiken berechnen
        summary_data = []

        for api_name in self.df['api_name'].unique():
            api_df = self.df[self.df['api_name'] == api_name]

            summary_data.append({
                'API': api_name,
                'CATEGORY': api_df['api_category'].iloc[0],
                'LOC': self.loc_mapping.get(api_name, 0),
                'RUNS (N)': len(api_df),
                'CHUNKS (AVG)': int(api_df['num_chunks'].mean()),
                'PG INGEST (MS)': f"{api_df['pg_write_ms'].mean():.1f} ± {api_df['pg_write_ms'].std():.1f}",
                'CHROMA INGEST (MS)': f"{api_df['chroma_write_ms'].mean():.1f} ± {api_df['chroma_write_ms'].std():.1f}",
                'PG QUERY (MS)': f"{api_df['pg_query_ms'].mean():.1f} ± {api_df['pg_query_ms'].std():.1f}",
                'CHROMA QUERY (MS)': f"{api_df['chroma_query_ms'].mean():.1f} ± {api_df['chroma_query_ms'].std():.1f}",
                'PG SIZE (MB)': f"{api_df['db_size_pg_mb'].iloc[0]:.2f}",
                'CHROMA SIZE (MB)': f"{api_df['db_size_chroma_mb'].iloc[0]:.2f}",
            })

        summary_df = pd.DataFrame(summary_data)

        # Als Tabellen-Plot (größere Figur für bessere Lesbarkeit)
        fig, ax = plt.subplots(figsize=(16, len(summary_data) * 0.8 + 1.5))
        ax.axis('tight')
        ax.axis('off')

        table = ax.table(
            cellText=summary_df.values,
            colLabels=summary_df.columns,
            cellLoc='center',
            loc='center',
            bbox=[0, 0, 1, 1]
        )

        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2.5)

        # Automatische Spaltenbreite nur für lange Spalten (Ingest/Query mit ±)
        long_cols = [i for i, col in enumerate(summary_df.columns)
                     if 'INGEST' in col or 'QUERY' in col]
        if long_cols:
            table.auto_set_column_width(col=long_cols)

        # Setze fixe Breite für kurze/mittlere Spalten
        col_widths = {
            'CATEGORY': 0.10,
            'LOC': 0.08,
            'RUNS (N)': 0.08,
            'CHUNKS (AVG)': 0.10,
            'PG SIZE (MB)': 0.10,
            'CHROMA SIZE (MB)': 0.12
        }
        for col_name, width in col_widths.items():
            if col_name in summary_df.columns:
                col_idx = list(summary_df.columns).index(col_name)
                for j in range(len(summary_df) + 1):  # +1 für Header
                    table[(j, col_idx)].set_width(width)

        # Header-Style
        for i in range(len(summary_df.columns)):
            table[(0, i)].set_facecolor('#40466e')
            table[(0, i)].set_text_props(weight='bold', color='white')

        # Zeilen abwechselnd einfärben
        for i in range(1, len(summary_df) + 1):
            for j in range(len(summary_df.columns)):
                if i % 2 == 0:
                    table[(i, j)].set_facecolor('#f0f0f0')

        plt.title('Statistische Zusammenfassung der Benchmark-Ergebnisse', fontsize=14, pad=20, weight='bold')

        output_file = self.output_dir / 'statistical_summary.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"   ✅ Saved to {output_file}")
        plt.close()

        # Auch als CSV speichern
        csv_output = self.output_dir / 'statistical_summary.csv'
        summary_df.to_csv(csv_output, index=False)
        print(f"   ✅ Saved to {csv_output}")

    def create_database_size_comparison(self):
        """Vergleicht Datenbank-Größen"""
        print("📈 Creating database size comparison...")

        # Nur eindeutige Werte (pro API)
        size_data = self.df.groupby('api_name').agg({
            'db_size_pg_mb': 'first',
            'db_size_chroma_mb': 'first',
            'api_category': 'first'
        }).reset_index()

        if size_data['db_size_pg_mb'].sum() == 0:
            print("   ⚠️  No database size data available, skipping...")
            return

        fig, ax = plt.subplots(figsize=(10, 6))

        x = np.arange(len(size_data))
        width = 0.35

        ax.bar(x - width/2, size_data['db_size_pg_mb'], width, label='PgVector',
               color=self.db_colors['PgVector'], alpha=0.8)
        ax.bar(x + width/2, size_data['db_size_chroma_mb'], width, label='ChromaDB',
               color=self.db_colors['ChromaDB'], alpha=0.8)

        ax.set_title('Datenbankgröße-Vergleich')
        ax.set_xlabel('API-Spezifikation')
        ax.set_ylabel('Datenbankgröße (MB)')
        ax.set_xticks(x)
        ax.set_xticklabels(size_data['api_name'], rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        output_file = self.output_dir / 'database_size_comparison.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"   ✅ Saved to {output_file}")
        plt.close()

    def create_all_visualizations(self):
        """Erstellt alle Visualisierungen"""
        print("\n🎨 Creating all visualizations...")
        print("="*60)

        self.create_ingest_comparison()
        self.create_query_comparison()
        self.create_category_comparison()
        self.create_statistical_summary()
        self.create_database_size_comparison()

        print("\n" + "="*60)
        print(f"✅ All visualizations created in: {self.output_dir}")
        print("="*60)


def main():
    parser = argparse.ArgumentParser(description="Visualize Vector Database Benchmark Results")
    parser.add_argument("csv_file", help="Path to benchmark results CSV file")
    parser.add_argument("--output-dir", default="plots", help="Output directory for plots")

    args = parser.parse_args()

    csv_file = Path(args.csv_file)
    if not csv_file.exists():
        print(f"❌ CSV file not found: {csv_file}")
        return

    output_dir = Path(args.output_dir)

    visualizer = BenchmarkVisualizer(csv_file, output_dir)
    visualizer.create_all_visualizations()


if __name__ == "__main__":
    main()
