#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Cleaning Script
Cleans scraped data for better quality and consistency
"""

import json
import os
import re
from html import unescape
import unicodedata

class DataCleaner:
    def __init__(self, input_file='data/scraped_data.json', output_file='data/cleaned_data.json'):
        self.input_file = input_file
        self.output_file = output_file
        self.articles = []
        self.stats = {
            'total': 0,
            'cleaned': 0,
            'removed': 0
        }
    
    def load_data(self):
        """Load scraped data from JSON file"""
        if not os.path.exists(self.input_file):
            print(f"Error: File {self.input_file} does not exist")
            print("Please run scraper.py first to scrape data")
            return False
        
        with open(self.input_file, 'r', encoding='utf-8') as f:
            self.articles = json.load(f)
        
        self.stats['total'] = len(self.articles)
        print(f"Loaded {len(self.articles)} articles from {self.input_file}")
        return True
    
    def clean_text(self, text):
        """Clean text content - remove HTML, normalize whitespace, etc."""
        if not text:
            return ''
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        text = unescape(text)
        
        # Remove zero-width spaces and normalize unicode
        text = re.sub(r'[\u200b-\u200d\ufeff]', '', text)
        text = unicodedata.normalize('NFKC', text)
        
        # Normalize whitespace
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines).strip()
        
        return text
    
    def is_valid_article(self, article):
        """Check if article is valid"""
        content = article.get('content', '')
        section = article.get('section', '')
        
        # Set minimum length based on section type
        if section == 'Menu':
            min_length = 30
        elif section == 'Store Information':
            min_length = 20
        else:
            min_length = 50
        
        return len(content) >= min_length
    
    def clean_article(self, article):
        """Clean a single article"""
        cleaned = {
            'url': article.get('url', '').strip(),
            'title': self.clean_text(article.get('title', '')),
            'content': self.clean_text(article.get('content', '')),
            'section': article.get('section', '').strip()
        }
        
        # Preserve optional fields
        if 'date' in article and article.get('date'):
            cleaned['date'] = article.get('date', '').strip()
        if 'store_name' in article:
            cleaned['store_name'] = article.get('store_name', '').strip()
        if 'menu_item' in article:
            cleaned['menu_item'] = article.get('menu_item', '').strip()
        if 'menu_category' in article:
            cleaned['menu_category'] = article.get('menu_category', '').strip()
        
        # Extract ingredients - first check if it exists, otherwise extract from content
        ingredients = ''
        if 'ingredients' in article and article.get('ingredients', '').strip():
            ingredients = article.get('ingredients', '').strip()
        else:
            # Try to extract ingredients from content (usually the last line with comma-separated English ingredients)
            content = cleaned.get('content', '')
            if content and cleaned.get('section') == 'Menu':
                lines = content.split('\n')
                for line in reversed(lines):
                    line = line.strip()
                    # Check if line contains common ingredient patterns (comma-separated, lowercase/English)
                    if ',' in line and len(line) > 20:
                        # Check if it looks like ingredients (contains common food words)
                        ingredient_keywords = ['broth', 'chashu', 'nori', 'egg', 'yuzu', 'menma', 'mizuna', 'dashi', 'shoyu', 'chicken', 'nitamago', 'negi']
                        if any(keyword in line.lower() for keyword in ingredient_keywords):
                            ingredients = line
                            break
        
        if ingredients:
            cleaned['ingredients'] = ingredients
        
        if 'tags' in article and article.get('tags'):
            cleaned['tags'] = [tag.strip() for tag in article.get('tags', []) if tag.strip()]
        
        return cleaned
    
    def remove_duplicates(self, articles):
        """Remove duplicate articles"""
        seen_items = set()
        unique_articles = []
        
        for article in articles:
            url = article.get('url', '')
            section = article.get('section', '')
            
            # Create unique identifier based on section type
            if section == 'Menu':
                menu_item = article.get('menu_item', '')
                menu_category = article.get('menu_category', '')
                identifier = f"{url}:{menu_category}:{menu_item}" if menu_item else url
            elif section == 'Store Information':
                store_name = article.get('store_name', '')
                identifier = f"{url}:{store_name}" if store_name else url
            else:
                identifier = url
            
            if identifier and identifier not in seen_items:
                seen_items.add(identifier)
                unique_articles.append(article)
            else:
                self.stats['removed'] += 1
        
        return unique_articles
    
    def clean_all(self):
        """Clean all articles"""
        if not self.load_data():
            return False
        
        print("\nStarting data cleaning...")
        print("=" * 80)
        
        cleaned_articles = []
        
        for article in self.articles:
            if not self.is_valid_article(article):
                self.stats['removed'] += 1
                continue
            
            cleaned = self.clean_article(article)
            
            if cleaned['title'] and cleaned['content']:
                cleaned_articles.append(cleaned)
                self.stats['cleaned'] += 1
            else:
                self.stats['removed'] += 1
        
        # Remove duplicates
        print("\nRemoving duplicates...")
        before_dedup = len(cleaned_articles)
        cleaned_articles = self.remove_duplicates(cleaned_articles)
        duplicates_removed = before_dedup - len(cleaned_articles)
        if duplicates_removed > 0:
            self.stats['removed'] += duplicates_removed
            print(f"Removed {duplicates_removed} duplicate articles")
        
        self.articles = cleaned_articles
        return True
    
    def save_data(self):
        """Save cleaned data to JSON file"""
        output_dir = os.path.dirname(self.output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.articles, f, ensure_ascii=False, indent=2)
        
        print(f"\nCleaned data saved to: {self.output_file}")
        return self.output_file
    
    def print_stats(self):
        """Print cleaning statistics"""
        print("\n" + "=" * 80)
        print("📊 Cleaning Statistics")
        print("=" * 80)
        print(f"Total articles loaded: {self.stats['total']}")
        print(f"Articles cleaned: {self.stats['cleaned']}")
        print(f"Articles removed: {self.stats['removed']}")
        if self.stats['total'] > 0:
            print(f"Removal rate: {self.stats['removed']/self.stats['total']*100:.1f}%")
        print("=" * 80)

# 此文件仅作为模块使用，请使用 run_pipeline.py 运行完整流程
