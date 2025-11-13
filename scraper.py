#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
5AM Ramen Website Scraper
Scrape blog article data
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os
from urllib.parse import urljoin, urlparse
import re

class RamenScraper:
    def __init__(self, base_url="https://www.5amramen.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.articles = []
        
    def get_page(self, url):
        """Fetch webpage content"""
        try:
            print(f"Scraping: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Failed to fetch page {url}: {e}")
            return None
    
    def parse_article_list(self, html):
        """Parse article list page"""
        soup = BeautifulSoup(html, 'html.parser')
        article_links = []
        
        # Find all article links
        # Based on website structure, articles may be in various tags
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            # Find blog article links
            if '/blog/' in href or href.startswith('/blog/'):
                full_url = urljoin(self.base_url, href)
                if full_url not in article_links:
                    article_links.append(full_url)
        
        # Also find possible article cards or list items
        for article in soup.find_all(['article', 'div'], class_=re.compile(r'article|post|blog', re.I)):
            link = article.find('a', href=True)
            if link:
                href = link.get('href', '')
                full_url = urljoin(self.base_url, href)
                if full_url not in article_links:
                    article_links.append(full_url)
        
        return article_links
    
    def parse_article_detail(self, html, url):
        """Parse single article detail"""
        soup = BeautifulSoup(html, 'html.parser')
        
        article_data = {
            'url': url,
            'title': '',
            'content': '',
            'date': '',
            'author': '',
            'tags': [],
            'categories': []
        }
        
        # Extract title
        title_tag = soup.find('h1') or soup.find('title')
        if title_tag:
            article_data['title'] = title_tag.get_text().strip()
        
        # Extract date
        # Find common date formats
        date_patterns = [
            soup.find('time'),
            soup.find('span', class_=re.compile(r'date|time', re.I)),
            soup.find('div', class_=re.compile(r'date|time|published', re.I))
        ]
        for date_tag in date_patterns:
            if date_tag:
                date_text = date_tag.get_text().strip()
                if date_text:
                    article_data['date'] = date_text
                    break
        
        # Extract article content
        # Find main content area
        content_selectors = [
            soup.find('article'),
            soup.find('div', class_=re.compile(r'content|post-content|article-content|entry', re.I)),
            soup.find('main'),
            soup.find('div', class_=re.compile(r'blog-post|post-body', re.I))
        ]
        
        content_text = []
        for selector in content_selectors:
            if selector:
                # Extract all paragraphs
                paragraphs = selector.find_all('p')
                for p in paragraphs:
                    text = p.get_text().strip()
                    if text and len(text) > 20:  # Filter out too short text
                        content_text.append(text)
                if content_text:
                    break
        
        # If not found, try to extract all p tags
        if not content_text:
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.get_text().strip()
                if text and len(text) > 20:
                    content_text.append(text)
        
        article_data['content'] = '\n\n'.join(content_text)
        
        # Extract author
        author_tag = soup.find('span', class_=re.compile(r'author', re.I)) or \
                     soup.find('div', class_=re.compile(r'author', re.I))
        if author_tag:
            article_data['author'] = author_tag.get_text().strip()
        
        # Extract tags and categories
        tag_tags = soup.find_all('a', class_=re.compile(r'tag', re.I)) or \
                   soup.find_all('span', class_=re.compile(r'tag', re.I))
        for tag in tag_tags:
            tag_text = tag.get_text().strip()
            if tag_text:
                article_data['tags'].append(tag_text)
        
        return article_data
    
    def scrape_blog(self, max_pages=10):
        """Scrape blog articles"""
        print("Starting to scrape 5AM Ramen blog...")
        
        # First get homepage
        homepage_html = self.get_page(self.base_url)
        if not homepage_html:
            print("Unable to fetch homepage")
            return
        
        # Get blog page
        blog_url = urljoin(self.base_url, '/blog')
        blog_html = self.get_page(blog_url)
        if not blog_html:
            blog_html = homepage_html  # If blog page doesn't exist, use homepage
        
        # Parse article list
        article_links = self.parse_article_list(blog_html)
        
        # Also parse from homepage
        homepage_links = self.parse_article_list(homepage_html)
        article_links.extend(homepage_links)
        
        # Remove duplicates
        article_links = list(set(article_links))
        
        print(f"Found {len(article_links)} articles")
        
        # Scrape each article
        for i, article_url in enumerate(article_links[:max_pages], 1):
            print(f"\n[{i}/{len(article_links)}] Processing: {article_url}")
            
            article_html = self.get_page(article_url)
            if article_html:
                article_data = self.parse_article_detail(article_html, article_url)
                if article_data['title'] or article_data['content']:
                    self.articles.append(article_data)
                    print(f"✓ Successfully extracted: {article_data['title'][:50]}...")
                else:
                    print("⚠ Article content is empty, skipping")
            
            # Polite delay
            time.sleep(1)
        
        print(f"\nScraping completed! Retrieved {len(self.articles)} articles")
    
    def save_data(self, filename='scraped_data.json'):
        """Save scraped data"""
        output_dir = 'data'
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.articles, f, ensure_ascii=False, indent=2)
        
        print(f"\nData saved to: {filepath}")
        return filepath

def main():
    scraper = RamenScraper()
    scraper.scrape_blog(max_pages=50)  # Scrape up to 50 articles
    scraper.save_data()

if __name__ == '__main__':
    main()

