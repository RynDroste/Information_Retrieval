# AFURI Menu Scraping and Search System

Scrape menu data from the AFURI website, clean and index it, and provide a frontend search interface.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Run Complete Pipeline

```bash
# Run complete pipeline (scrape -> clean -> index)
python3 run_pipeline.py

# Skip indexing if Solr is not running
python3 run_pipeline.py --skip-index

# Run and start frontend server
python3 run_pipeline.py --start-frontend
```

### 3. Use Frontend Interface

```bash
# Start frontend server
bash start_frontend.sh
# or
python3 -m http.server 8000
```

Open in browser: **http://localhost:8000/frontend/**

## 📖 Features

### Data Processing Pipeline

1. **Scraping** - Scrape menu, store, and brand information from AFURI website
2. **Cleaning** - Clean and normalize data, remove duplicates
3. **Indexing** - Index data to Solr (optional)
4. **Searching** - Search and browse through frontend interface

### Search Modes

- **Local Search**: Directly search JSON files, no Solr required
- **Solr Search**: Use Solr for more powerful search capabilities (requires Solr installation)

### Fuzzy Search Support

The search system supports fuzzy matching to handle typos and partial matches:

- **Wildcard Matching**: Uses `*word*` pattern for substring matching
- **Fuzzy Matching**: Uses Solr's fuzzy search (`word~2`) with edit distance of 2 for typo tolerance
- **Smart Query Building**: 
  - Short words (≤3 characters): Uses wildcard matching only
  - Longer words (>3 characters): Combines wildcard and fuzzy search for better results
- **Multi-field Search**: Searches across title, content, menu_item, and ingredients fields simultaneously

**Example**: Searching for "yuzu" will also match "yusu", "yuzo", "yuzu ramen", etc.

### Synonym Expansion

The search system includes synonym mapping to handle English-Japanese translations and related terms:

- **Automatic Synonym Expansion**: When you search for a term, the system automatically searches for its synonyms as well
- **Bidirectional Mapping**: Synonyms work in both directions (e.g., "salt" ↔ "shio")
- **Word Form Variations**: The system handles common word form variations:
  - Adjective forms: "salty" → "salt" → "shio"
  - Suffix handling: -y, -ly, -ed, -ing, -er, -est
- **Common Mappings**:
  - `salt`, `salty` ↔ `shio` (Japanese for salt)
  - `soy` ↔ `shoyu` (Japanese for soy sauce)
  - `egg` ↔ `nitamago`, `tamago` (Japanese for egg)
  - `pork` ↔ `chashu` (Japanese for pork)
  - `noodle` ↔ `ramen`, `men` (Japanese for noodles)
  - `spicy`, `spice` ↔ `kara`, `ratan` (Japanese for spicy)

**Examples**: 
- Searching for "salt" or "salty" will automatically also search for "shio", so you'll find "Shio Ramen" and "Yuzu Shio Ramen" in the results.
- Searching for "spicy" will also match "kara" and "ratan" variants.

## 🔧 Solr Setup (Optional)

### Installation and Startup

```bash
# macOS
brew install solr
solr start
solr create -c afuri_menu

# Linux
wget https://archive.apache.org/dist/solr/solr/8.11.2/solr-8.11.2.tgz
tar xzf solr-8.11.2.tgz
cd solr-8.11.2
./bin/solr start
./bin/solr create -c afuri_menu
```

### Index Data

```bash
python3 run_pipeline.py
# or only index
python3 run_pipeline.py --skip-scrape --skip-clean
```

### Solr Advantages

- ⚡ **Fast Search** - Optimized indexing, millisecond response times
- 🎯 **Smart Ranking** - Relevance scoring, most relevant results first
- 🔍 **Complex Queries** - Support for boolean queries, phrase search, etc.
- 📊 **Advanced Features** - Faceted search, highlighting, statistical analysis

## 📁 Project Structure

```
Information_Retrieval/
├── run_pipeline.py          # Main pipeline script
├── scraper.py               # Scraping module
├── data_cleaner.py          # Cleaning module
├── solr_indexer.py          # Indexing module
├── solr_proxy.py            # Solr proxy server
├── start_frontend.sh        # Frontend startup script
├── frontend/                # Frontend interface
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── data/                    # Data directory
    ├── scraped_data.json    # Raw data
    └── cleaned_data.json    # Cleaned data
```

## 🛠️ Common Commands

```bash
# Run complete pipeline
python3 run_pipeline.py

# Only scrape and clean
python3 run_pipeline.py --skip-index

# Only index
python3 run_pipeline.py --skip-scrape --skip-clean

# Check Solr status
solr status

# View data statistics
python3 -c "import json; data = json.load(open('data/cleaned_data.json')); print(f'Total {len(data)} menu items')"
```

## ❓ Troubleshooting

### Issue: Module not found
```bash
pip3 install -r requirements.txt
```

### Issue: Cannot access website
- Check network connection
- Verify https://afuri.com/menu/ is accessible

### Issue: Solr connection failed
- Verify Solr is running: `solr status`
- Verify core is created: `solr create -c afuri_menu`
- Check if port 8983 is occupied

### Issue: Frontend cannot load data
- Verify `python3 run_pipeline.py` has been run
- Verify `data/cleaned_data.json` file exists
- Check browser console for errors

## 📊 Data Format

Each menu item contains the following fields:

```json
{
  "url": "https://afuri.com/menu/",
  "title": "Menu - Yuzu Shio Ramen",
  "content": "Menu description...",
  "section": "Menu",
  "menu_item": "Yuzu Shio Ramen",
  "menu_category": "Ramen",
  "ingredients": "chicken & dashi based broth, yuzu..."
}
```

**Categories**: Ramen, Noodles, Side Dishes, Drinks, Chi-yu

## 📝 Notes

- Data uses UTF-8 encoding, supports Japanese characters
- Scripts automatically create `data/` directory
- Menu items are automatically categorized
- Solr is optional, local search works fine

---

**Last Updated**: 2025
