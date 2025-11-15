#!/bin/bash
# Setup Solr schema using Schema API (for Solr 8.5+ with managed schema)
# This script configures synonym expansion and field types

CORE_NAME="afuri_menu"
SOLR_URL="http://localhost:8983/solr/$CORE_NAME"

echo "Setting up Solr schema for core: $CORE_NAME"
echo "Solr URL: $SOLR_URL"
echo ""

# Check if core exists
if ! curl -s "$SOLR_URL/admin/ping" > /dev/null 2>&1; then
    echo "Error: Cannot connect to Solr core $CORE_NAME"
    echo "Please make sure Solr is running and the core exists"
    exit 1
fi

echo "✓ Connected to Solr core"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SYNONYMS_FILE="$SCRIPT_DIR/solr_config/synonyms.txt"
STOPWORDS_FILE="$SCRIPT_DIR/solr_config/stopwords.txt"

# Copy synonyms.txt and stopwords.txt to Solr conf directory
SOLR_CONF_DIR="/opt/homebrew/var/lib/solr/$CORE_NAME/conf"
if [ -d "$SOLR_CONF_DIR" ]; then
    echo "Copying synonyms.txt and stopwords.txt to Solr conf directory..."
    cp "$SYNONYMS_FILE" "$SOLR_CONF_DIR/" 2>/dev/null && echo "✓ Copied synonyms.txt" || echo "⚠ Failed to copy synonyms.txt"
    cp "$STOPWORMS_FILE" "$SOLR_CONF_DIR/" 2>/dev/null && echo "✓ Copied stopwords.txt" || echo "⚠ Failed to copy stopwords.txt"
else
    echo "⚠ Warning: Solr conf directory not found at $SOLR_CONF_DIR"
    echo "Please copy synonyms.txt and stopwords.txt manually to the Solr conf directory"
fi

echo ""
echo "Configuring field types with synonym support..."

# First, let's check what field types exist
echo "Current field types:"
curl -s "$SOLR_URL/schema/fieldtypes" | python3 -m json.tool 2>&1 | grep -E '"name"|"class"' | head -10

echo ""
echo "Adding text_synonym field type..."

# Add text_synonym field type with synonym filter
curl -X POST "$SOLR_URL/schema/fieldtypes" \
  -H 'Content-type:application/json' \
  -d '{
    "add-field-type": {
      "name": "text_synonym",
      "class": "solr.TextField",
      "positionIncrementGap": "100",
      "analyzer": {
        "tokenizer": {
          "class": "solr.StandardTokenizerFactory"
        },
        "filters": [
          {
            "class": "solr.LowerCaseFilterFactory"
          },
          {
            "class": "solr.SynonymGraphFilterFactory",
            "synonyms": "synonyms.txt",
            "ignoreCase": true,
            "expand": true
          },
          {
            "class": "solr.FlattenGraphFilterFactory"
          },
          {
            "class": "solr.StopFilterFactory",
            "words": "stopwords.txt",
            "ignoreCase": true
          }
        ]
      },
      "queryAnalyzer": {
        "tokenizer": {
          "class": "solr.StandardTokenizerFactory"
        },
        "filters": [
          {
            "class": "solr.LowerCaseFilterFactory"
          },
          {
            "class": "solr.SynonymGraphFilterFactory",
            "synonyms": "synonyms.txt",
            "ignoreCase": true,
            "expand": true
          },
          {
            "class": "solr.StopFilterFactory",
            "words": "stopwords.txt",
            "ignoreCase": true
          }
        ]
      }
    }
  }' 2>&1 | python3 -m json.tool

echo ""
echo "Updating existing fields to use text_synonym type..."

# Update title field
echo "Updating title field..."
curl -X POST "$SOLR_URL/schema/fields/title" \
  -H 'Content-type:application/json' \
  -d '{
    "replace-field": {
      "name": "title",
      "type": "text_synonym",
      "indexed": true,
      "stored": true
    }
  }' 2>&1 | python3 -m json.tool

# Update content field
echo "Updating content field..."
curl -X POST "$SOLR_URL/schema/fields/content" \
  -H 'Content-type:application/json' \
  -d '{
    "replace-field": {
      "name": "content",
      "type": "text_synonym",
      "indexed": true,
      "stored": true
    }
  }' 2>&1 | python3 -m json.tool

# Update menu_item field
echo "Updating menu_item field..."
curl -X POST "$SOLR_URL/schema/fields/menu_item" \
  -H 'Content-type:application/json' \
  -d '{
    "replace-field": {
      "name": "menu_item",
      "type": "text_synonym",
      "indexed": true,
      "stored": true
    }
  }' 2>&1 | python3 -m json.tool

# Update ingredients field
echo "Updating ingredients field..."
curl -X POST "$SOLR_URL/schema/fields/ingredients" \
  -H 'Content-type:application/json' \
  -d '{
    "replace-field": {
      "name": "ingredients",
      "type": "text_synonym",
      "indexed": true,
      "stored": true
    }
  }' 2>&1 | python3 -m json.tool

echo ""
echo "Configuration complete!"
echo ""
echo "Next steps:"
echo "1. Re-index your data: python3 run_pipeline.py --skip-scrape --skip-clean"
echo "2. Test synonym search: curl \"$SOLR_URL/select?q=salt&defType=edismax\""

