# Solr Setup Guide

This guide will help you set up Apache Solr for indexing and searching the AFURI menu data.

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
# Create a core named 'afuri_menu'
solr create -c afuri_menu

# Or if installed manually
./bin/solr create -c afuri_menu
```

### 4. Configure Schema (Optional)

The default schema should work, but you can customize it. The script expects these fields:

- `id` (string, required) - Unique document ID
- `url` (string) - Menu page URL
- `title` (text) - Menu item title (searchable)
- `content` (text) - Menu item description (searchable)
- `section` (string) - Section type (e.g., "Menu")
- `menu_item` (text) - Menu item name (searchable)
- `menu_category` (string) - Menu category (Ramen, Tsukemen, Noodles, Side Dishes, Drinks, Chi-yu)
- `store_name` (string) - Store name (if applicable)
- `date` (string) - Optional date field

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
python3 solr_indexer.py --solr-url http://localhost:8983/solr/afuri_menu
```

### Keep Existing Documents

```bash
python3 solr_indexer.py --keep-existing
```

## Verify Indexing

### Using Solr Admin UI

1. Open http://localhost:8983/solr/#/afuri_menu/query
2. Click "Execute Query" to see all documents
3. Try searching with: `q=yuzu` or `q=ramen`

### Using Command Line

```bash
# Search via curl
curl "http://localhost:8983/solr/afuri_menu/select?q=yuzu&rows=5"
```

## Troubleshooting

### Solr not running
```bash
solr start
```

### Core doesn't exist
```bash
solr create -c afuri_menu
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

