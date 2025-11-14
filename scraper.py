#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AFURI Website Scraper
Scrape website content from afuri.com
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import re
from urllib.parse import urljoin

class RamenScraper:
    def __init__(self, base_url="https://afuri.com"):
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
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
        except requests.RequestException as e:
            print(f"Failed to fetch page {url}: {e}")
            return None
    
    def is_descriptive_text(self, text):
        """Check if text is a descriptive sentence rather than a menu item name"""
        # Known menu item names that should never be filtered
        known_menu_items = [
            'Yuzu Shio Ramen', 'Yuzu Shoyu Ramen', 'Shio Ramen', 'Shoyu Ramen',
            'Yuzu Ratan Ramen', 'Rainbow Vegan Ramen', 'Summer Limited Cold Yuzu Shio Ramen',
            'Ama-tsuyu Tsukemen', 'Yuzu-tsuyu Tsukemen', 'Kara-tsuyu Tsukemen', 'Yuzu-kara-tsuyu Tsukemen',
            'Gokuboso Men', 'Temomi Men', 'Konnyaku Men',
            'Aburi Koro Pork Chashu Gohan', 'Pork Niku Gohan', 'Hongarebushi Okaka Gohan',
            'Tare Gohan', 'Gohan', 'Pork Aburi Chashu', 'Kaku-ni Chashu',
            'Nitamago', 'Menma', 'Nori', 'Mizuna', 'Nori 7 pieces',
            'Draft Beer', 'Whisky Soda AFURI\'s style', 'Japanese SAKE'
        ]
        
        # If it's a known menu item, don't filter it
        if text in known_menu_items or any(text.startswith(item) for item in known_menu_items if len(item) > 10):
            return False
        
        # Descriptive patterns that indicate this is not a menu item name
        descriptive_patterns = [
            'お選び', 'お楽しみ', 'いただけます', 'ご用意', 'ご変更',
            'は、', 'の量を', 'の麺は', 'の喉越し', 'を最大限に',
            'から', 'へ', 'など', '♡', '。', '、',
            '選び', '変更', '用意', 'お召し上がり', 'お好みで'
        ]
        
        # Check if text starts with descriptive patterns
        if any(text.startswith(pattern) for pattern in ['麺は', 'らーめんの', 'つけ麺の', '鶏油の', 'AFURIの', 'AFURIが', 'つるつるの']):
            return True
        
        # Check if text contains multiple descriptive patterns
        pattern_count = sum(1 for pattern in descriptive_patterns if pattern in text)
        if pattern_count >= 2:
            return True
        
        # Check if text is too long (descriptions are usually longer than menu item names)
        # But allow longer known menu items
        if len(text) > 60 and not any(item in text for item in known_menu_items if len(item) > 20):
            return True
        
        # Check if text contains sentence-ending punctuation and is descriptive
        if ('。' in text or '、' in text) and len(text) > 30:
            # But allow if it's a known menu item that happens to have punctuation
            if not any(item in text[:50] for item in known_menu_items):
                return True
        
        return False
    
    def parse_menu_page(self, soup, url):
        """Parse AFURI menu page - extract detailed menu items"""
        menu_items = []
        
        # Menu categories
        categories = {
            'Ramen': ['Yuzu Shio Ramen', 'Yuzu Shoyu Ramen', 'Shio Ramen', 'Shoyu Ramen', 
                     'Yuzu Ratan Ramen', 'Rainbow Vegan Ramen', 'Summer Limited', 'Seasonal Limited',
                     'Ama-tsuyu Tsukemen', 'Yuzu-tsuyu Tsukemen', 'Kara-tsuyu Tsukemen', 
                     'Yuzu-kara-tsuyu Tsukemen', 'つけ麺', 'Tsukemen'],
            'Chi-yu': ['Chi-yu', '鶏油', 'Tanrei', 'Maroaji', '淡麗', 'まろ味'],
            'Noodles': ['Gokuboso Men', 'Temomi Men', 'Konnyaku Men', '麺'],
            'Side Dishes': ['Chashu', 'Nitamago', 'Menma', 'Nori', 'Mizuna', 'Gohan', 'チャーシュー', 'ごはん'],
            'Drinks': ['Beer', 'Whisky', 'SAKE', 'ビール', '酒']
        }
        
        all_text = soup.get_text()
        list_items = soup.find_all('li')
        paragraphs = soup.find_all('p')
        
        # Process list items
        for li in list_items:
            text = li.get_text().strip()
            if not text or len(text) < 10:
                continue
            
            # Determine category
            item_category = None
            for cat_name, keywords in categories.items():
                if any(keyword in text for keyword in keywords):
                    item_category = cat_name
                    break
            
            if item_category:
                item_name = text.split('\n')[0].strip()[:50] if '\n' in text else text[:50]
                
                # Skip if this is descriptive text, not a menu item name
                if self.is_descriptive_text(item_name):
                    continue
                
                # Check for known side dishes by name first (before checking text content)
                if item_name in ['Nori', 'Menma', 'Mizuna', 'Nitamago', 'Chashu', 'Pork Aburi Chashu', 'Kaku-ni Chashu']:
                    item_category = 'Side Dishes'
                # Check if name contains Tsukemen and set category accordingly
                elif 'Tsukemen' in item_name or 'tsukemen' in item_name.lower():
                    item_category = 'Tsukemen'
                # Add AFURI keyword to content and tags
                content_with_afuri = f"AFURI {text}" if "AFURI" not in text.upper() else text
                menu_data = {
            'url': url,
                    'title': item_name,
                    'content': content_with_afuri,
                    'section': 'Menu',
                    'menu_item': item_name,
                    'menu_category': item_category,
            'date': '',
            'author': '',
                    'tags': ['afuri'],
            'categories': []
        }
                menu_items.append(menu_data)
        
        # Process paragraphs
        for p in paragraphs:
            text = p.get_text().strip()
            if not text or len(text) < 20:
                continue
            
            if any(keyword in text for keyword in ['Ramen', 'Tsukemen', 'Chashu', 'Men', 'Gohan', 'Beer', 
                                                   'らーめん', 'つけ麺', 'チャーシュー', '麺', 'ごはん']):
                item_name = text.split('\n')[0].strip()[:50]
                
                # Skip if this is descriptive text, not a menu item name
                if self.is_descriptive_text(item_name):
                    continue
                
                if not any(item['menu_item'] == item_name for item in menu_items):
                    item_category = 'Ramen'
                    # Check for known side dishes by name first (before checking text content)
                    if item_name in ['Nori', 'Menma', 'Mizuna', 'Nitamago', 'Chashu', 'Pork Aburi Chashu', 'Kaku-ni Chashu']:
                        item_category = 'Side Dishes'
                    else:
                        for cat_name, keywords in categories.items():
                            if any(keyword in text for keyword in keywords):
                                item_category = cat_name
                                break
                    
                    # Check if name contains Tsukemen and set category accordingly
                    if 'Tsukemen' in item_name or 'tsukemen' in item_name.lower():
                        item_category = 'Tsukemen'
                    
                    # Add AFURI keyword to content and tags
                    content_with_afuri = f"AFURI {text}" if "AFURI" not in text.upper() else text
                    menu_data = {
                        'url': url,
                        'title': item_name,
                        'content': content_with_afuri,
                        'section': 'Menu',
                        'menu_item': item_name,
                        'menu_category': item_category,
                        'date': '',
                        'author': '',
                        'tags': ['afuri'],
                        'categories': []
                    }
                    menu_items.append(menu_data)
        
        # Extract specific menu items by name
        # Sort by length (longest first) to avoid matching shorter names when longer ones exist
        menu_item_names = [
            'Yuzu Shio Ramen', 'Yuzu Shoyu Ramen', 'Shio Ramen', 'Shoyu Ramen',
            'Yuzu Ratan Ramen', 'Rainbow Vegan Ramen', 'Summer Limited Cold Yuzu Shio Ramen',
            'Ama-tsuyu Tsukemen', 'Yuzu-tsuyu Tsukemen', 'Kara-tsuyu Tsukemen', 'Yuzu-kara-tsuyu Tsukemen',
            'Gokuboso Men', 'Temomi Men', 'Konnyaku Men',
            'Aburi Koro Pork Chashu Gohan', 'Pork Niku Gohan', 'Hongarebushi Okaka Gohan',
            'Tare Gohan', 'Gohan', 'Pork Aburi Chashu', 'Kaku-ni Chashu',
            'Nitamago', 'Menma', 'Nori 7 pieces', 'Nori', 'Mizuna',
            'Draft Beer', 'Whisky Soda AFURI\'s style', 'Japanese SAKE'
        ]
        
        # Sort by length (longest first) to prioritize more specific names
        menu_item_names.sort(key=len, reverse=True)
        
        for item_name in menu_item_names:
            if any(item['menu_item'] == item_name for item in menu_items):
                continue
            
            if item_name in all_text:
                # Check if a more specific version of this item already exists
                # For example, if "Nori 7 pieces" exists, don't add "Nori"
                has_more_specific = False
                for existing_item in menu_items:
                    existing_name = existing_item.get('menu_item', '')
                    # Check if existing item is a more specific version (contains current item name + more)
                    if existing_name != item_name and item_name in existing_name and len(existing_name) > len(item_name):
                        has_more_specific = True
                        break
                
                if has_more_specific:
                    continue
                
                for elem in soup.find_all(['p', 'li', 'div']):
                    text = elem.get_text().strip()
                    # Check for exact match or match followed by space/newline/punctuation
                    # This avoids partial matches like "Nori" matching "Nori 7 pieces"
                    # But allows "Nori" to match "Nori\n" or "Nori " or "Nori."
                    item_name_escaped = re.escape(item_name)
                    # Match item_name at word boundary, followed by space, newline, punctuation, or end of string
                    pattern = r'\b' + item_name_escaped + r'(?:\s|$|[。、，,\.\n])'
                    if re.search(pattern, text) and len(text) > len(item_name) + 10:
                        # Additional check: if text contains a longer menu item name that includes this one, skip
                        # For example, if text contains "Nori 7 pieces", don't match "Nori"
                        should_skip = False
                        for other_item in menu_item_names:
                            if other_item != item_name and len(other_item) > len(item_name) and item_name in other_item:
                                if other_item in text:
                                    should_skip = True
                                    break
                        if should_skip:
                            continue
                        # Extract only the relevant content for this menu item
                        # Find the menu item name in the text and extract content after it
                        item_name_index = text.find(item_name)
                        relevant_content = ''
                        text_after_item = ''
                        
                        if item_name_index >= 0:
                            # Get text after the menu item name
                            text_after_item = text[item_name_index + len(item_name):].strip()
                            
                            # Extract content until we hit another menu item name or a clear separator
                            # Look for the next menu item name or stop at certain patterns
                            lines = text_after_item.split('\n')
                            relevant_lines = []
                            for line in lines:
                                line = line.strip()
                                if not line:
                                    # If we hit an empty line after some content, it might be a separator
                                    if len(relevant_lines) > 0:
                                        # Check if next non-empty line looks like another menu item
                                        break
                                    continue
                                
                                # Stop if we encounter another menu item name (check against all known menu items)
                                is_another_menu_item = False
                                for other_item in menu_item_names:
                                    if other_item != item_name and line.startswith(other_item):
                                        is_another_menu_item = True
                                        break
                                
                                if is_another_menu_item:
                                    break
                                
                                # Stop if we hit certain section markers
                                if line in ['アレルゲン情報Allergen information', 'Allergen information', 
                                           'アレルゲン情報', '* All our rice']:
                                    break
                                
                                relevant_lines.append(line)
                            
                            # Use only the relevant content, not the entire text
                            relevant_content = '\n'.join(relevant_lines).strip()
                            if not relevant_content:
                                # Fallback: use text after item name, but limit to reasonable length
                                relevant_content = text_after_item[:500].strip()
                            
                            # Use the original item name + relevant content
                            item_content = f"{item_name}\n{relevant_content}" if relevant_content else item_name
                        else:
                            item_content = text
                        
                        item_category = 'Ramen'
                        # Check if name contains Tsukemen first
                        if 'Tsukemen' in item_name or 'tsukemen' in item_name.lower():
                            item_category = 'Tsukemen'
                        elif 'Men' in item_name and 'Tsukemen' not in item_name and 'Ramen' not in item_name:
                            item_category = 'Noodles'
                        elif 'Gohan' in item_name:
                            item_category = 'Side Dishes'
                        elif 'Beer' in item_name or 'Whisky' in item_name or 'SAKE' in item_name:
                            item_category = 'Drinks'
                        # Check for known side dishes by name (before checking text content)
                        elif item_name in ['Nori', 'Menma', 'Mizuna', 'Nitamago', 'Chashu', 'Pork Aburi Chashu', 'Kaku-ni Chashu']:
                            item_category = 'Side Dishes'
                        # Only check text content for Chi-yu if not already categorized
                        elif item_category == 'Ramen' and ('Chi-yu' in text or '鶏油' in text):
                            item_category = 'Chi-yu'
                        
                        # Add AFURI keyword to content and tags
                        content_with_afuri = f"AFURI {item_content}" if "AFURI" not in item_content.upper() else item_content
                        
                        # Extract ingredients from the relevant content
                        ingredients = ''
                        # Use relevant_content if available, otherwise use text_after_item
                        content_to_search = relevant_content if relevant_content else text_after_item
                        if content_to_search:
                            lines = content_to_search.split('\n')
                            for line in reversed(lines):
                                line = line.strip()
                                # Check if line contains common ingredient patterns (comma-separated, lowercase/English)
                                if ',' in line and len(line) > 20:
                                    # Check if it looks like ingredients (contains common food words)
                                    ingredient_keywords = ['broth', 'chashu', 'nori', 'egg', 'yuzu', 'menma', 'mizuna', 'dashi', 'shoyu', 'chicken', 'rice', 'pork', 'beef', 'seaweed', 'ginger', 'negi', 'onion']
                                    if any(keyword in line.lower() for keyword in ingredient_keywords):
                                        ingredients = line
                                        break
                        
                        menu_data = {
                            'url': url,
                            'title': item_name,
                            'content': content_with_afuri,
                            'section': 'Menu',
                            'menu_item': item_name,
                            'menu_category': item_category,
                            'ingredients': ingredients,
                            'date': '',
                            'author': '',
                            'tags': ['afuri'],
                            'categories': []
                        }
                        menu_items.append(menu_data)
                        break
        
        return menu_items
    
    def scrape_menu_page(self, menu_url=None):
        """Scrape AFURI menu page specifically"""
        if menu_url is None:
            menu_url = urljoin(self.base_url, '/menu/')
        
        print(f"Starting to scrape AFURI menu page: {menu_url}")
        
        menu_html = self.get_page(menu_url)
        if not menu_html:
            print("Unable to fetch menu page")
            return
        
        soup = BeautifulSoup(menu_html, 'html.parser')
        
        print("\nExtracting menu items...")
        
        menu_items = self.parse_menu_page(soup, menu_url)
        
        for menu in menu_items:
            if menu['content']:
                self.articles.append(menu)
                print(f"    ✓ Menu item: {menu['menu_item']} ({menu.get('menu_category', 'Unknown')})")
        
        print(f"\nMenu scraping completed! Retrieved {len(menu_items)} menu items")
    
    def parse_store_information(self, soup, url):
        """Parse AFURI findus page - extract detailed store information"""
        stores = []
        
        all_text = soup.get_text()
        lines = all_text.split('\n')
        
        # Process lines to extract store information
        # Each store section starts with "Google map" followed by store name
        current_store = None
        store_content_lines = []
        in_store_section = False
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            # Detect start of a new store section (usually after "Google map")
            if 'Google map' in line.lower() or line == 'Google map':
                # Save previous store if exists
                if current_store and store_content_lines:
                    store_content = '\n'.join([current_store] + store_content_lines)
                    if current_store not in [s['store_name'] for s in stores]:
                        store_data = {
                            'url': url,
                            'title': f'Store - {current_store}',
                            'content': store_content,
                            'section': 'Store Information',
                            'store_name': current_store,
                            'date': '',
                            'author': '',
                            'tags': ['afuri'],
                            'categories': []
                        }
                        stores.append(store_data)
                
                # Reset for new store
                current_store = None
                store_content_lines = []
                in_store_section = True
                i += 1
                continue
            
            # If we're in a store section, extract store name from address or explicit name
            if in_store_section and not current_store:
                # Method 1: Check if line explicitly contains store name
                if (line.startswith('AFURI') and 
                    any(keyword in line for keyword in ['恵比寿', 'Ebisu', '原宿', 'Harajuku', 
                                                       '中目黒', 'Nakameguro', '麻布十番', 'Azabujuban',
                                                       '六本木', 'Roppongi', '三軒茶屋', 'Sangenjaya',
                                                       '新宿', 'Shinjuku', '横浜', 'Yokohama', 
                                                       '南青山', 'Minamiaoyama', '辛紅', 'kara kurenai',
                                                       '有楽町', 'Yurakucho'])):
                    # Extract store name (take first part before TEL: or other details)
                    store_name = line.split('TEL:')[0].split('AFURI kara')[0].strip()
                    if store_name:
                        current_store = store_name
                        in_store_section = False
                        # Add the rest as content
                        if 'TEL:' in line:
                            store_content_lines.append(line[line.find('TEL:'):])
                        i += 1
                        continue
                
                # Method 2: Extract from address information
                # Look for location keywords in the address line
                location_map = {
                    '恵比寿': 'AFURI 恵比寿', 'Ebisu': 'AFURI 恵比寿',
                    '千駄ヶ谷': 'AFURI 原宿', 'Sendagaya': 'AFURI 原宿',
                    '上目黒': 'AFURI 中目黒', 'Kamimeguro': 'AFURI 中目黒', 'Nakameguro': 'AFURI 中目黒',
                    '麻布十番': 'AFURI 麻布十番', 'Azabujuban': 'AFURI 麻布十番',
                    '六本木4-9-4': 'AFURI 六本木交差点', '六本木6-4-1': 'AFURI 六本木ヒルズ',
                    '三軒茶屋': 'AFURI 三軒茶屋', 'Sangenjaya': 'AFURI 三軒茶屋',
                    '西新宿1-1-5': '新宿ルミネ', 'Nishi-Shinjuku': '新宿ルミネ',
                    '西新宿2丁目6-1': 'AFURI 新宿住友ビル', 'Nishi-shinjuku': 'AFURI 新宿住友ビル',
                    '南青山': 'AFURI 南青山', 'Minamiaoyama': 'AFURI 南青山',
                    '横浜ジョイナス': 'AFURI 横浜ジョイナス', 'Yokohama-joinus': 'AFURI 横浜ジョイナス',
                    '横浜ランドマーク': '横浜ランドマークタワー', 'Landmark Tower': '横浜ランドマークタワー',
                    '町田': 'Minamimachida', 'Machida': 'Minamimachida',
                    '歌舞伎町': 'AFURI 辛紅', '辛紅': 'AFURI 辛紅',
                    '有楽町': 'AFURI有楽町', 'Yurakucho': 'AFURI有楽町',
                    # Overseas stores
                    'ポートランド': 'AFURI ramen + izakaya Portland', 'Portland': 'AFURI ramen + izakaya Portland',
                    'スラブタウン': 'AFURI ramen + dumplings Portland', 'Slabtown': 'AFURI ramen + dumplings Portland',
                    'ブルックリン': 'AFURI ramen + dumplings Brooklyn', 'Brooklyn': 'AFURI ramen + dumplings Brooklyn',
                    'ヒューストン': 'AFURI ramen + dumplings Houston', 'Houston': 'AFURI ramen + dumplings Houston',
                    'ロサンゼルス': 'AFURI ramen + dumpling Los Angeles', 'Los Angeles': 'AFURI ramen + dumpling Los Angeles',
                    'カルバーシティ': 'AFURI ramen + dumpling Culver City', 'Culver City': 'AFURI ramen + dumpling Culver City',
                    '香港': 'AFURI ramen + dumpling Hongkong', 'Hongkong': 'AFURI ramen + dumpling Hongkong',
                    'リッチモンド': 'AFURI ramen + dumpling Richmond', 'Richmond': 'AFURI ramen + dumpling Richmond',
                    'トロント': 'AFURI ramen + dumpling Toronto', 'Toronto': 'AFURI ramen + dumpling Toronto',
                    'ZUND-BAR': 'ZUND-BAR', 'Zund-bar': 'ZUND-BAR'
                }
                
                # Check if line contains address information
                if (('東京都' in line or '神奈川' in line or '北海道' in line or 'TEL:' in line or 
                     'Portland' in line or 'Brooklyn' in line or 'Houston' in line or 
                     'Los Angeles' in line or 'Culver City' in line or 'Hongkong' in line or
                     'Richmond' in line or 'Toronto' in line or 'Canada' in line or 'USA' in line or
                     'アメリカ合衆国' in line or 'カナダ' in line or 'オレゴン州' in line or
                     'テキサス州' in line or 'カリフォルニア州' in line or 'ニューヨーク州' in line) 
                    and not current_store):
                    for keyword, store_name in location_map.items():
                        if keyword in line:
                            current_store = store_name
                            in_store_section = False
                            store_content_lines.append(line)
                            i += 1
                            break
                    if current_store:
                        continue
            
            # Collect store details if we have a store name
            if current_store:
                # Collect relevant information (phone, hours, address, etc.)
                if (line.startswith('TEL:') or 'TEL:' in line or
                    '※完全キャッシュレス' in line or '※' in line or
                    '11:00' in line or '10:00' in line or '12:00' in line or '16:00' in line or
                    'Open' in line or '営業' in line or '年中無休' in line or
                    '東京都' in line or '神奈川' in line or '北海道' in line or
                    'Address' in line or '住所' in line or
                    'B1F' in line or '1F' in line or 'B2F' in line or '1階' in line or '2階' in line or
                    'Monday' in line or '月曜' in line or 'Sunday' in line or '日曜' in line or
                    'Friday' in line or '金曜' in line or 'Saturday' in line or '土曜' in line or
                    'am' in line.lower() or 'pm' in line.lower() or
                    'Portland' in line or 'Brooklyn' in line or 'Houston' in line or
                    'Los Angeles' in line or 'Culver City' in line or 'Hongkong' in line or
                    'Toronto' in line or 'Richmond' in line or 'Canada' in line or 'USA' in line or
                    'アメリカ合衆国' in line or 'カナダ' in line or 'オレゴン州' in line or
                    'テキサス州' in line or 'カリフォルニア州' in line or 'ニューヨーク州' in line or
                    'www.afuri' in line.lower() or 'facebook' in line.lower() or
                    'Reservation' in line):
                    if line not in store_content_lines and len(line) > 3:
                        store_content_lines.append(line)
                # If we encounter another "Google map", it means we've finished this store
                elif 'Google map' in line.lower():
                    # Save current store
                    if current_store and store_content_lines:
                        store_content = '\n'.join([current_store] + store_content_lines)
                        if current_store not in [s['store_name'] for s in stores]:
                            store_data = {
                                'url': url,
                                'title': f'Store - {current_store}',
                                'content': store_content,
                                'section': 'Store Information',
                                'store_name': current_store,
                                'date': '',
                                'author': '',
                                'tags': ['afuri'],
                                'categories': []
                            }
                            stores.append(store_data)
                    
                    # Reset for next store
                    current_store = None
                    store_content_lines = []
                    in_store_section = True
            
            i += 1
        
        # Save last store
        if current_store and store_content_lines:
            store_content = '\n'.join([current_store] + store_content_lines)
            if current_store not in [s['store_name'] for s in stores]:
                store_data = {
                    'url': url,
                    'title': f'Store - {current_store}',
                    'content': store_content,
                    'section': 'Store Information',
                    'store_name': current_store,
                    'date': '',
                    'author': '',
                    'tags': ['afuri'],
                    'categories': []
                }
                stores.append(store_data)
        
        return stores
    
    def scrape_store_information(self, findus_url=None):
        """Scrape AFURI findus page for store information"""
        if findus_url is None:
            findus_url = urljoin(self.base_url, '/findus/')
        
        print(f"Starting to scrape AFURI store information: {findus_url}")
        
        findus_html = self.get_page(findus_url)
        if not findus_html:
            print("Unable to fetch findus page")
            return
        
        soup = BeautifulSoup(findus_html, 'html.parser')
        
        print("\nExtracting store information...")
        
        stores = self.parse_store_information(soup, findus_url)
        
        for store in stores:
            self.articles.append(store)
            print(f"    ✓ Store: {store['store_name']}")
        
        print(f"\nStore scraping completed! Retrieved {len(stores)} stores")
    
    def parse_brand_info(self, soup, url):
        """Parse AFURI about page - extract brand information"""
        brand_info = []
        
        all_text = soup.get_text()
        
        # Extract brand information from paragraphs and sections
        paragraphs = soup.find_all('p')
        sections = soup.find_all(['div', 'section', 'article'])
        
        brand_content_parts = []
        
        # Collect brand information
        for p in paragraphs:
            text = p.get_text().strip()
            if text and len(text) > 30:  # Filter out short text
                # Check if it's brand-related content
                if any(keyword in text for keyword in ['AFURI', '素材', 'ingredients', 'power', 'ちから', 
                                                      '阿夫利山', 'Mt. Afuri', '丹沢', 'Kanagawa']):
                    brand_content_parts.append(text)
        
        # Also check sections
        for section in sections:
            text = section.get_text().strip()
            if len(text) > 50 and any(keyword in text for keyword in ['AFURI', '素材', 'ingredients']):
                # Avoid duplicates
                if text not in brand_content_parts:
                    brand_content_parts.append(text)
        
        if brand_content_parts:
            brand_content = '\n'.join(brand_content_parts)
            
            brand_data = {
                'url': url,
                'title': 'AFURI Brand Information',
                'content': brand_content,
                'section': 'Brand Information',
                'date': '',
                'author': '',
                'tags': ['afuri'],
                'categories': []
            }
            brand_info.append(brand_data)
        
        return brand_info
    
    def scrape_brand_info(self, about_url=None):
        """Scrape AFURI about page for brand information"""
        if about_url is None:
            about_url = urljoin(self.base_url, '/about/')
        
        print(f"Starting to scrape AFURI brand information: {about_url}")
        
        about_html = self.get_page(about_url)
        if not about_html:
            print("Unable to fetch about page")
            return
        
        soup = BeautifulSoup(about_html, 'html.parser')
        
        print("\nExtracting brand information...")
        
        brand_info = self.parse_brand_info(soup, about_url)
        
        for brand in brand_info:
            self.articles.append(brand)
            print(f"    ✓ Brand info extracted")
        
        print(f"\nBrand information scraping completed! Retrieved {len(brand_info)} items")
    
    def save_data(self, filename='scraped_data.json'):
        """Save scraped data"""
        output_dir = 'data'
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.articles, f, ensure_ascii=False, indent=2)
        
        print(f"\nData saved to: {filepath}")
        return filepath
