# Information Retrieval Project - 5AM Ramen Scraper

A web scraping project for extracting blog articles from 5AM Ramen website, with data cleaning, Solr integration, and frontend display capabilities.

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Data Format](#data-format)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

## 🎯 Project Overview

This project is designed to:
1. **Scrape** blog articles from https://www.5amramen.com
2. **Clean** and process the scraped data
3. **Index** data into Solr for search functionality
4. **Display** data through a frontend interface

Currently, the scraping component is complete. Data cleaning, Solr integration, and frontend are in development.

## ✨ Features

- ✅ Web scraping with `requests` and `BeautifulSoup`
- ✅ Automatic article discovery and extraction
- ✅ Data export to JSON format
- ✅ Result viewing and statistics
- ✅ Data cleaning and normalization
- 🔄 Solr integration (planned)
- 🔄 Frontend display (planned)

## 📦 Requirements

- Python 3.7 or higher
- pip (Python package manager)

## 🚀 Installation

### Step 1: Clone or Download the Project

```bash
cd /path/to/Information_Retrieval
```

### Step 2: Install Dependencies

```bash
pip3 install -r requirements.txt
```

This will install:
- `requests` - For HTTP requests
- `beautifulsoup4` - For HTML parsing
- `lxml` - For faster HTML parsing

## 📖 Usage

### 1. Scraping Data

Run the scraper to collect blog articles:

```bash
python3 scraper.py
```

**What it does:**
- Fetches the homepage and blog pages
- Discovers all article links
- Extracts article details (title, content, date, author, tags)
- Saves data to `data/scraped_data.json`

**Options:**
- Modify `max_pages` in `scraper.py` to change the number of articles to scrape (default: 50)

**Example output:**
```
Starting to scrape 5AM Ramen blog...
Scraping: https://www.5amramen.com
Found 24 articles

[1/24] Processing: https://www.5amramen.com/post/ramen-iida-shoten
✓ Successfully extracted: Ramen Iida Shoten - Japan's Ramen Holy Grail...

Scraping completed! Retrieved 24 articles
Data saved to: data/scraped_data.json
```

### 2. Viewing Results

View the scraped data:

```bash
# View all articles summary
python3 view_results.py

# View only first 5 articles
python3 view_results.py --limit 5

# View full content of articles
python3 view_results.py --content

# Combine options
python3 view_results.py --limit 3 --content
```

**Example output:**
```
================================================================================
📊 Scraping Results Statistics
================================================================================
Total articles: 24
Data file: data/scraped_data.json
File size: 47.66 KB

================================================================================
📝 Article List
================================================================================

[1] Ramen Iida Shoten - Japan's Ramen Holy Grail
    URL: https://www.5amramen.com/post/ramen-iida-shoten
    Date: Jul 23, 2022
    Content preview: Ramen Iida Shoten (らぁ麺飯田商店) is Japan's no. 1 ranked ramen shop!...
```

### 3. Cleaning Data

Clean the scraped data to improve quality:

```bash
python3 data_cleaner.py
```

**What it does:**
- Removes HTML tags and entities
- Normalizes whitespace and special characters
- Standardizes date formats (ISO format: YYYY-MM-DD)
- Filters out invalid articles (category pages, blog listings, etc.)
- Removes duplicate articles
- Removes empty fields
- Validates article content

**Example output:**
```
Loaded 24 articles from data/scraped_data.json

Starting data cleaning...
================================================================================

Cleaned data saved to: data/cleaned_data.json

================================================================================
📊 Cleaning Statistics
================================================================================
Total articles loaded: 24
Articles cleaned: 15
Articles removed: 9
Removal rate: 37.5%

Issues fixed:
  - content_cleaned: 4 articles
================================================================================
```

**Output:**
- Cleaned data is saved to `data/cleaned_data.json`
- Original scraped data remains in `data/scraped_data.json`

### 4. Accessing Data Programmatically

You can also use the data in your own Python scripts:

```python
import json

# Load cleaned data (recommended)
with open('data/cleaned_data.json', 'r', encoding='utf-8') as f:
    articles = json.load(f)

# Or load raw scraped data
with open('data/scraped_data.json', 'r', encoding='utf-8') as f:
    articles = json.load(f)

# Process articles
for article in articles:
    print(f"Title: {article['title']}")
    print(f"URL: {article['url']}")
    if 'date' in article:
        print(f"Date: {article['date']}")
    print(f"Content length: {len(article['content'])} characters")
    print("---")
```

## 📁 Project Structure

```
Information_Retrieval/
├── README.md                    # This file
├── requirements.txt              # Python dependencies
├── scraper.py                   # Main scraping script
├── data_cleaner.py              # Data cleaning script
├── view_results.py              # Result viewing tool
├── data/
│   ├── scraped_data.json        # Raw scraped data (generated)
│   └── cleaned_data.json        # Cleaned data (generated)
└── IR_practical_session_1_2025-checkpoint.ipynb  # Jupyter notebook
```

## 📊 Data Format

### Raw Data (`scraped_data.json`)

Each article in `scraped_data.json` contains:

```json
{
  "url": "https://www.5amramen.com/post/article-name",
  "title": "Article Title",
  "content": "Full article content...",
  "date": "Jul 23, 2022",
  "author": "Author Name",
  "tags": ["tag1", "tag2"],
  "categories": []
}
```

### Cleaned Data (`cleaned_data.json`)

After cleaning, the data format is similar but with improvements:

```json
{
  "url": "https://www.5amramen.com/post/article-name",
  "title": "Article Title",
  "content": "Full article content...",
  "date": "2022-07-23"
}
```

**Key differences:**
- `date`: Standardized to ISO format (YYYY-MM-DD)
- Empty fields (`author`, `tags`, `categories`) are removed if not present
- HTML tags and entities are removed
- Whitespace is normalized
- Only valid articles are included (category pages, blog listings filtered out)

**Fields:**
- `url`: Full URL of the article (required)
- `title`: Article title (required, cleaned)
- `content`: Main article text (required, cleaned, paragraphs separated by double newlines)
- `date`: Publication date in ISO format YYYY-MM-DD (optional)
- `author`: Author name (optional, removed if empty)
- `tags`: List of tags (optional, removed if empty)
- `categories`: List of categories (optional, removed if empty)

## 🔧 Troubleshooting

### Issue: "Failed to fetch page"

**Possible causes:**
- No internet connection
- Website is down
- Rate limiting by the website

**Solutions:**
- Check your internet connection
- Wait a few minutes and try again
- The scraper includes a 1-second delay between requests to be polite

### Issue: "File does not exist"

**Solution:**
- Make sure you've run `python3 scraper.py` first
- Check that the `data/` directory exists

### Issue: Empty content in articles

**Possible causes:**
- Website structure changed
- Article page has different HTML structure

**Solutions:**
- Check the website manually
- Update the parsing logic in `scraper.py` if needed

### Issue: Import errors

**Solution:**
```bash
# Reinstall dependencies
pip3 install --upgrade -r requirements.txt
```

## 🎯 Next Steps

This project is part of a larger information retrieval system. Future development includes:

1. ✅ **Data Cleaning** (`data_cleaner.py`) - **COMPLETED**
   - ✅ Remove HTML artifacts
   - ✅ Normalize text
   - ✅ Standardize date formats
   - ✅ Filter invalid articles
   - ✅ Handle encoding issues

2. **Solr Integration** (`solr_indexer.py`)
   - Set up Solr instance
   - Create schema
   - Index cleaned data
   - Implement search functionality

3. **Frontend Display** (`frontend/`)
   - Web interface for browsing articles
   - Search functionality
   - Filtering and sorting
   - Responsive design

## 📝 Notes

- The scraper includes a 1-second delay between requests to be respectful to the website
- Data is saved in UTF-8 encoding to support international characters
- The scraper automatically creates the `data/` directory if it doesn't exist

## 🤝 Contributing

Feel free to improve the scraper or add new features:
- Better error handling
- More robust HTML parsing
- Additional data fields
- Performance optimizations

## 📄 License

This project is for educational purposes.

---

**Last Updated:** 2025
