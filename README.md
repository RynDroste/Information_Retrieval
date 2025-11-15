# AFURI Menu Scraping and Search System

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
