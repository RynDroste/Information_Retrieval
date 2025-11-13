# Solr Setup Guide

This guide will help you set up Apache Solr for indexing and searching the scraped articles.

## Prerequisites

- Java 8 or higher installed
- Apache Solr installed

## Installation

### 1. Install Solr

**macOS (using Homebrew):**
```bash
brew install solr
```

**Linux:**
```bash
# Download Solr
wget https://archive.apache.org/dist/solr/solr/8.11.2/solr-8.11.2.tgz
tar xzf solr-8.11.2.tgz
cd solr-8.11.2
```

**Windows:**
Download from https://solr.apache.org/downloads.html

### 2. Start Solr

```bash
# macOS/Linux
solr start

# Or if installed manually
./bin/solr start
```

Verify Solr is running:
```bash
solr status
```

You should see Solr running on port 8983.

### 3. Create Solr Core

```bash
# Create a core named 'ramen_articles'
solr create -c ramen_articles

# Or if installed manually
./bin/solr create -c ramen_articles
```

### 4. Configure Schema (Optional)

The default schema should work, but you can customize it. The script expects these fields:

- `id` (string, required) - Unique document ID
- `url` (string) - Article URL
- `title` (text) - Article title (searchable)
- `content` (text) - Article content (searchable)
- `date` (string) - Publication date
- `author` (string) - Author name
- `tags` (string, multi-valued) - Article tags
- `categories` (string, multi-valued) - Article categories

### 5. Install Python Dependencies

```bash
pip3 install pysolr
```

Or add to requirements.txt:
```
pysolr>=5.0.0
```

## Usage

### Index Data

```bash
python3 solr_indexer.py
```

### Custom Solr URL

```bash
python3 solr_indexer.py --solr-url http://localhost:8983/solr/ramen_articles
```

### Keep Existing Documents

```bash
python3 solr_indexer.py --keep-existing
```

## Verify Indexing

### Using Solr Admin UI

1. Open http://localhost:8983/solr/#/ramen_articles/query
2. Click "Execute Query" to see all documents
3. Try searching with: `q=ramen`

### Using Command Line

```bash
# Search via curl
curl "http://localhost:8983/solr/ramen_articles/select?q=ramen&rows=5"
```

## Troubleshooting

### Solr not running
```bash
solr start
```

### Core doesn't exist
```bash
solr create -c ramen_articles
```

### Connection refused
- Check if Solr is running: `solr status`
- Verify the URL: http://localhost:8983/solr/#/
- Check firewall settings

### Schema errors
- Use the default schema or create custom fields in Solr Admin UI
- Field types should match: text for searchable fields, string for exact matches

## Next Steps

After indexing, you can:
1. Use the frontend to search articles
2. Query Solr directly via API
3. Build custom search applications

