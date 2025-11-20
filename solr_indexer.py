#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Solr Indexer
Index cleaned data into Apache Solr for search functionality
"""

import json
import os
import sys
from urllib.parse import urlparse

try:
    import pysolr
except ImportError:
    print("Error: pysolr is not installed.")
    print("Please install it using: pip3 install pysolr")
    sys.exit(1)

class SolrIndexer:
    def __init__(self, solr_url='http://localhost:8983/solr/RamenProject', data_file='data/cleaned_data.json', use_labse=False):
        self.solr_url = solr_url
        self.data_file = data_file
        self.solr = None
        self.use_labse = use_labse
        self.labse_embedder = None
        self.stats = {
            'total': 0,
            'indexed': 0,
            'failed': 0,
            'errors': []
        }
        
        if self.use_labse:
            try:
                from labse_embedder import LaBSEEmbedder
                self.labse_embedder = LaBSEEmbedder()
                if not self.labse_embedder.is_available():
                    print("⚠ Warning: LaBSE not available, continuing without semantic embeddings")
                    self.use_labse = False
            except ImportError:
                print("⚠ Warning: LaBSE embedder not found, continuing without semantic embeddings")
                self.use_labse = False
    
    def connect(self):
        """Connect to Solr instance"""
        try:
            print(f"Connecting to Solr at {self.solr_url}...")
            self.solr = pysolr.Solr(self.solr_url, timeout=10)
            # Test connection
            self.solr.ping()
            print("✓ Successfully connected to Solr")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to Solr: {e}")
            print("\nPlease make sure:")
            print("1. Solr is running (check with: solr status)")
            print("2. A core named 'RamenProject' exists")
            print("3. The URL is correct (default: http://localhost:8983/solr/RamenProject)")
            return False
    
    def load_data(self):
        """Load cleaned data from JSON file"""
        if not os.path.exists(self.data_file):
            print(f"Error: File {self.data_file} does not exist")
            print("Please run data_cleaner.py first to generate cleaned data")
            return None
        
        with open(self.data_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        
        self.stats['total'] = len(articles)
        print(f"Loaded {len(articles)} articles from {self.data_file}")
        return articles
    
    def prepare_document(self, article, index):
        """Prepare article for Solr indexing"""
        # Use menu_item or title for unique ID
        unique_id = article.get('menu_item') or article.get('title', f"item_{index}")
        doc = {
            'id': f"{article.get('section', 'menu')}_{index}_{unique_id[:50]}".replace(' ', '_'),
            'url': article.get('url', ''),
            'title': article.get('title', ''),
            'content': article.get('content', ''),
            'section': article.get('section', ''),
        }
        
        # Add menu-specific fields
        if 'menu_item' in article and article['menu_item']:
            doc['menu_item'] = article['menu_item']
        
        if 'menu_category' in article and article['menu_category']:
            doc['menu_category'] = article['menu_category']
        
        # Add introduction if exists
        if 'introduction' in article and article['introduction']:
            doc['introduction'] = article['introduction']
        
        # Add store information if exists
        if 'store_name' in article and article['store_name']:
            doc['store_name'] = article['store_name']
        
        # Add optional fields if they exist
        if 'date' in article and article['date']:
            doc['date'] = article['date']
        
        if 'tags' in article and article['tags']:
            doc['tags'] = article['tags']
        
        if 'price' in article and article['price']:
            doc['price'] = article['price']
        
        if 'price_range' in article and article['price_range']:
            doc['price_range'] = article['price_range']
        
        return doc
    
    def index_articles(self, clear_existing=True):
        """Index articles into Solr"""
        if not self.connect():
            return False
        
        articles = self.load_data()
        if not articles:
            return False
        
        # Clear existing documents if requested
        if clear_existing:
            print("\nClearing existing documents...")
            try:
                self.solr.delete(q='*:*')
                self.solr.commit()
                print("✓ Cleared existing documents")
            except Exception as e:
                print(f"⚠ Warning: Could not clear existing documents: {e}")
        
        print(f"\nIndexing {len(articles)} articles...")
        print("=" * 80)
        
        # Generate LaBSE embeddings if enabled
        embeddings = {}
        if self.use_labse and self.labse_embedder:
            print("\nGenerating LaBSE embeddings...")
            print("=" * 80)
            articles_texts = []
            article_ids = []
            for i, article in enumerate(articles, 1):
                unique_id = article.get('menu_item') or article.get('title', f"item_{i}")
                doc_id = f"{article.get('section', 'menu')}_{i}_{unique_id[:50]}".replace(' ', '_')
                article_ids.append(doc_id)
                
                # Prepare text for embedding
                text_parts = []
                if article.get('title'):
                    text_parts.append(article['title'])
                if article.get('menu_item') and article['menu_item'] != article.get('title'):
                    text_parts.append(article['menu_item'])
                if article.get('content'):
                    text_parts.append(article['content'][:500])
                if article.get('menu_category'):
                    text_parts.append(article['menu_category'])
                articles_texts.append(' '.join(text_parts) if text_parts else '')
            
            # Generate embeddings in batches
            article_embeddings = self.labse_embedder.generate_embeddings_batch(articles_texts, batch_size=32)
            embeddings = {doc_id: emb for doc_id, emb in zip(article_ids, article_embeddings) if emb is not None}
            
            # Save embeddings to file
            embeddings_file = 'data/embeddings.json'
            self.labse_embedder.save_embeddings(embeddings, embeddings_file)
            print(f"✓ Generated {len(embeddings)} embeddings")
        
        # Prepare documents
        documents = []
        for i, article in enumerate(articles, 1):
            try:
                doc = self.prepare_document(article, i)
                documents.append(doc)
                print(f"[{i}/{len(articles)}] Prepared: {doc['title'][:50]}...")
            except Exception as e:
                self.stats['failed'] += 1
                self.stats['errors'].append(f"Article {i}: {str(e)}")
                print(f"✗ Failed to prepare article {i}: {e}")
        
        # Index documents in batches
        batch_size = 10
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            try:
                self.solr.add(batch)
                self.stats['indexed'] += len(batch)
                print(f"✓ Indexed batch {i//batch_size + 1} ({len(batch)} documents)")
            except Exception as e:
                self.stats['failed'] += len(batch)
                self.stats['errors'].append(f"Batch {i//batch_size + 1}: {str(e)}")
                print(f"✗ Failed to index batch {i//batch_size + 1}: {e}")
        
        # Commit changes
        try:
            self.solr.commit()
            print("\n✓ Committed changes to Solr")
        except Exception as e:
            print(f"✗ Failed to commit: {e}")
            return False
        
        return True
    
    def search(self, query, rows=10):
        """Search articles in Solr"""
        if not self.solr:
            if not self.connect():
                return None
        
        try:
            results = self.solr.search(query, rows=rows)
            return results
        except Exception as e:
            print(f"Search error: {e}")
            return None
    
    def print_stats(self):
        """Print indexing statistics"""
        print("\n" + "=" * 80)
        print("📊 Indexing Statistics")
        print("=" * 80)
        print(f"Total articles: {self.stats['total']}")
        print(f"Successfully indexed: {self.stats['indexed']}")
        print(f"Failed: {self.stats['failed']}")
        
        if self.stats['errors']:
            print(f"\nErrors ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(self.stats['errors']) > 5:
                print(f"  ... and {len(self.stats['errors']) - 5} more errors")
        
        print("=" * 80)
        
        # Test search
        print("\n🔍 Testing search functionality...")
        test_query = "yuzu"
        results = self.search(test_query, rows=3)
        if results:
            print(f"Found {results.hits} results for query '{test_query}'")
            for i, result in enumerate(results, 1):
                title = result.get('title', 'No title')[:60]
                category = result.get('menu_category', '')
                if category:
                    print(f"  {i}. {title} ({category})")
                else:
                    print(f"  {i}. {title}")
        else:
            print("Search test failed")

