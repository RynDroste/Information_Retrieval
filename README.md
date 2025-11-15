# AFURI Menu Scraping and Search System

A comprehensive information retrieval system for searching AFURI restaurant menu items, store information, and brand details with advanced search capabilities including synonym expansion, single-character matching, and intelligent relevance ranking.

## Key Features

### 🔍 Advanced Search Capabilities

1. **Synonym Expansion**
   - Automatic bidirectional synonym mapping (English ↔ Japanese)
   - Examples: "salt" ↔ "shio", "soy" ↔ "shoyu", "pork" ↔ "chashu"
   - Configured via `solr_config/synonyms.txt`
   - Powered by Solr's `SynonymGraphFilterFactory`

2. **Single-Character Matching**
   - Prefix matching: typing "r" matches "ramen"
   - Implemented using `EdgeNGramFilterFactory` (minGramSize: 1, maxGramSize: 50)
   - Supports incremental search and autocomplete-like behavior

3. **Intelligent Relevance Ranking**
   - Multi-field search with weighted scoring
   - Field weights: `title^2.0`, `menu_item^2.5`, `content^1.5`, `store_name^3.0`
   - Phrase matching boost: `title^3.0`, `menu_item^3.0`, `store_name^4.0`
   - Uses Solr's eDismax query parser for optimal relevance

4. **Category-Based Boosting**
   - Automatic category detection and boosting
   - Search "store" → prioritizes Store Information
   - Search "drink" → prioritizes Drinks category
   - Search "afuri" → prioritizes Brand Information, then Store Information
   - Dynamic boost queries (bq) with weights 5.0-7.0

5. **Multi-Field Search**
   - Simultaneous search across title, content, menu_item, ingredients, menu_category, and store_name
   - Field-specific relevance scoring
   - Phrase matching for exact term combinations

### 🛠️ Technical Algorithms

1. **Text Analysis Pipeline**
   - **Tokenizer**: StandardTokenizerFactory (word boundary detection)
   - **Lowercasing**: LowerCaseFilterFactory (case-insensitive search)
   - **Stemming**: PorterStemFilterFactory (word root extraction)
   - **Synonym Expansion**: SynonymGraphFilterFactory (bidirectional mapping)
   - **N-Gram Generation**: EdgeNGramFilterFactory (prefix matching)
   - **Stop Word Removal**: StopFilterFactory (common word filtering)

2. **Relevance Scoring Algorithm**
   - **BM25 (Best Matching 25)**: Solr's default scoring algorithm, an improved version of TF-IDF
   - **TF-IDF Components**:
     - **Term Frequency (TF)**: How often a term appears in a document
     - **Inverse Document Frequency (IDF)**: How rare a term is across all documents
     - Calculated automatically by Solr/Lucene during indexing and querying
   - **Field Boosting**: Multiplies TF-IDF scores with field-specific weights (e.g., `title^2.0`)
   - **Phrase Boost**: Additional scoring multiplier for exact phrase matches (e.g., `title^3.0`)
   - **Category Boost**: Context-aware boost queries (bq) that add to base TF-IDF scores
   - **Section Prioritization**: Brand > Store > Menu based on query context using boost queries
   
   **How TF-IDF is Applied:**
   - Solr automatically calculates TF-IDF for each term in indexed documents
   - Field weights (`qf` parameter) multiply the base TF-IDF scores
   - Phrase matching (`pf` parameter) provides additional relevance boost
   - Boost queries (`bq` parameter) add context-specific scoring on top of TF-IDF
   - Final score = (TF-IDF base score) × (field weight) + (phrase boost) + (category boost)

3. **Query Processing**
   - **eDismax Parser**: Extended DisMax for flexible query parsing
   - **Query Field (qf)**: Multi-field search with weights
   - **Phrase Field (pf)**: Phrase matching with higher weights
   - **Boost Query (bq)**: Context-aware relevance boosting

4. **Data Processing Pipeline**
   - **Web Scraping**: BeautifulSoup-based content extraction
   - **Data Cleaning**: Normalization, deduplication, and categorization
   - **Indexing**: Batch processing with Solr for fast retrieval
   - **Schema Management**: Dynamic field type configuration via Solr Schema API

## Quick Start

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Run Complete Pipeline

```bash
# Run complete pipeline with Solr configuration and start frontend (recommended)
python3 run_pipeline.py --configure-solr --start-frontend

# Run complete pipeline (scrape -> clean -> index)
python3 run_pipeline.py

# Run complete pipeline with Solr configuration only
python3 run_pipeline.py --configure-solr

# Skip scraping, only clean and index
python3 run_pipeline.py --skip-scrape

# Only index (assuming cleaned data exists)
python3 run_pipeline.py --skip-scrape --skip-clean

# Start frontend manually
bash start_frontend.sh
```

### 3. Access Frontend

Open your browser and navigate to: **http://localhost:8000/frontend/**

> **Note:** When using `--start-frontend`, the frontend server will start automatically after the pipeline completes. Press `Ctrl+C` to stop the server.

## Project Structure

```
Information_Retrieval/
├── run_pipeline.py          # Main pipeline script
├── scraper.py               # Scraping module
├── data_cleaner.py          # Cleaning module
├── solr_indexer.py          # Indexing module
├── solr_proxy.py            # Solr proxy server
├── start_frontend.sh        # Frontend startup script
├── requirements.txt         # Python dependencies
├── solr_config/             # Solr configuration files
│   ├── managed-schema       # Solr schema with synonym support
│   ├── solrconfig.xml       # Solr configuration
│   ├── synonyms.txt         # Synonym mappings
│   └── stopwords.txt        # Stop words
├── frontend/                # Frontend interface
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── data/                    # Data directory
    ├── scraped_data.json    # Raw scraped data
    └── cleaned_data.json     # Cleaned data
```
