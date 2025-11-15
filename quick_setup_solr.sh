#!/bin/bash
# Quick setup script for Solr synonym configuration
# This script configures Solr 9.x with managed schema using Schema API

CORE_NAME="afuri_menu"
SOLR_URL="http://localhost:8983/solr/$CORE_NAME"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "=========================================="
echo "Solr Synonym Configuration Setup"
echo "=========================================="
echo ""

# Check if Solr is running
if ! curl -s "$SOLR_URL/admin/ping" > /dev/null 2>&1; then
    echo "❌ Error: Cannot connect to Solr core $CORE_NAME"
    echo "Please make sure:"
    echo "  1. Solr is running: solr status"
    echo "  2. Core exists: solr create -c $CORE_NAME"
    exit 1
fi

echo "✓ Connected to Solr core: $CORE_NAME"
echo ""

# Copy synonyms.txt
SOLR_CONF_DIR="/opt/homebrew/var/lib/solr/$CORE_NAME/conf"
if [ -d "$SOLR_CONF_DIR" ]; then
    echo "Copying synonyms.txt..."
    cp "$SCRIPT_DIR/solr_config/synonyms.txt" "$SOLR_CONF_DIR/" && echo "✓ Copied synonyms.txt" || echo "⚠ Failed"
else
    echo "⚠ Warning: Solr conf directory not found"
    echo "Please copy synonyms.txt manually to: $SOLR_CONF_DIR/"
fi
echo ""

# Add text_synonym field type
echo "Adding text_synonym field type..."
RESPONSE=$(curl -s -X POST "$SOLR_URL/schema/fieldtypes" \
  -H 'Content-type:application/json' \
  -d '{
    "add-field-type": {
      "name": "text_synonym",
      "class": "solr.TextField",
      "positionIncrementGap": "100",
      "analyzer": {
        "tokenizer": {"class": "solr.StandardTokenizerFactory"},
        "filters": [
          {"class": "solr.LowerCaseFilterFactory"},
          {"class": "solr.EnglishPossessiveFilterFactory"},
          {"class": "solr.PorterStemFilterFactory"},
          {"class": "solr.SynonymGraphFilterFactory", "synonyms": "synonyms.txt", "ignoreCase": true, "expand": true},
          {"class": "solr.FlattenGraphFilterFactory"},
          {"class": "solr.StopFilterFactory", "words": "stopwords.txt", "ignoreCase": true}
        ]
      },
      "queryAnalyzer": {
        "tokenizer": {"class": "solr.StandardTokenizerFactory"},
        "filters": [
          {"class": "solr.LowerCaseFilterFactory"},
          {"class": "solr.EnglishPossessiveFilterFactory"},
          {"class": "solr.PorterStemFilterFactory"},
          {"class": "solr.SynonymGraphFilterFactory", "synonyms": "synonyms.txt", "ignoreCase": true, "expand": true},
          {"class": "solr.StopFilterFactory", "words": "stopwords.txt", "ignoreCase": true}
        ]
      }
    }
  }')

if echo "$RESPONSE" | grep -q '"status":0'; then
    echo "✓ Field type added successfully"
else
    echo "⚠ Warning: Field type may already exist or there was an error"
    echo "$RESPONSE" | head -5
fi
echo ""

# Update fields
FIELDS=("title" "content" "menu_item" "ingredients")
for FIELD in "${FIELDS[@]}"; do
    echo "Updating $FIELD field..."
    RESPONSE=$(curl -s -X POST "$SOLR_URL/schema/fields/$FIELD" \
      -H 'Content-type:application/json' \
      -d "{\"replace-field\":{\"name\":\"$FIELD\",\"type\":\"text_synonym\",\"indexed\":true,\"stored\":true}}")
    
    if echo "$RESPONSE" | grep -q '"status":0'; then
        echo "✓ $FIELD field updated"
    else
        echo "⚠ Warning: Failed to update $FIELD"
    fi
done
echo ""

echo "=========================================="
echo "Configuration complete!"
echo "=========================================="
echo ""
echo "Next step: Re-index your data"
echo "  python3 run_pipeline.py --skip-scrape --skip-clean"
echo ""
echo "Test synonym search:"
echo "  curl \"$SOLR_URL/select?q=salt&defType=edismax\""
echo ""

