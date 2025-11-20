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
    
    def is_non_food_product(self, article):
        """Check if product is non-food (merchandise, utensils, clothing, etc.)"""
        title = article.get('title', '').lower()
        content = article.get('content', '').lower()
        combined = f'{title} {content}'
        
        # Strong food keywords - if present, product is likely food
        food_keywords = ['ramen', 'tsukemen', 'noodle', 'soba', 'chashu', 'pork', 'chicken', 'egg', 'menma', 'mizuna', 'nori', 'yuzu', 'shio', 'shoyu', 'soup', 'broth', 'hotpot', 'nabe', 'meat', 'meatball', 'bamboo', 'spicy', 'seasoned', 'ingredient', 'duck', 'char siu', 'nitamago', 'gohan', 'roast', 'fillet', 'charred']
        
        # Check for specific non-food patterns first (these override food keywords)
        # These patterns should appear in the title, not just in content/description
        non_food_patterns_in_title = [
            'original ramen bowl', 'original bowl', 'half ramen bowl',
            'original mug', 'original tokkuri', 'ramen tebo',
            't-shirt', 'tshirt', 'socks', 'apron', 'typography t-shirt',
            'gift wrapping', 'noshi', 'eco bag', 'umbrella', 'thermos',
            'pin badge', 'charm', 'keychain', '20th anniversary'
        ]
        
        # Patterns that can appear anywhere (more specific)
        non_food_patterns_anywhere = [
            'afuri original rice bowl', 'original rice bowl',  # Only if "original" is present
        ]
        
        # If it contains strong food keywords, check if it's actually food packaging
        has_food_keyword = any(kw in combined for kw in food_keywords)
        
        if has_food_keyword:
            # Check if title contains non-food patterns (more reliable)
            if any(pattern in title for pattern in non_food_patterns_in_title):
                return True
            # Check for "original rice bowl" pattern (must have "original" to avoid false positives)
            if any(pattern in combined for pattern in non_food_patterns_anywhere):
                return True
            # Otherwise it's food (even if it says "bags of pork", those are food bags)
            return False
        
        # Non-food keywords (only check if no food keywords found)
        # Exclude generic words like "bag" that might appear in food contexts
        non_food_keywords = {
            'utensils': ['original bowl', 'original mug', 'original tokkuri', 'ramen tebo', 'rice bowl', 'half ramen bowl'],
            'clothing': ['t-shirt', 'tshirt', 'shirt', 'cap', 'hat', '帽子', 'socks', 'apron', 'sweatshirt', 'hoodie'],
            'merchandise': ['gift wrapping', 'noshi', 'towel', '毛巾', 'eco bag', 'umbrella', 'thermos', 'pin', 'badge', 'charm', 'keychain', 'キーホルダー', 'poster', 'calendar', 'カレンダー'],
            'other': ['sticker', 'book', '本', 'magazine', '雑誌']
        }
        
        # Only check non-food keywords if no food keywords were found
        # This prevents "bags of pork" from being misclassified
        # Note: "bag" alone is not in the list, only "eco bag" is, so "bags of pork" won't match
        for category, keywords in non_food_keywords.items():
            for kw in keywords:
                if kw in combined:
                    return True
        
        return False
    
    def clean_price(self, price_text):
        """Clean price text - only keep yen symbol and numbers"""
        if not price_text:
            return ''
        
        price_str = str(price_text).strip()
        
        # Find all matches of yen symbol (¥ or ￥) followed by numbers and commas
        # Pattern: ¥ or ￥ followed by digits and commas
        pattern = r'[¥￥][\d,]+'
        matches = re.findall(pattern, price_str)
        
        if matches:
            # Normalize yen symbol to ¥
            matches = [m.replace('￥', '¥') for m in matches]
            # Take the first match (usually sale price when "Sale price" is present)
            cleaned_price = matches[0]
            return cleaned_price
        
        # If no yen symbol found, try to extract just numbers with commas
        # This handles cases where yen symbol might be missing
        numbers = re.findall(r'[\d,]+', price_str)
        if numbers:
            # Take the largest number (usually the price)
            largest = max(numbers, key=lambda x: int(x.replace(',', '')))
            return f'¥{largest}'
        
        return ''
    
    def get_price_range(self, price_text):
        """Calculate price range category from price text"""
        if not price_text:
            return ''
        
        # Extract numeric value from price string (e.g., "¥3,580" -> 3580)
        price_str = str(price_text).strip()
        numbers = re.findall(r'[\d,]+', price_str)
        
        if not numbers:
            return ''
        
        # Get the first/largest number
        price_value_str = max(numbers, key=lambda x: int(x.replace(',', '')))
        try:
            price_value = int(price_value_str.replace(',', ''))
        except ValueError:
            return ''
        
        # Define price ranges
        if price_value < 1000:
            return '< ¥1,000'
        elif price_value < 2000:
            return '¥1,000 - ¥2,000'
        elif price_value < 3000:
            return '¥2,000 - ¥3,000'
        elif price_value < 5000:
            return '¥3,000 - ¥5,000'
        elif price_value < 10000:
            return '¥5,000 - ¥10,000'
        else:
            return '> ¥10,000'
    
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
        title = article.get('title', '').strip()
        content = article.get('content', '')
        section = article.get('section', '')
        
        # Must have at least a title
        if not title:
            return False
        
        # For Menu items, allow empty content if title exists (for gift items, etc.)
        if section == 'Menu':
            return True
        
        # Set minimum length based on section type
        if section == 'Store Information':
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
        # Always preserve price field if it exists in original data
        if 'price' in article:
            price_value = article.get('price', '')
            if price_value:
                cleaned['price'] = self.clean_price(price_value)
                # Calculate price range
                cleaned['price_range'] = self.get_price_range(cleaned['price'])
            else:
                cleaned['price'] = ''
                cleaned['price_range'] = ''
        else:
            cleaned['price'] = ''
            cleaned['price_range'] = ''
        
        # Extract introduction - first check if it exists, otherwise extract from content
        introduction = ''
        if 'introduction' in article and article.get('introduction', '').strip():
            introduction = article.get('introduction', '').strip()
        else:
            # Try to extract introduction from content (usually the last line with comma-separated English introduction)
            content = cleaned.get('content', '')
            if content and cleaned.get('section') == 'Menu':
                lines = content.split('\n')
                for line in reversed(lines):
                    line = line.strip()
                    # Check if line contains common introduction patterns (comma-separated, lowercase/English)
                    if ',' in line and len(line) > 20:
                        # Check if it looks like introduction (contains common food words)
                        introduction_keywords = ['broth', 'chashu', 'nori', 'egg', 'yuzu', 'menma', 'mizuna', 'dashi', 'shoyu', 'chicken', 'nitamago', 'negi']
                        if any(keyword in line.lower() for keyword in introduction_keywords):
                            introduction = line
                            break
        
        if introduction:
            cleaned['introduction'] = introduction
        
        # Handle tags
        if 'tags' in article and article.get('tags'):
            cleaned['tags'] = [tag.strip() for tag in article.get('tags', []) if tag.strip()]
        else:
            cleaned['tags'] = []
        
        # Add 'others' tag for non-food products
        if cleaned.get('section') == 'Menu' and self.is_non_food_product(article):
            if 'others' not in cleaned['tags']:
                cleaned['tags'].append('others')
        
        # Set menu_category to 'others' if tags contain 'others'
        if cleaned.get('section') == 'Menu' and 'others' in cleaned.get('tags', []):
            cleaned['menu_category'] = 'Others'
        
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
            
            # Allow articles with title even if content is empty (for gift items, etc.)
            if cleaned['title']:
                # If content is empty, use title as content for Menu items
                if not cleaned['content'] and cleaned.get('section') == 'Menu':
                    cleaned['content'] = cleaned['title']
                
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

