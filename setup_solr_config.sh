#!/bin/bash
# Setup Solr configuration for AFURI menu search
# This script copies configuration files to Solr core directory

SOLR_HOME="${SOLR_HOME:-$HOME/solr}"
CORE_NAME="afuri_menu"
CORE_DIR="$SOLR_HOME/server/solr/$CORE_NAME"

# Detect Solr installation path
if [ -d "/opt/solr" ]; then
    SOLR_HOME="/opt/solr"
    CORE_DIR="$SOLR_HOME/server/solr/$CORE_NAME"
elif [ -d "/usr/local/solr" ]; then
    SOLR_HOME="/usr/local/solr"
    CORE_DIR="$SOLR_HOME/server/solr/$CORE_NAME"
elif command -v solr &> /dev/null; then
    # Try to find Solr using solr command
    SOLR_HOME=$(solr version 2>&1 | grep -oP 'Solr home: \K[^\s]+' || echo "$HOME/solr")
    CORE_DIR="$SOLR_HOME/server/solr/$CORE_NAME"
fi

echo "Setting up Solr configuration for core: $CORE_NAME"
echo "Solr home: $SOLR_HOME"
echo "Core directory: $CORE_DIR"

# Check if core exists
if [ ! -d "$CORE_DIR" ]; then
    echo "Error: Core directory not found at $CORE_DIR"
    echo "Please create the core first: solr create -c $CORE_NAME"
    exit 1
fi

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CONFIG_DIR="$SCRIPT_DIR/solr_config"

if [ ! -d "$CONFIG_DIR" ]; then
    echo "Error: Configuration directory not found at $CONFIG_DIR"
    exit 1
fi

# Copy configuration files
echo "Copying configuration files..."

# Copy managed-schema
if [ -f "$CONFIG_DIR/managed-schema" ]; then
    cp "$CONFIG_DIR/managed-schema" "$CORE_DIR/conf/managed-schema"
    echo "✓ Copied managed-schema"
else
    echo "⚠ Warning: managed-schema not found"
fi

# Copy solrconfig.xml
if [ -f "$CONFIG_DIR/solrconfig.xml" ]; then
    cp "$CONFIG_DIR/solrconfig.xml" "$CORE_DIR/conf/solrconfig.xml"
    echo "✓ Copied solrconfig.xml"
else
    echo "⚠ Warning: solrconfig.xml not found"
fi

# Copy synonyms.txt
if [ -f "$CONFIG_DIR/synonyms.txt" ]; then
    cp "$CONFIG_DIR/synonyms.txt" "$CORE_DIR/conf/synonyms.txt"
    echo "✓ Copied synonyms.txt"
else
    echo "⚠ Warning: synonyms.txt not found"
fi

# Copy stopwords.txt
if [ -f "$CONFIG_DIR/stopwords.txt" ]; then
    cp "$CONFIG_DIR/stopwords.txt" "$CORE_DIR/conf/stopwords.txt"
    echo "✓ Copied stopwords.txt"
else
    echo "⚠ Warning: stopwords.txt not found"
fi

echo ""
echo "Configuration files copied successfully!"
echo ""
echo "Next steps:"
echo "1. Reload the core: solr reload -c $CORE_NAME"
echo "2. Re-index your data: python3 run_pipeline.py --skip-scrape --skip-clean"
echo ""
echo "Note: If Solr is using managed schema, you may need to use the Schema API"
echo "instead of copying managed-schema. Check Solr version and configuration."

