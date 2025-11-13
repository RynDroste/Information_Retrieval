#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool script to view scraping results
"""

import json
import os
import sys

def view_results(filename='data/scraped_data.json', show_content=False, limit=None):
    """View scraping results"""
    if not os.path.exists(filename):
        print(f"Error: File {filename} does not exist")
        print("Please run scraper.py first to scrape data")
        return
    
    with open(filename, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print("=" * 80)
    print(f"📊 Scraping Results Statistics")
    print("=" * 80)
    print(f"Total articles: {len(articles)}")
    print(f"Data file: {filename}")
    print(f"File size: {os.path.getsize(filename) / 1024:.2f} KB")
    print()
    
    # Display article list
    print("=" * 80)
    print("📝 Article List")
    print("=" * 80)
    
    articles_to_show = articles[:limit] if limit else articles
    
    for i, article in enumerate(articles_to_show, 1):
        print(f"\n[{i}] {article.get('title', 'No Title')}")
        print(f"    URL: {article.get('url', 'N/A')}")
        if article.get('date'):
            print(f"    Date: {article.get('date')}")
        if article.get('author'):
            print(f"    Author: {article.get('author')}")
        
        content = article.get('content', '')
        if content:
            content_preview = content[:100].replace('\n', ' ')
            print(f"    Content preview: {content_preview}...")
            if show_content:
                print(f"    Full content:\n    {content}")
        
        if article.get('tags'):
            print(f"    Tags: {', '.join(article.get('tags', []))}")
    
    if limit and len(articles) > limit:
        print(f"\n... {len(articles) - limit} more articles not shown")
    
    print("\n" + "=" * 80)
    print("💡 Tips:")
    print("  - Use python3 view_results.py --content to view full content")
    print("  - Use python3 view_results.py --limit 5 to show only first 5 articles")
    print("  - Data saved in data/scraped_data.json")
    print("=" * 80)

def main():
    show_content = '--content' in sys.argv or '-c' in sys.argv
    limit = None
    
    # Parse limit parameter
    if '--limit' in sys.argv:
        idx = sys.argv.index('--limit')
        if idx + 1 < len(sys.argv):
            try:
                limit = int(sys.argv[idx + 1])
            except ValueError:
                print("Error: --limit parameter must be a number")
                return
    
    view_results(show_content=show_content, limit=limit)

if __name__ == '__main__':
    main()

