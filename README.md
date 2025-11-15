# AFURI Menu Scraping and Search System

A comprehensive information retrieval system for searching AFURI restaurant menu items, store information, and brand details with advanced search capabilities including synonym expansion, single-character matching, intelligent relevance ranking, and semantic search using LaBSE.

## 📑 Table of Contents

- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Semantic Search](#semantic-search)
- [Keyword Score Calculation](#keyword-score-calculation)
- [Troubleshooting](#troubleshooting)
- [Technical Details](#technical-details)

---

## Key Features

### 🔍 Advanced Search Capabilities

1. **Synonym Expansion** - Automatic bidirectional synonym mapping (English ↔ Japanese) via `solr_config/synonyms.txt`
2. **Single-Character Matching** - Prefix matching using `EdgeNGramFilterFactory` (minGramSize: 1, maxGramSize: 50)
3. **Intelligent Relevance Ranking** - Multi-field search with weighted scoring (`title^2.0`, `menu_item^2.5`, `store_name^3.0`)
4. **Category-Based Boosting** - Automatic category detection with dynamic boost queries (weights 5.0-7.0)
5. **Multi-Field Search** - Simultaneous search across title, content, menu_item, ingredients, menu_category, and store_name

### 🛠️ Technical Algorithms

- **Text Analysis**: StandardTokenizerFactory, LowerCaseFilterFactory, PorterStemFilterFactory, SynonymGraphFilterFactory, EdgeNGramFilterFactory, StopFilterFactory
- **Relevance Scoring**: BM25 (improved TF-IDF) with field boosting, phrase boost, and category boost
- **Query Processing**: eDismax parser with multi-field search (qf), phrase matching (pf), and boost queries (bq)
- **Data Pipeline**: Web scraping (BeautifulSoup) → Data cleaning → Solr indexing → Schema management

---

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

# Only update index (skip scrape/clean)
python3 run_pipeline.py --skip-scrape --skip-clean         # Without semantic
python3 run_pipeline.py --use-labse --skip-scrape --skip-clean  # With semantic
```

### Frontend Usage

- **Basic Search**: Enter keywords and press Enter
- **Filters**: Category, price range, tags, type (Menu/Store/Brand)

### Check Service Status

**Browser Console (F12)** - Simplest method:
- ✅ Enabled: `✓ Semantic search available (136 embeddings)`
- ℹ️ Disabled: `ℹ Semantic search API not available`

**Command Line**:
```bash
curl http://localhost:8888/solr/RamenProject/select?q=*:*&rows=1  # Solr proxy
curl http://localhost:8889/semantic/status                        # Semantic API
```

---

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
│   ├── managed-schema       # Solr schema (with synonym support)
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

---

## Semantic Search

### Overview

LaBSE (Language-agnostic BERT Sentence Embedding) provides semantic search that understands query meaning, not just keyword matching.

**How It Works**:
1. **Text → Vector**: Converts queries and documents into 768-dimensional vectors
2. **Similarity**: Calculates cosine similarity between vectors (0-1 range)
3. **Hybrid Ranking**: Combines keyword scores and semantic scores

### Generate Embeddings

```bash
# Complete process (scrape → clean → index + generate embeddings)
python3 run_pipeline.py --use-labse --configure-solr

# Or only re-index and generate embeddings (if data exists)
python3 run_pipeline.py --use-labse --skip-scrape --skip-clean
```

**Time**: First run ~5-10 min (download model), then ~2-3 min for 136 documents.

### Hybrid Search Ratio

**Current Configuration**: 50% Keyword + 50% Semantic

Edit `frontend/app.js` to adjust:
```javascript
keyword_weight: 0.5,  // Modify here
semantic_weight: 0.5   // Modify here
```

**Formula**: `Combined Score = (Keyword Weight × Keyword Score) + (Semantic Weight × Semantic Score)`

**Example Configurations**:
- Exact match priority: `keyword_weight: 0.8, semantic_weight: 0.2`
- Balanced mode: `keyword_weight: 0.6, semantic_weight: 0.4`
- Semantic priority: `keyword_weight: 0.3, semantic_weight: 0.7`

### LaBSE Advantages

- ✅ **Semantic Understanding**: Matches semantically related content even without exact keywords
- ✅ **Cross-language**: Supports multilingual search (English, Japanese, Chinese)
- ✅ **Context Awareness**: Understands word meanings in context

---

## Keyword Score Calculation

### Overview

**Keyword Score** is the normalized Solr raw score (0-1 range), completely independent of semantic search.

### Calculation Process

#### Step 1: Solr Raw Score (BM25 Algorithm)

**Influencing Factors**:
- **Term Frequency (TF)**: How often query term appears
- **Inverse Document Frequency (IDF)**: How rare the term is
- **Field Weights**: `title^2.0`, `menu_item^2.5`, `store_name^3.0`, `content^1.5`
- **Phrase Boost**: `title^5.0`, `menu_item^5.0`, `store_name^6.0`
- **Boost Queries**: Dynamic category-based boosting

**Example**: Searching "ramen" → `Menu_90_Ramen_soup_(salt)`: **1.603** (raw Solr score)

#### Step 2: Normalization

```python
if solr_score > 100:
    normalized_solr_score = min(1.0, solr_score / 100.0)
else:
    normalized_solr_score = min(1.0, solr_score / 10.0) if solr_score > 0 else 0
```

**Examples**:
- `1.603` → `0.160` (1.603 / 10)
- `0.500` → `0.050` (0.500 / 10)
- `150.0` → `1.000` (min(1.0, 150/100))

#### Step 3: Usage

- Used in hybrid search: `combined_score = (keyword_weight × keyword_score) + (semantic_weight × semantic_score)`
- Displayed in browser console (3 decimal places)

### Why Normalization?

1. **Unify Score Range**: Solr scores vary (0-10 or 0-100+), normalize to 0-1 for mixing with semantic scores
2. **Balance Score Types**: Both Keyword Score and Semantic Score are 0-1, can be directly combined
3. **Easy to Understand**: 1.0 = perfect match, 0.0 = no match

### Code Locations

- Frontend: `frontend/app.js` lines 80-90 (`calculateKeywordScore`), 99-108 (`addKeywordScores`)
- Backend: `semantic_search.py` lines 84-104

---

## Troubleshooting

### Common Issues

#### Q1: Cannot Access Frontend?

1. Check services are running (terminal output)
2. Check port: `lsof -i :8000`
3. Confirm URL: `http://localhost:8000/frontend/` (note trailing `/frontend/`)

#### Q2: Semantic Search Not Working?

1. Confirm used `--use-labse` or `bash start_frontend.sh true`
2. Check embedding file: `ls -lh data/embeddings.json`
3. Check API status: `curl http://localhost:8889/semantic/status`
4. View browser console (F12)

#### Q3: Semantic Search API Responds But Not Available?

**Problem**: API running but embeddings missing or model not loaded.

**Solution 1: Restart API** (if embeddings exist)
```bash
# Stop API (Ctrl+C), then restart
python3 semantic_api.py
# Or use script
bash start_frontend.sh true
```

**Solution 2: Regenerate Embeddings** (if file missing/corrupted)
```bash
python3 run_pipeline.py --use-labse --skip-scrape --skip-clean
python3 semantic_api.py
```

**Check Steps**:
```bash
# Check file exists
ls -lh data/embeddings.json

# Check content
python3 -c "import json; data = json.load(open('data/embeddings.json')); print(f'Embeddings: {len(data)}')"

# Check API status
curl http://localhost:8889/semantic/status
```

#### Q4: Solr Connection Failed?

1. **Confirm Solr is running** (most important):
   ```bash
   curl http://localhost:8983/solr/admin/ping
   ```
   - If fails, start Solr server first
   - Default: `http://localhost:8983`
2. Check Solr core: `curl http://localhost:8983/solr/admin/cores?action=STATUS`
3. If not installed, install Solr first

#### Q5: Search Speed Slow?

- First semantic search is slower (loads model)
- Subsequent searches are faster
- Skip `--use-labse` if semantic search not needed

#### Q6: How to Stop Services?

Press `Ctrl+C` in the terminal. If using `start_frontend.sh`, stops all services.

### Check Semantic Search Status

**Method 1: Browser Console (F12)** - Simplest
- ✅ Enabled: `✓ Semantic search available (136 embeddings)`
- ℹ️ Disabled: `ℹ Semantic search API not available`

**Method 2: API Check**
```bash
curl http://localhost:8889/semantic/status
```

**Method 3: Check File**
```bash
ls -lh data/embeddings.json
```

### View Search Scores

**Browser Console (F12)**:
1. Open `http://localhost:8000/frontend/`
2. Press F12 → Console tab
3. Execute search
4. View detailed score tables:
   - Solr Keyword Search Results (with Solr Score)
   - Semantic Search Scores (with Keyword Score, Semantic Score, Combined Score)
   - Final Ranking (with all scores)

**Score Explanation**:
- **Keyword Score**: Normalized Solr score (0-1)
- **Semantic Score**: LaBSE similarity (0-1)
- **Combined Score**: Hybrid = Keyword(50%) + Semantic(50%)

---

## Technical Details

### Solr Native Features vs Our Implementation

**Solr Provides**:
- Multi-field search (qf)
- Phrase matching (pf)
- Boost queries (bq)
- Minimum match (mm)

**Solr Limitations**:
- ❌ Cannot auto-identify keyword types
- ❌ Cannot dynamically adjust weights
- ❌ Cannot understand business semantics

**Our Implementation**:
- Keyword semantic recognition (brand, category, type)
- Intelligent combination detection
- Dynamic weight adjustment
- Priority rules: Category > Brand > Type

### Hybrid Search Solution

1. **Solr Keyword Search**: Fast document finding
2. **LaBSE Semantic Search**: Semantic similarity calculation
3. **Score Fusion**: `Final Score = (Keyword Weight × Keyword Score) + (Semantic Weight × Semantic Score)`

**Advantages**:
- ✅ Semantic understanding
- ✅ Cross-language support
- ✅ Synonym handling
- ✅ Flexible weight adjustment

### Performance

- **Embedding Generation**: First run ~5-10 min (download), then ~1-2 min per 100 docs
- **Search Performance**: Keyword < 100ms, Semantic reranking < 200ms, Total < 300ms
- **Storage**: ~3KB per document (768-dim vector), 136 docs ~400KB

### Service Ports

| Service | Port | Description |
|---------|------|-------------|
| Solr Server | 8983 | Main server (start separately) |
| Solr Proxy | 8888 | Frontend access proxy |
| Semantic Search API | 8889 | Semantic API (optional) |
| Frontend Server | 8000 | Web frontend |

---

## Complete Command Reference

```bash
# Basic usage
python3 run_pipeline.py --configure-solr --start-frontend

# With semantic search
python3 run_pipeline.py --use-labse --configure-solr --start-frontend

# Start frontend only (data exists)
bash start_frontend.sh              # Without semantic
bash start_frontend.sh true         # With semantic

# Skip steps
python3 run_pipeline.py --skip-scrape              # Skip scraping
python3 run_pipeline.py --skip-scrape --skip-clean # Only index

# Check services
curl http://localhost:8888/solr/RamenProject/select?q=*:*&rows=1  # Solr proxy
curl http://localhost:8889/semantic/status                        # Semantic API
```
