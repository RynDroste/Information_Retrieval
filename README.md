# Information Retrieval Project - AFURI Menu Scraper

A web scraping project for extracting menu data from AFURI website, with data cleaning, Solr integration, and frontend display capabilities.

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Data Format](#data-format)
- [Troubleshooting](#troubleshooting)

## 🎯 Project Overview

This project is designed to:
1. **Scrape** menu data from https://afuri.com/menu/
2. **Clean** and process the scraped data
3. **Index** data into Solr for search functionality
4. **Display** data through a frontend interface

All components are complete and ready to use!

## ✨ Features

- ✅ Web scraping with `requests` and `BeautifulSoup`
- ✅ Automatic menu item extraction and categorization
- ✅ Data export to JSON format
- ✅ Data cleaning and normalization
- ✅ Solr integration for search functionality
- ✅ Frontend web interface with search and category filtering

## 📦 Requirements

- Python 3.7 or higher
- pip (Python package manager)
- Apache Solr (optional, for Solr search functionality)

## 🚀 Installation

### Step 1: Install Dependencies

```bash
pip3 install -r requirements.txt
```

This will install:
- `requests` - For HTTP requests
- `beautifulsoup4` - For HTML parsing
- `lxml` - For faster HTML parsing
- `pysolr` - For Solr integration (optional, only needed for Solr search)

### Step 2: Setup Solr (Optional)

If you want to use Solr search functionality, see `solr_setup.md` for detailed instructions.

## 📖 Usage

### 1. Scraping Data

Run the scraper to collect menu data:

```bash
python3 scraper.py
```

**What it does:**
- Fetches the AFURI menu page
- Extracts menu items with categories
- Saves data to `data/scraped_data.json`

**Example output:**
```
Starting to scrape AFURI menu page: https://afuri.com/menu/
Scraping: https://afuri.com/menu/

Extracting menu items...
    ✓ Menu item: Yuzu Shio Ramen (Ramen)
    ✓ Menu item: Yuzu Shoyu Ramen (Ramen)
    ...

Menu scraping completed! Retrieved 58 menu items
Data saved to: data/scraped_data.json
```

### 2. Cleaning Data

Clean the scraped data to improve quality:

```bash
python3 data_cleaner.py
```

**What it does:**
- Removes HTML tags and entities
- Normalizes whitespace and special characters
- Filters out invalid items
- Removes duplicate items
- Validates content

**Output:**
- Cleaned data is saved to `data/cleaned_data.json`
- Original scraped data remains in `data/scraped_data.json`

### 3. Indexing Data into Solr

Index cleaned data into Apache Solr for advanced search functionality:

**Prerequisites:**
- Apache Solr installed and running
- A Solr core named `afuri_menu` created

See `solr_setup.md` for detailed Solr setup instructions.

**Index data:**
```bash
python3 solr_indexer.py
```

**Options:**
```bash
# Custom Solr URL
python3 solr_indexer.py --solr-url http://localhost:8983/solr/afuri_menu

# Keep existing documents (append instead of replacing)
python3 solr_indexer.py --keep-existing
```

### 4. Using the Frontend

Open the web interface to search and browse menu items:

**Option 1: Simple HTTP Server (Recommended)**

```bash
# Python 3
python3 -m http.server 8000
```

Then open http://localhost:8000/frontend/ in your browser.

**Features:**
- 🔍 Search menu items by keywords (e.g., "yuzu", "ramen", "tsukemen")
- 📊 View menu statistics
- 🎯 Sort by relevance, title, or category
- 🏷️ Category badges for easy identification
- 🌐 Two search modes:
  - **Local Search**: Searches JSON file directly (works offline)
  - **Solr Search**: Uses Solr for advanced search (requires Solr running)
- 📱 Responsive design for mobile and desktop

## 📁 Project Structure

```
Information_Retrieval/
├── README.md                    # This file
├── requirements.txt              # Python dependencies
├── scraper.py                   # Main scraping script
├── data_cleaner.py              # Data cleaning script
├── solr_indexer.py              # Solr indexing script
├── solr_setup.md                # Solr setup guide
├── frontend/                    # Web interface
│   ├── index.html              # Main HTML page
│   ├── styles.css              # CSS styles
│   └── app.js                  # JavaScript application
└── data/
    ├── scraped_data.json        # Raw scraped data (generated)
    └── cleaned_data.json        # Cleaned data (generated)
```

## 📊 Data Format

### Cleaned Data (`cleaned_data.json`)

Each menu item in `cleaned_data.json` contains:

```json
{
  "url": "https://afuri.com/menu/",
  "title": "Menu - Yuzu Shio Ramen",
  "content": "Yuzu Shio Ramen\n黄金色に輝く淡麗スープに爽やかな柚子の香りが広がる、AFURIを代表する一杯。\nchicken & dashi based broth, yuzu, half nitamago, chashu, mizuna, menma, nori",
  "section": "Menu",
  "menu_item": "Yuzu Shio Ramen",
  "menu_category": "Ramen"
}
```

**Fields:**
- `url`: Menu page URL (required)
- `title`: Menu item title (required)
- `content`: Menu item description with ingredients (required)
- `section`: Section type, typically "Menu" (required)
- `menu_item`: Menu item name (required)
- `menu_category`: Menu category - Ramen, Tsukemen, Noodles, Side Dishes, Drinks, or Chi-yu (required)

## 🔧 Troubleshooting

### Issue: "Failed to fetch page"

**Possible causes:**
- No internet connection
- Website is down

**Solutions:**
- Check your internet connection
- Wait a few minutes and try again

### Issue: "File does not exist"

**Solution:**
- Make sure you've run `python3 scraper.py` first
- Check that the `data/` directory exists

### Issue: Solr connection errors

**Solution:**
- Make sure Solr is running: `solr status`
- Create the core: `solr create -c afuri_menu`
- See `solr_setup.md` for detailed instructions

## 🎯 Project Status

This project is a complete information retrieval system with the following components:

1. ✅ **Web Scraping** (`scraper.py`) - **COMPLETED**
   - ✅ Scrape menu items from AFURI website
   - ✅ Extract menu item details and categories
   - ✅ Save to JSON format

2. ✅ **Data Cleaning** (`data_cleaner.py`) - **COMPLETED**
   - ✅ Remove HTML artifacts
   - ✅ Normalize text
   - ✅ Filter invalid items
   - ✅ Handle encoding issues

3. ✅ **Solr Integration** (`solr_indexer.py`) - **COMPLETED**
   - ✅ Index cleaned data into Solr
   - ✅ Search functionality
   - ✅ Batch processing
   - ✅ Error handling

4. ✅ **Frontend Display** (`frontend/`) - **COMPLETED**
   - ✅ Web interface for browsing menu items
   - ✅ Search functionality (local and Solr)
   - ✅ Category filtering and sorting
   - ✅ Responsive design
   - ✅ Highlighted search results

## 📝 Notes

- Data is saved in UTF-8 encoding to support Japanese characters
- The scraper automatically creates the `data/` directory if it doesn't exist
- Menu items are categorized automatically (Ramen, Tsukemen, Noodles, Side Dishes, Drinks, Chi-yu)

---

**Last Updated:** 2025
