# Ramen Restaurant Search System

A comprehensive information retrieval system for searching Ramen restaurant menu items and store information with advanced search capabilities including synonym expansion, intelligent relevance ranking, and semantic search using LaBSE.

## Quick Start

> ⚠️ **Important**: Make sure the **Solr server is started** before running the project!
> 
> Solr runs on `http://localhost:8983` by default. Check with: `curl http://localhost:8983/solr/admin/ping`

### Prerequisites

1. **Python 3.7+**
2. **Solr Server Running** (required) - Default: `http://localhost:8983`

### First Time Use

#### Basic Version (Keyword Search Only)

```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Run complete pipeline (auto-start frontend)
python3 run_pipeline.py --configure-solr --start-frontend
```

**Done!** Open browser: **http://localhost:8000/frontend/**

#### Full Version (With Semantic Search) ⭐ Recommended

```bash
# 1. Install semantic search dependencies
pip3 install sentence-transformers numpy torch

# 2. Run complete pipeline (with semantic search)
python3 run_pipeline.py --use-labse --configure-solr --start-frontend
```

**Note**: First run downloads LaBSE model (~1.2GB), takes 5-10 minutes.

### Daily Use

```bash
# Start frontend (data already exists)
bash start_frontend.sh              # Without semantic search
bash start_frontend.sh true         # With semantic search

# Re-index after data update
python3 run_pipeline.py --configure-solr                    # Without semantic
python3 run_pipeline.py --use-labse --configure-solr        # With semantic
```

## Key Features

- **Synonym Expansion** - Automatic bidirectional synonym mapping (English ↔ Japanese)
- **Single-Character Matching** - Prefix matching for partial queries
- **Intelligent Relevance Ranking** - Multi-field search with weighted scoring
- **Semantic Search** - LaBSE-based semantic understanding for cross-language search
- **Multi-Field Search** - Simultaneous search across title, content, menu_item, ingredients, and store_name
- **Filters**: Category, price range, tags, type (Menu/Store)

## Project Structure

```
Information_Retrieval/
├── run_pipeline.py          # Main pipeline script
├── scraper.py               # Scraping module
├── data_cleaner.py          # Cleaning module
├── solr_indexer.py          # Indexing module
├── labse_embedder.py        # LaBSE embedding generator
├── semantic_search.py       # Semantic search module
├── semantic_api.py          # Semantic search API server
├── solr_proxy.py            # Solr proxy server
├── start_frontend.sh        # Frontend startup script
├── requirements.txt         # Python dependencies
├── solr_config/             # Solr configuration files
│   ├── managed-schema       # Solr schema
│   ├── solrconfig.xml       # Solr configuration
│   ├── synonyms.txt         # Synonym mappings
│   └── stopwords.txt        # Stop words
├── frontend/                # Frontend interface
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── data/                    # Data directory
    ├── scraped_data.json    # Raw scraped data
    ├── cleaned_data.json     # Cleaned data
    └── embeddings.json       # LaBSE embeddings (generated with --use-labse)
```

## Semantic Search

LaBSE (Language-agnostic BERT Sentence Embedding) provides semantic search that understands query meaning, not just keyword matching.

**How It Works**:
1. Converts queries and documents into 768-dimensional vectors
2. Calculates cosine similarity between vectors
3. Combines keyword scores and semantic scores (50% each by default)

**Generate Embeddings**:
```bash
python3 run_pipeline.py --use-labse --configure-solr
```

**Time**: First run ~5-10 min (download model), then ~2-3 min for documents.

## Troubleshooting

### Cannot Access Frontend?

1. Check services are running (terminal output)
2. Check port: `lsof -i :8000`
3. Confirm URL: `http://localhost:8000/frontend/` (note trailing `/frontend/`)

### Semantic Search Not Working?

1. Confirm used `--use-labse` or `bash start_frontend.sh true`
2. Check embedding file: `ls -lh data/embeddings.json`
3. Check API status: `curl http://localhost:8889/semantic/status`
4. View browser console (F12)

### Solr Connection Failed?

1. **Confirm Solr is running**:
   ```bash
   curl http://localhost:8983/solr/admin/ping
   ```
   - If fails, start Solr server first
   - Default: `http://localhost:8983`

### Check Semantic Search Status

**Browser Console (F12)**:
- ✅ Enabled: `✓ Semantic search available (X embeddings)`
- ℹ️ Disabled: `ℹ Semantic search API not available`

**API Check**:
```bash
curl http://localhost:8889/semantic/status
```

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| Solr Server | 8983 | Main server (start separately) |
| Solr Proxy | 8888 | Frontend access proxy |
| Semantic Search API | 8889 | Semantic API (optional) |
| Frontend Server | 8000 | Web frontend |
