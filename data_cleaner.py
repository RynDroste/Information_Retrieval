#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Cleaning Script
Cleans scraped data for better quality and consistency
"""

import json
import os
import re
from datetime import datetime
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
            'removed': 0,
            'issues_fixed': {}
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
    
    def clean_html_entities(self, text):
        """Remove HTML entities and decode them"""
        if not text:
            return text
        # Decode HTML entities like &amp; &lt; &gt; etc.
        text = unescape(text)
        return text
    
    def normalize_whitespace(self, text):
        """Normalize whitespace characters"""
        if not text:
            return text
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        # Replace multiple newlines with double newline
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        # Remove empty lines at start and end
        text = text.strip()
        return text
    
    def remove_html_tags(self, text):
        """Remove any remaining HTML tags"""
        if not text:
            return text
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        return text
    
    def clean_special_characters(self, text):
        """Clean special characters while preserving important ones"""
        if not text:
            return text
        # Remove zero-width spaces and other invisible characters
        text = re.sub(r'[\u200b-\u200d\ufeff]', '', text)
        # Normalize unicode characters
        text = unicodedata.normalize('NFKC', text)
        return text
    
    def standardize_date(self, date_str):
        """Standardize date format"""
        if not date_str or date_str.strip() == '':
            return None
        
        date_str = date_str.strip()
        
        # Handle relative dates like "19 hours ago", "2 days ago"
        if 'ago' in date_str.lower():
            return date_str  # Keep relative dates as is for now
        
        # Try to parse common date formats
        date_formats = [
            '%b %d, %Y',      # "Jul 23, 2022"
            '%B %d, %Y',      # "July 23, 2022"
            '%Y-%m-%d',       # "2022-07-23"
            '%d/%m/%Y',       # "23/07/2022"
            '%m/%d/%Y',       # "07/23/2022"
            '%b %d',          # "Jul 23" (current year assumed)
            '%B %d',          # "July 23"
        ]
        
        for fmt in date_formats:
            try:
                # For dates without year, assume current year
                if fmt in ['%b %d', '%B %d']:
                    date_str_with_year = f"{date_str}, {datetime.now().year}"
                    parsed_date = datetime.strptime(date_str_with_year, f"{fmt}, %Y")
                else:
                    parsed_date = datetime.strptime(date_str, fmt)
                # Return in ISO format
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # If no format matches, return original (might be relative date)
        return date_str
    
    def clean_content(self, content):
        """Clean article content"""
        if not content:
            return ''
        
        # Track if we made changes
        original = content
        
        # Step 1: Remove HTML tags
        content = self.remove_html_tags(content)
        
        # Step 2: Decode HTML entities
        content = self.clean_html_entities(content)
        
        # Step 3: Clean special characters
        content = self.clean_special_characters(content)
        
        # Step 4: Normalize whitespace
        content = self.normalize_whitespace(content)
        
        # Track issues fixed
        if content != original:
            if 'content_cleaned' not in self.stats['issues_fixed']:
                self.stats['issues_fixed']['content_cleaned'] = 0
            self.stats['issues_fixed']['content_cleaned'] += 1
        
        return content
    
    def clean_title(self, title):
        """Clean article title"""
        if not title:
            return ''
        
        original = title
        title = self.remove_html_tags(title)
        title = self.clean_html_entities(title)
        title = self.clean_special_characters(title)
        title = self.normalize_whitespace(title)
        
        if title != original:
            if 'title_cleaned' not in self.stats['issues_fixed']:
                self.stats['issues_fixed']['title_cleaned'] = 0
            self.stats['issues_fixed']['title_cleaned'] += 1
        
        return title
    
    def is_valid_article(self, article):
        """Check if article is valid (not a category page, etc.)"""
        # Filter out non-article pages
        url = article.get('url', '')
        title = article.get('title', '')
        content = article.get('content', '')
        
        # Skip category pages and blog listing pages
        if '/blog/categories/' in url or '/blog/page/' in url:
            return False
        
        # Skip if title suggests it's not an article
        if title.lower() in ['blog', 'browse the 5am ramen blog', 'blog | 5 am ramen']:
            return False
        
        # Skip if content is too short (likely not a real article)
        if len(content) < 100:
            return False
        
        # Skip if it's the homepage
        if url == 'https://www.5amramen.com' or url == 'https://www.5amramen.com/':
            return False
        
        return True
    
    def clean_article(self, article):
        """Clean a single article"""
        cleaned = {
            'url': article.get('url', '').strip(),
            'title': self.clean_title(article.get('title', '')),
            'content': self.clean_content(article.get('content', '')),
            'date': self.standardize_date(article.get('date', '')),
            'author': article.get('author', '').strip(),
            'tags': [tag.strip() for tag in article.get('tags', []) if tag.strip()],
            'categories': [cat.strip() for cat in article.get('categories', []) if cat.strip()]
        }
        
        # Remove empty fields for cleaner data
        if not cleaned['author']:
            cleaned.pop('author', None)
        if not cleaned['tags']:
            cleaned.pop('tags', None)
        if not cleaned['categories']:
            cleaned.pop('categories', None)
        if not cleaned['date']:
            cleaned.pop('date', None)
        
        return cleaned
    
    def remove_duplicates(self, articles):
        """Remove duplicate articles based on URL"""
        seen_urls = set()
        unique_articles = []
        
        for article in articles:
            url = article.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
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
            # Check if article is valid
            if not self.is_valid_article(article):
                self.stats['removed'] += 1
                continue
            
            # Clean the article
            cleaned = self.clean_article(article)
            
            # Only add if it has meaningful content
            if cleaned['title'] and cleaned['content']:
                cleaned_articles.append(cleaned)
                self.stats['cleaned'] += 1
            else:
                self.stats['removed'] += 1
        
        # Remove duplicates
        print(f"\nRemoving duplicates...")
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
        print(f"Removal rate: {self.stats['removed']/self.stats['total']*100:.1f}%")
        
        if self.stats['issues_fixed']:
            print("\nIssues fixed:")
            for issue, count in self.stats['issues_fixed'].items():
                print(f"  - {issue}: {count} articles")
        
        print("=" * 80)

def main():
    cleaner = DataCleaner()
    
    if cleaner.clean_all():
        cleaner.save_data()
        cleaner.print_stats()
        
        # Show sample of cleaned data
        if cleaner.articles:
            print("\n📝 Sample of cleaned data:")
            print("=" * 80)
            sample = cleaner.articles[0]
            print(f"Title: {sample['title']}")
            print(f"URL: {sample['url']}")
            if 'date' in sample:
                print(f"Date: {sample['date']}")
            print(f"Content length: {len(sample['content'])} characters")
            print(f"Content preview: {sample['content'][:200]}...")
    else:
        print("Cleaning failed. Please check the error messages above.")

if __name__ == '__main__':
    main()

