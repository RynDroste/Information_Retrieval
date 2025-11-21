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
import time
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from concurrent.futures import ThreadPoolExecutor, as_completed

class RamenScraper:
    def __init__(self, base_url="https://afuri.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.articles = []
        
    def fix_encoding(self, text):
        """Fix common encoding issues (mojibake)"""
        if not text:
            return text
        
        # Common mojibake patterns
        fixes = {
            'ï¼ˆ': '（',
            'ï¼‰': '）',
            'ï¼»': '［',
            'ï¼½': '］',
            'ã€‚': '。',
            'ã€': '、',
            'æœ¬': '本',
            'ã‚»ãƒƒãƒˆ': 'セット',
            'åŒæ¢±': '同梱',
            'ä¸å¯': '不可',
            'å“': '品',
        }
        
        for wrong, correct in fixes.items():
            text = text.replace(wrong, correct)
        
        # Try to fix double-encoded UTF-8
        if 'ï¼' in text or ('ã' in text and len([c for c in text if ord(c) > 127]) > len(text) * 0.1):
            try:
                # Try latin-1 -> utf-8 conversion
                fixed = text.encode('latin-1', errors='ignore').decode('utf-8', errors='ignore')
                # Check if fix improved the text (fewer mojibake characters)
                if 'ï¼' not in fixed and 'ã' not in fixed[:100]:
                    return fixed
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
        
        return text
    
    def get_page(self, url, delay=0.6):
        """Fetch webpage content"""
        try:
            print(f"Scraping: {url}")
            time.sleep(delay)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Try multiple encoding strategies
            text = None
            encodings_to_try = ['utf-8', response.apparent_encoding, 'utf-8-sig', 'latin-1']
            
            for encoding in encodings_to_try:
                if encoding:
                    try:
                        response.encoding = encoding
                        text = response.text
                        # Check if text looks correct (not too many mojibake characters)
                        if text and 'ï¼' not in text[:500] and 'ã' not in text[:500]:
                            break
                    except:
                        continue
            
            # If still have issues, try raw decode
            if not text or ('ï¼' in text[:500] or 'ã' in text[:500]):
                try:
                    text = response.content.decode('utf-8', errors='replace')
                except:
                    text = response.content.decode('utf-8', errors='ignore')
            
            # Apply encoding fixes
            if text:
                text = self.fix_encoding(text)
            
            return text
        except requests.RequestException as e:
            print(f"Failed to fetch page {url}: {e}")
            return None
        except Exception as e:
            print(f"Encoding error for {url}: {e}")
            # Fallback: return raw text with UTF-8
            try:
                return response.content.decode('utf-8', errors='replace')
            except:
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
                        
                        # Extract introduction from the relevant content
                        introduction = ''
                        # Use relevant_content if available, otherwise use text_after_item
                        content_to_search = relevant_content if relevant_content else text_after_item
                        if content_to_search:
                            lines = content_to_search.split('\n')
                            for line in reversed(lines):
                                line = line.strip()
                                # Check if line contains common introduction patterns (comma-separated, lowercase/English)
                                if ',' in line and len(line) > 20:
                                    # Check if it looks like introduction (contains common food words)
                                    introduction_keywords = ['broth', 'chashu', 'nori', 'egg', 'yuzu', 'menma', 'mizuna', 'dashi', 'shoyu', 'chicken', 'rice', 'pork', 'beef', 'seaweed', 'ginger', 'negi', 'onion']
                                    if any(keyword in line.lower() for keyword in introduction_keywords):
                                        introduction = line
                                        break
                        
                        menu_data = {
                            'url': url,
                            'title': item_name,
                            'content': content_with_afuri,
                            'section': 'Menu',
                            'menu_item': item_name,
                            'menu_category': item_category,
                            'introduction': introduction,
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
    
    def parse_product_detail(self, soup, url):
        """Parse product detail page - extract product information"""
        product_data = {
            'url': url,
            'title': '',
            'content': '',
            'section': 'Menu',
            'menu_item': '',
            'menu_category': '',
            'introduction': '',
            'price': '',
            'images': [],
            'description': '',
            'date': '',
            'author': '',
            'tags': ['afuri', 'shop'],
            'categories': []
        }
        
        title_elem = soup.find('h1') or soup.find('h2') or soup.find('title')
        if title_elem:
            title_text = title_elem.get_text().strip()
            product_data['title'] = self.fix_encoding(title_text)
            product_data['menu_item'] = product_data['title']
        
        price_elem = None
        price_selectors = [
            soup.find(class_=re.compile('price|Price|product.*price', re.I)),
            soup.find('span', class_=re.compile('price', re.I)),
            soup.find('div', class_=re.compile('price', re.I)),
            soup.find('p', class_=re.compile('price', re.I)),
            soup.find(string=re.compile(r'¥|JPY|\$|USD|EUR|GBP', re.I)),
            soup.find(attrs={'data-price': True}),
            soup.find(attrs={'itemprop': 'price'})
        ]
        
        for selector in price_selectors:
            if selector:
                price_elem = selector
                break
        
        if price_elem:
            if hasattr(price_elem, 'get_text'):
                price_text = price_elem.get_text().strip()
            elif hasattr(price_elem, 'get'):
                price_text = price_elem.get('data-price', '') or str(price_elem).strip()
            else:
                price_text = str(price_elem).strip()
            
            if price_text:
                product_data['price'] = self.fix_encoding(price_text)
        
        desc_elem = soup.find(class_=re.compile('description|Description|product.*description', re.I)) or \
                    soup.find('div', {'id': re.compile('description|Description', re.I)})
        if desc_elem:
            desc_text = desc_elem.get_text().strip()
            product_data['description'] = self.fix_encoding(desc_text)
            product_data['content'] = product_data['description']
        
        # Scrape images - get the second image
        img_elems = soup.find_all('img', src=True)
        valid_images = []
        for img in img_elems:
            img_src = img.get('src') or img.get('data-src')
            if img_src:
                if img_src.startswith('//'):
                    img_src = 'https:' + img_src
                elif img_src.startswith('/'):
                    img_src = urljoin(url, img_src)
                # Collect all valid images
                if img_src and img_src not in valid_images:
                    valid_images.append(img_src)
        
        # Get the second image if available, otherwise get the first one
        if len(valid_images) >= 2:
            product_data['images'].append(valid_images[1])
        elif len(valid_images) == 1:
            product_data['images'].append(valid_images[0])
        
        # Determine menu_category based on URL product ID prefix and title
        title_lower = product_data['title'].lower()
        desc_lower = product_data['description'].lower() if product_data['description'] else ''
        combined_text = f"{title_lower} {desc_lower}".lower()
        
        # Extract product ID from URL (e.g., ra00050002006 from /products/ra00050002006)
        product_id = None
        url_match = re.search(r'/products/([^/?]+)', url)
        if url_match:
            product_id = url_match.group(1).lower()
        
        # Check for IPA drinks first (highest priority - override URL prefix)
        is_ipa_drink = (
            'yuzu hazy ipa' in title_lower or 'ipa 350ml' in title_lower or
            ('ipa' in title_lower and ('370ml' in title_lower or '350ml' in title_lower))
        )
        
        # Check for soup products
        is_soup = (
            'ramen soup' in title_lower or 
            ('soup' in title_lower and 'ramen' in title_lower)
        )
        
        # Priority order: IPA Drinks > URL Prefix (ra/me/tu/ni/sr) > tp prefix (Soup > Drinks > Side Dishes) > Title-based
        if is_ipa_drink:
            product_data['menu_category'] = 'Drinks'
        elif product_id:
            # Classify based on URL product ID prefix
            if product_id.startswith('ra'):
                product_data['menu_category'] = 'Ramen'
            elif product_id.startswith('me'):
                product_data['menu_category'] = 'Noodles'
            elif product_id.startswith('tu'):
                product_data['menu_category'] = 'Tsukemen'
            elif product_id.startswith('ni') or product_id.startswith('sr'):
                product_data['menu_category'] = 'Side Dishes'
            elif product_id.startswith('tp'):
                # For tp prefix: check Soup > Drinks > Side Dishes
                if is_soup:
                    product_data['menu_category'] = 'Soup'
                else:
                    # Check for drink products
                    is_drink = (
                        'yuzu juice' in title_lower or 'juice' in title_lower or
                        ('drink' in title_lower or 'beer' in title_lower or 
                         'sake' in title_lower or 'whisky' in title_lower or
                         'beverage' in title_lower or 'craft beer' in title_lower or 
                         'brewing' in title_lower)
                    )
                    if is_drink:
                        product_data['menu_category'] = 'Drinks'
                    else:
                        product_data['menu_category'] = 'Side Dishes'
            else:
                # Unknown prefix, use title-based classification
                if is_soup:
                    product_data['menu_category'] = 'Soup'
                else:
                    is_drink = (
                        'yuzu juice' in title_lower or 'juice' in title_lower or
                        ('drink' in title_lower or 'beer' in title_lower or 
                         'sake' in title_lower or 'whisky' in title_lower or
                         'beverage' in title_lower or 'craft beer' in title_lower or 
                         'brewing' in title_lower)
                    )
                    if is_drink:
                        product_data['menu_category'] = 'Drinks'
                    else:
                        # Fallback to title-based classification
                        if 'tsukemen' in title_lower or (title_lower and 'tsukemen' in combined_text and 'ramen' not in title_lower):
                            product_data['menu_category'] = 'Tsukemen'
                        elif 'ramen' in title_lower or (title_lower and 'ramen' in combined_text):
                            product_data['menu_category'] = 'Ramen'
                        elif 'noodle' in combined_text and 'ramen' not in combined_text and 'tsukemen' not in combined_text:
                            product_data['menu_category'] = 'Noodles'
                        elif 'topping' in combined_text or 'side' in combined_text or 'gohan' in combined_text:
                            product_data['menu_category'] = 'Side Dishes'
                        else:
                            product_data['menu_category'] = 'Ramen'
        else:
            # No product ID found, use title-based classification
            if 'tsukemen' in title_lower or (title_lower and 'tsukemen' in combined_text and 'ramen' not in title_lower):
                product_data['menu_category'] = 'Tsukemen'
            elif 'ramen' in title_lower or (title_lower and 'ramen' in combined_text):
                product_data['menu_category'] = 'Ramen'
            elif 'noodle' in combined_text and 'ramen' not in combined_text and 'tsukemen' not in combined_text:
                product_data['menu_category'] = 'Noodles'
            elif 'topping' in combined_text or 'side' in combined_text or 'gohan' in combined_text:
                product_data['menu_category'] = 'Side Dishes'
            else:
                # Try to get category from page element as fallback
                category_elem = soup.find(class_=re.compile('category|Category|collection', re.I))
                if category_elem:
                    category_text = category_elem.get_text().strip().lower()
                    if 'ramen' in category_text:
                        product_data['menu_category'] = 'Ramen'
                    elif 'tsukemen' in category_text:
                        product_data['menu_category'] = 'Tsukemen'
                    elif 'noodle' in category_text:
                        product_data['menu_category'] = 'Noodles'
                    elif 'drink' in category_text:
                        product_data['menu_category'] = 'Drinks'
                    elif 'soup' in category_text:
                        product_data['menu_category'] = 'Soup'
                    elif 'topping' in category_text:
                        product_data['menu_category'] = 'Side Dishes'
                    else:
                        product_data['menu_category'] = 'Ramen'
                else:
                    # Default to Ramen if no category found
                    product_data['menu_category'] = 'Ramen'
        
        # Add tag based on menu_category
        category_tag_map = {
            'Ramen': 'ramen',
            'Tsukemen': 'tsukemen',
            'Noodles': 'noodles',
            'Drinks': 'drink',
            'Soup': 'soup',
            'Side Dishes': 'side-dish'
        }
        category_tag = category_tag_map.get(product_data['menu_category'], '')
        if category_tag and category_tag not in product_data['tags']:
            product_data['tags'].append(category_tag)
        
        if product_data['description']:
            introduction_match = re.search(r'ingredients?[:\s]+([^\n]+)', product_data['description'], re.I)
            if introduction_match:
                product_data['introduction'] = introduction_match.group(1).strip()
        
        return product_data
    
    def get_product_links(self, soup, base_url):
        """Extract product links from product listing page"""
        product_links = []
        
        link_elems = soup.find_all('a', href=True)
        for link in link_elems:
            href = link.get('href')
            if href and '/products/' in href:
                full_url = urljoin(base_url, href)
                if full_url not in product_links:
                    product_links.append(full_url)
        
        return product_links
    
    def get_all_product_links(self, shop_url="https://shop.afuri.com/en/collections/all"):
        """Get all product links from all pages (handles pagination)"""
        all_product_links = []
        visited_urls = set()
        page_url = shop_url
        page_num = 1
        
        while page_url:
            if page_url in visited_urls:
                break
            visited_urls.add(page_url)
            
            print(f"  Fetching page {page_num}...")
            page_html = self.get_page(page_url)
            if not page_html:
                break
            
            soup = BeautifulSoup(page_html, 'html.parser')
            product_links = self.get_product_links(soup, shop_url)
            
            new_links = [link for link in product_links if link not in all_product_links]
            all_product_links.extend(new_links)
            print(f"    Found {len(new_links)} new products (total: {len(all_product_links)})")
            
            next_page_url = None
            next_link = soup.find('a', href=True, string=re.compile(r'next|Next|>|»', re.I))
            if not next_link:
                next_link = soup.find('a', {'aria-label': re.compile(r'next|Next', re.I)})
            if not next_link:
                pagination_links = soup.find_all('a', href=True, class_=re.compile(r'pagination|page', re.I))
                for link in pagination_links:
                    href = link.get('href', '')
                    if 'page=' in href or '/page/' in href:
                        page_match = re.search(r'page[=/](\d+)', href, re.I)
                        if page_match:
                            current_page_match = re.search(r'page[=/](\d+)', page_url, re.I)
                            current_page = int(current_page_match.group(1)) if current_page_match else 1
                            next_page = int(page_match.group(1))
                            if next_page > current_page:
                                next_page_url = urljoin(shop_url, href)
                                break
            
            if not next_page_url:
                if page_num == 1:
                    if len(all_product_links) < 50:
                        next_page_url = urljoin(shop_url, f"{shop_url.rstrip('/')}/page/2")
                    else:
                        parsed = urlparse(shop_url)
                        query_params = parse_qs(parsed.query)
                        query_params['page'] = ['2']
                        new_query = urlencode(query_params, doseq=True)
                        next_page_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
                else:
                    if len(new_links) > 0:
                        next_page_num = page_num + 1
                        parsed = urlparse(shop_url)
                        query_params = parse_qs(parsed.query)
                        query_params['page'] = [str(next_page_num)]
                        new_query = urlencode(query_params, doseq=True)
                        next_page_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
                    else:
                        break
            
            if next_page_url:
                page_num_match = re.search(r'page[=/](\d+)', next_page_url, re.I)
                if page_num_match:
                    next_page_num = int(page_num_match.group(1))
                    if next_page_num <= page_num:
                        break
                    page_num = next_page_num
                else:
                    page_num += 1
                
                page_url = next_page_url
            else:
                break
        
        return all_product_links
    
    def scrape_shop_products(self, shop_url="https://shop.afuri.com/en/collections/all"):
        """Scrape AFURI online shop product details"""
        print(f"Starting to scrape AFURI shop products: {shop_url}")
        
        print("\nExtracting product links from all pages...")
        product_links = self.get_all_product_links(shop_url)
        
        if not product_links:
            print("No product links found from pagination, trying single page method...")
            shop_html = self.get_page(shop_url)
            if shop_html:
                soup = BeautifulSoup(shop_html, 'html.parser')
                product_links = self.get_product_links(soup, shop_url)
                
                if not product_links:
                    product_cards = soup.find_all(class_=re.compile('product|Product'))
                    for card in product_cards:
                        link = card.find('a', href=True)
                        if link:
                            href = link.get('href')
                            if '/products/' in href:
                                full_url = urljoin(shop_url, href)
                                if full_url not in product_links:
                                    product_links.append(full_url)
        
        print(f"\nFound {len(product_links)} total products")
        
        if len(product_links) == 0:
            print("No products found, skipping shop scraping")
            return
        
        print("\nScraping product details...")
        scraped_count = 0
        
        def scrape_single_product(product_url):
            """Scrape a single product page"""
            product_html = self.get_page(product_url, delay=0.6)
            if not product_html:
                return None
            
            product_soup = BeautifulSoup(product_html, 'html.parser')
            product_data = self.parse_product_detail(product_soup, product_url)
            
            if product_data['title']:
                return product_data
            return None
        
        # Use concurrent threads to speed up scraping
        max_workers = 3
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(scrape_single_product, url): url for url in product_links}
            
            completed = 0
            for future in as_completed(future_to_url):
                completed += 1
                product_url = future_to_url[future]
                try:
                    product_data = future.result()
                    if product_data:
                        self.articles.append(product_data)
                        scraped_count += 1
                        print(f"  [{completed}/{len(product_links)}] ✓ {product_data['title'][:50]}")
                    else:
                        print(f"  [{completed}/{len(product_links)}] ✗ Failed: {product_url[:60]}")
                except Exception as e:
                    print(f"  [{completed}/{len(product_links)}] ✗ Error: {product_url[:60]} - {e}")
        
        print(f"\nShop product scraping completed! Retrieved {scraped_count} out of {len(product_links)} products")
    
    def parse_ippudo_product_list(self, soup, url):
        """Parse Ippudo product listing page"""
        products = []
        seen_titles = set()  # Track seen titles to avoid duplicates
        
        # Find product items - look for common product container patterns
        product_containers = soup.find_all(['div', 'li', 'article'], class_=re.compile('product|item|card', re.I))
        
        # If no specific product containers found, try to find links with product patterns
        if not product_containers:
            # Look for product links
            product_links = soup.find_all('a', href=re.compile(r'/shop/|/product/|/item/', re.I))
            for link in product_links:
                href = link.get('href', '')
                if href and ('/shop/' in href or '/product/' in href):
                    # Skip navigation links
                    if any(nav in href for nav in ['/c/', '/r/', 'TOP', 'top', 'default']):
                        continue
                    # Try to extract product info from the link area
                    parent = link.find_parent(['div', 'li', 'article'])
                    if parent:
                        product_containers.append(parent)
        
        # Also try to find by text patterns (product names, prices)
        if not product_containers:
            # Look for elements containing price patterns
            price_elements = soup.find_all(string=re.compile(r'¥[\d,]+|￥[\d,]+|[\d,]+円', re.I))
            for price_elem in price_elements:
                parent = price_elem.find_parent(['div', 'li', 'article', 'tr'])
                if parent and parent not in product_containers:
                    product_containers.append(parent)
        
        for container in product_containers:
            try:
                # Extract product name/title
                title_elem = container.find(['h1', 'h2', 'h3', 'h4', 'a'], class_=re.compile('title|name|product', re.I))
                if not title_elem:
                    title_elem = container.find('a', href=re.compile(r'/shop/|/product/', re.I))
                if not title_elem:
                    # Try to find any heading or strong text
                    title_elem = container.find(['h1', 'h2', 'h3', 'h4', 'strong', 'b'])
                
                title = ''
                if title_elem:
                    title = title_elem.get_text().strip()
                    # Clean up title
                    title = re.sub(r'\s+', ' ', title)
                
                # Skip if no title found
                if not title or len(title) < 5:
                    continue
                
                # Skip navigation links and non-product items
                skip_keywords = ['TOPへ', 'TOP', 'top', '商品カテゴリー', '価格から選ぶ', '用途で選ぶ', 
                                '商品検索', 'ログイン', 'お気に入り', 'カート', 'ホーム', '新規会員登録',
                                'お買い物ガイド', 'よくある質問', 'お問い合わせ', '一風堂', '渡辺製麺', '因幡うどん',
                                'FEATURES', 'RANKING', 'NEW ARRIVALS', 'NEWS', 'Recipe Collection']
                if any(keyword in title for keyword in skip_keywords):
                    continue
                
                # Skip if already seen
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                
                # Extract price
                price = ''
                price_elem = container.find(string=re.compile(r'¥[\d,]+|￥[\d,]+|[\d,]+円', re.I))
                if price_elem:
                    price_text = price_elem.strip()
                    # Extract price pattern
                    price_match = re.search(r'[¥￥]?([\d,]+)', price_text)
                    if price_match:
                        price = price_match.group(1).replace(',', '')
                
                # Extract description
                desc = ''
                desc_elem = container.find(['p', 'div'], class_=re.compile('desc|description|summary', re.I))
                if desc_elem:
                    desc = desc_elem.get_text().strip()
                else:
                    # Try to get all text and use as description
                    all_text = container.get_text()
                    lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                    # Skip title and price lines
                    desc_lines = []
                    for line in lines:
                        if line != title and not re.search(r'[¥￥]?[\d,]+', line):
                            if len(line) > 10:  # Only meaningful descriptions
                                desc_lines.append(line)
                    desc = ' '.join(desc_lines[:3])  # Take first 3 description lines
                
                # Extract product URL
                product_url = url
                link_elem = container.find('a', href=True)
                if link_elem:
                    href = link_elem.get('href')
                    if href and '/shop/' in href:
                        product_url = urljoin(url, href)
                
                # Extract image
                image_url = ''
                img_elem = container.find('img', src=True)
                if img_elem:
                    img_src = img_elem.get('src') or img_elem.get('data-src')
                    if img_src:
                        if img_src.startswith('//'):
                            image_url = 'https:' + img_src
                        elif img_src.startswith('/'):
                            image_url = urljoin(url, img_src)
                        else:
                            image_url = urljoin(url, img_src)
                
                # Determine category
                category = 'Ramen'
                title_lower = title.lower()
                if 'ビール' in title or 'beer' in title_lower or 'ale' in title_lower:
                    category = 'Drinks'
                elif 'ソース' in title or 'sauce' in title_lower or 'ドレッシング' in title or 'ダシ' in title:
                    category = 'Sauce'
                elif '丼' in title or 'don' in title_lower:
                    category = 'Side Dishes'
                elif 'セット' in title or 'set' in title_lower or 'ギフト' in title or 'gift' in title_lower:
                    category = 'Gift Set'
                elif '冷凍' in title or 'frozen' in title_lower:
                    category = 'Frozen'
                
                # Create product data
                product_data = {
                    'url': product_url,
                    'title': self.fix_encoding(title),
                    'content': self.fix_encoding(f"{title}\n{desc}"),
                    'section': 'Menu',
                    'menu_item': self.fix_encoding(title),
                    'menu_category': category,
                    'price': price,
                    'description': self.fix_encoding(desc),
                    'images': [image_url] if image_url else [],
                    'date': '',
                    'author': '',
                    'tags': ['ippudo', '一風堂'],
                    'categories': []
                }
                
                products.append(product_data)
                
            except Exception as e:
                print(f"Error parsing product container: {e}")
                continue
        
        return products
    
    def get_ippudo_product_links(self, soup, base_url):
        """Extract product detail page links from Ippudo listing page"""
        product_links = []
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            # Look for product detail links - Ippudo uses /shop/r/ for product pages
            if href and ('/shop/r/' in href or '/shop/product/' in href or '/shop/item/' in href):
                # Skip navigation and category links
                if any(skip in href for skip in ['/c/', '/default', 'TOP', 'top']):
                    continue
                full_url = urljoin(base_url, href)
                if full_url not in product_links:
                    product_links.append(full_url)
        
        return product_links
    
    def parse_ippudo_product_detail(self, soup, url):
        """Parse Ippudo product detail page"""
        product_data = {
            'url': url,
            'title': '',
            'content': '',
            'section': 'Menu',
            'menu_item': '',
            'menu_category': '',
            'price': '',
            'description': '',
            'images': [],
            'date': '',
            'author': '',
            'tags': ['ippudo', '一風堂'],
            'categories': []
        }
        
        # Extract description/content first
        desc_elem = soup.find(['p', 'div'], class_=re.compile('desc|description|summary|detail', re.I))
        if desc_elem:
            desc_text = desc_elem.get_text().strip()
            product_data['description'] = self.fix_encoding(desc_text)
            product_data['content'] = product_data['description']
        
        # Extract title
        title_elem = soup.find('h1') or soup.find('h2') or soup.find('title')
        if title_elem:
            title_text = title_elem.get_text().strip()
            product_data['title'] = self.fix_encoding(title_text)
        
        # If title is "SHOPPING GUIDE" or similar navigation text, use first line of content as title
        title_lower = product_data['title'].lower()
        if ('shopping guide' in title_lower or 'お買い物ガイド' in product_data['title'] or 
            'guide' in title_lower and 'shopping' in title_lower) and product_data.get('content'):
            # Use first non-empty line of content as title
            content_lines = [line.strip() for line in product_data['content'].split('\n') if line.strip()]
            if content_lines:
                product_data['title'] = content_lines[0]
        
        product_data['menu_item'] = product_data['title']
        
        # Extract price
        price_elem = soup.find(string=re.compile(r'¥[\d,]+|￥[\d,]+|[\d,]+円', re.I))
        if price_elem:
            price_text = price_elem.strip()
            price_match = re.search(r'[¥￥]?([\d,]+)', price_text)
            if price_match:
                product_data['price'] = price_match.group(1).replace(',', '')
        
        # Extract images
        img_elems = soup.find_all('img', src=True)
        for img in img_elems:
            img_src = img.get('src') or img.get('data-src')
            if img_src:
                if img_src.startswith('//'):
                    img_src = 'https:' + img_src
                elif img_src.startswith('/'):
                    img_src = urljoin(url, img_src)
                if img_src and img_src not in product_data['images']:
                    product_data['images'].append(img_src)
        
        # Determine category
        title_lower = product_data['title'].lower()
        if 'ビール' in product_data['title'] or 'beer' in title_lower or 'ale' in title_lower:
            product_data['menu_category'] = 'Drinks'
        elif 'ソース' in product_data['title'] or 'sauce' in title_lower or 'ドレッシング' in product_data['title'] or 'ダシ' in product_data['title']:
            product_data['menu_category'] = 'Sauce'
        elif '丼' in product_data['title'] or 'don' in title_lower:
            product_data['menu_category'] = 'Side Dishes'
        elif 'セット' in product_data['title'] or 'set' in title_lower or 'ギフト' in product_data['title'] or 'gift' in title_lower:
            product_data['menu_category'] = 'Gift Set'
        elif '冷凍' in product_data['title'] or 'frozen' in title_lower:
            product_data['menu_category'] = 'Frozen'
        else:
            product_data['menu_category'] = 'Ramen'
        
        return product_data
    
    def scrape_ippudo_products(self, ippudo_url="https://ec-ippudo.com/shop/default.aspx"):
        """Scrape Ippudo online shop products"""
        print(f"Starting to scrape Ippudo shop products: {ippudo_url}")
        
        # Get the main product listing page
        page_html = self.get_page(ippudo_url, delay=0.6)
        if not page_html:
            print("Unable to fetch Ippudo page")
            return
        
        soup = BeautifulSoup(page_html, 'html.parser')
        
        print("\nExtracting products from listing page...")
        
        # First, try to get product detail links
        product_links = self.get_ippudo_product_links(soup, ippudo_url)
        
        # Also parse products from listing page
        products = self.parse_ippudo_product_list(soup, ippudo_url)
        
        # If we found product detail links, scrape them
        if product_links:
            print(f"\nFound {len(product_links)} product detail links, scraping details...")
            
            def scrape_single_product(product_url):
                """Scrape a single product detail page"""
                product_html = self.get_page(product_url, delay=0.6)
                if not product_html:
                    return None
                
                product_soup = BeautifulSoup(product_html, 'html.parser')
                product_data = self.parse_ippudo_product_detail(product_soup, product_url)
                
                if product_data['title']:
                    return product_data
                return None
            
            # Use concurrent threads with 3 workers
            max_workers = 3
            scraped_count = 0
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_url = {executor.submit(scrape_single_product, url): url for url in product_links}
                
                completed = 0
                for future in as_completed(future_to_url):
                    completed += 1
                    product_url = future_to_url[future]
                    try:
                        product_data = future.result()
                        if product_data:
                            self.articles.append(product_data)
                            scraped_count += 1
                            print(f"  [{completed}/{len(product_links)}] ✓ {product_data['title'][:50]}")
                        else:
                            print(f"  [{completed}/{len(product_links)}] ✗ Failed: {product_url[:60]}")
                    except Exception as e:
                        print(f"  [{completed}/{len(product_links)}] ✗ Error: {product_url[:60]} - {e}")
            
            print(f"\nScraped {scraped_count} product details")
        
        # Add products from listing page parsing
        for product in products:
            if product['title']:
                # Check if already added from detail pages
                if not any(existing['url'] == product['url'] for existing in self.articles):
                    self.articles.append(product)
                    print(f"    ✓ Product: {product['title'][:50]}")
        
        print(f"\nIppudo product scraping completed! Retrieved {len([p for p in self.articles if 'ippudo' in p.get('tags', [])])} products")
    
    def parse_kagetsu_menu(self, soup, url):
        """Parse Kagetsu menu page - extract menu items from regular_menu section"""
        menu_items = []
        
        # Find the regular_menu section
        regular_menu_section = soup.find('section', class_='regular_menu')
        if not regular_menu_section:
            print(f"Warning: Could not find section with class 'regular_menu' in {url}")
            return menu_items
        
        # Find all tables within the section (side.html has multiple tables)
        # Also check for tables inside regular_menu_1 div (seasonal.html structure)
        tables = regular_menu_section.find_all('table')
        
        # If no tables found directly, check inside regular_menu_1 div
        if not tables:
            regular_menu_1 = regular_menu_section.find('div', class_='regular_menu_1')
            if regular_menu_1:
                tables = regular_menu_1.find_all('table')
                print(f"  Found {len(tables)} table(s) inside regular_menu_1 div")
        
        if not tables:
            print(f"Warning: Could not find table in regular_menu section in {url}")
            return menu_items
        
        print(f"  Found {len(tables)} table(s) to process")
        
        # Process each table
        for table in tables:
            # Find tbody
            tbody = table.find('tbody')
            if not tbody:
                tbody = table  # If no tbody, use table directly
            
            # Find all table rows
            rows = tbody.find_all('tr')
            print(f"    Processing {len(rows)} rows in table")
            
            for row in rows:
                try:
                    # Skip rows that are headers (colspan="2" or only th with no td)
                    th_colspan = row.find('th', colspan=True)
                    if th_colspan and th_colspan.get('colspan') == '2':
                        continue  # Skip header rows like "ONLY IN WINTER"
                    
                    # Find the td element containing menu information
                    # For seasonal menu, td might be in the second column
                    tds = row.find_all('td')
                    td = None
                    
                    # Try to find td with dl element (menu information)
                    for t in tds:
                        if t.find('dl'):
                            td = t
                            break
                    
                    # If no td with dl found, try first td
                    if not td and tds:
                        td = tds[0]
                    
                    if not td:
                        continue
                    
                    # Find dl element containing menu details
                    dl = td.find('dl')
                    if not dl:
                        continue
                    
                    # Extract menu name from dt
                    dt = dl.find('dt')
                    menu_name = ''
                    if dt:
                        menu_name = dt.get_text().strip()
                        # Clean up menu name (remove extra whitespace and newlines)
                        menu_name = ' '.join(menu_name.split())
                    
                    if not menu_name:
                        continue
                    
                    # Extract price from first dd
                    price = ''
                    price_dd = dl.find('dd')
                    if price_dd:
                        price_text = price_dd.get_text().strip()
                        # Extract price pattern (e.g., "Price:920yen" or "920yen")
                        price_match = re.search(r'Price:\s*([\d,]+)\s*yen|([\d,]+)\s*yen', price_text, re.I)
                        if price_match:
                            price = price_match.group(1) or price_match.group(2)
                            price = price.replace(',', '')
                    
                    # Extract description from dd with class txt_left
                    description = ''
                    desc_dd = dl.find('dd', class_='txt_left')
                    if desc_dd:
                        description = desc_dd.get_text().strip()
                        # Clean up description
                        description = ' '.join(description.split())
                    
                    # Extract images
                    images = []
                    # Image in th
                    th = row.find('th')
                    if th:
                        th_imgs = th.find_all('img', src=True)
                        for th_img in th_imgs:
                            img_src = th_img.get('src')
                            if img_src:
                                if img_src.startswith('//'):
                                    img_src = 'https:' + img_src
                                elif img_src.startswith('/'):
                                    img_src = urljoin(url, img_src)
                                elif not img_src.startswith('http'):
                                    img_src = urljoin(url, img_src)
                                if img_src not in images:
                                    images.append(img_src)
                    
                    # Images in all tds (seasonal menu has images in first td)
                    for t in row.find_all('td'):
                        td_imgs = t.find_all('img', src=True)
                        for td_img in td_imgs:
                            img_src = td_img.get('src')
                            if img_src:
                                if img_src.startswith('//'):
                                    img_src = 'https:' + img_src
                                elif img_src.startswith('/'):
                                    img_src = urljoin(url, img_src)
                                elif not img_src.startswith('http'):
                                    img_src = urljoin(url, img_src)
                                if img_src not in images:
                                    images.append(img_src)
                    
                    # Determine category based on menu name and URL
                    category = 'Ramen'
                    menu_name_lower = menu_name.lower()
                    url_lower = url.lower()
                    
                    # First, check menu name for specific patterns
                    # Check for noodles/soba first (before ramen check)
                    if 'soba' in menu_name_lower or 'niboshi chuka soba' in menu_name_lower:
                        category = 'Noodles'
                    # Check for tsukemen (before ramen check, as tsukemen is a specific type)
                    elif 'tsukemen' in menu_name_lower:
                        category = 'Tsukemen'
                    # Check for ramen (including specific ramen names like "Mara Ramen", "Pork Stamina Ramen")
                    elif 'ramen' in menu_name_lower:
                        category = 'Ramen'
                    # Check for kids menu
                    elif 'kids' in menu_name_lower or 'okosama' in menu_name_lower:
                        category = 'Kids Menu'
                    # Check for side dishes
                    elif 'side' in menu_name_lower or 'extra' in menu_name_lower or 'set' in menu_name_lower:
                        category = 'Side Dishes'
                    elif 'gyoza' in menu_name_lower or 'rice' in menu_name_lower or 'bean sprouts' in menu_name_lower:
                        category = 'Side Dishes'
                    # Then check URL if category still not determined
                    elif 'side.html' in url_lower:
                        category = 'Side Dishes'
                    elif 'seasonal.html' in url_lower:
                        # For seasonal menu, default to Ramen if not already categorized
                        category = 'Ramen'
                    
                    # Build content
                    content_parts = [menu_name]
                    if price:
                        content_parts.append(f"Price: {price}yen")
                    if description:
                        content_parts.append(description)
                    content = '\n'.join(content_parts)
                    
                    # Add Kagetsu keyword to content
                    if "kagetsu" not in content.lower() and "花月嵐" not in content:
                        content = f"Kagetsu {content}"
                    
                    menu_data = {
                        'url': url,
                        'title': menu_name,
                        'content': self.fix_encoding(content),
                        'section': 'Menu',
                        'menu_item': self.fix_encoding(menu_name),
                        'menu_category': category,
                        'price': price,
                        'description': self.fix_encoding(description) if description else '',
                        'images': images,
                        'date': '',
                        'author': '',
                        'tags': ['kagetsu', '花月嵐'],
                        'categories': []
                    }
                    
                    menu_items.append(menu_data)
                    
                except Exception as e:
                    print(f"Error parsing menu row: {e}")
                    continue
        
        return menu_items
    
    def scrape_kagetsu_menu(self):
        """Scrape Kagetsu menu pages (regular, side, and seasonal)"""
        # List of all Kagetsu menu pages to scrape
        kagetsu_urls = [
            "https://www.kagetsu.co.jp/menu/english/index.html",  # Regular menu
            "https://www.kagetsu.co.jp/menu/english/side.html",   # Side menu
            "https://www.kagetsu.co.jp/menu/english/seasonal.html"  # Seasonal menu
        ]
        
        total_items = 0
        
        for url in kagetsu_urls:
            print(f"\n{'='*60}")
            print(f"Starting to scrape Kagetsu menu page: {url}")
            print(f"{'='*60}")
            
            menu_html = self.get_page(url, delay=0.6)
            if not menu_html:
                print(f"✗ Unable to fetch Kagetsu menu page: {url}")
                continue
            
            soup = BeautifulSoup(menu_html, 'html.parser')
            
            # Debug: Check if section exists
            regular_menu_section = soup.find('section', class_='regular_menu')
            if regular_menu_section:
                print(f"✓ Found section with class 'regular_menu'")
            else:
                print(f"✗ Warning: Could not find section with class 'regular_menu'")
            
            print(f"Extracting menu items from regular_menu section...")
            
            menu_items = self.parse_kagetsu_menu(soup, url)
            
            if menu_items:
                for menu in menu_items:
                    if menu['content']:
                        self.articles.append(menu)
                        print(f"    ✓ Menu item: {menu['menu_item']} ({menu.get('menu_category', 'Unknown')})")
            else:
                print(f"    ⚠ No menu items extracted from {url}")
            
            total_items += len(menu_items)
            print(f"\nRetrieved {len(menu_items)} menu items from {url}")
        
        print(f"\nKagetsu menu scraping completed! Retrieved {total_items} total menu items")
    
    def parse_kagetsu_stores(self, soup, url, prefecture_name=''):
        """Parse Kagetsu store page - extract store information from table"""
        stores = []
        
        # Find the table containing store information
        tables = soup.find_all('table')
        store_table = None
        
        for table in tables:
            # Look for table with store information (has headers like 店舗名, 住所, TEL, etc.)
            headers = table.find_all('th')
            header_text = ' '.join([h.get_text().strip() for h in headers]).lower()
            if any(keyword in header_text for keyword in ['店舗名', '住所', 'tel', '営業時間']):
                store_table = table
                break
        
        if not store_table:
            # If no table found with headers, try the first table with multiple rows
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > 1:  # Has multiple rows (header + data)
                    store_table = table
                    break
        
        if not store_table:
            print(f"    ⚠ No store table found in {url}")
            return stores
        
        # Extract table rows
        rows = store_table.find_all('tr')
        if len(rows) < 2:
            print(f"    ⚠ Table found but no data rows in {url}")
            return stores
        
        # Process each row (skip header row)
        for i, row in enumerate(rows):
            # Skip header row
            if i == 0:
                continue
            
            try:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:  # Need at least store name, address, and phone
                    continue
                
                # Extract store name (first cell, may contain link)
                store_name_cell = cells[0]
                store_name = ''
                # Try to find link first (store name is usually in a link)
                link = store_name_cell.find('a')
                if link:
                    store_name = link.get_text().strip()
                    # Remove brackets like [青森東バイパス店]
                    store_name = re.sub(r'\[.*?\]', '', store_name).strip()
                else:
                    store_name = store_name_cell.get_text().strip()
                    # Remove brackets
                    store_name = re.sub(r'\[.*?\]', '', store_name).strip()
                
                if not store_name or len(store_name) < 3:
                    continue
                
                # Filter out non-store entries
                skip_keywords = [
                    '店舗営業時間について', 'テイクアウト対応', '営業時間について',
                    '店舗検索', '都道府県', '新店情報', 'お知らせ', '公式SNS',
                    'ホームページ', 'お問い合わせ', '店舗リスト', 'ショップリスト',
                    '店舗名', '住所', 'TEL', '営業時間', '検索結果', '検索トップ'
                ]
                
                if any(keyword in store_name for keyword in skip_keywords):
                    continue
                
                # Extract address (second cell)
                address = cells[1].get_text().strip() if len(cells) > 1 else ''
                
                # Extract phone (third cell)
                phone = cells[2].get_text().strip() if len(cells) > 2 else ''
                
                # Extract hours (fourth cell)
                hours = cells[3].get_text().strip() if len(cells) > 3 else ''
                # Clean up hours (remove notice text)
                hours = re.sub(r'諸般の事情により.*', '', hours).strip()
                
                # Extract takeout info (fifth cell)
                takeout = ''
                if len(cells) > 4:
                    takeout_cell = cells[4]
                    if takeout_cell.find('img', alt=re.compile('テイクアウト', re.I)) or 'テイクアウト' in takeout_cell.get_text():
                        takeout = 'テイクアウト対応'
                
                # Extract delivery info (sixth cell)
                delivery = ''
                if len(cells) > 5:
                    delivery_cell = cells[5]
                    if 'デリバリー' in delivery_cell.get_text():
                        delivery = 'デリバリー対応'
                
                # Build store content
                content_parts = [store_name]
                if address:
                    content_parts.append(f"住所: {address}")
                if phone:
                    content_parts.append(f"TEL: {phone}")
                if hours:
                    content_parts.append(f"営業時間: {hours}")
                if takeout:
                    content_parts.append(takeout)
                if delivery:
                    content_parts.append(delivery)
                
                store_content = '\n'.join(content_parts)
                
                if prefecture_name:
                    store_content = f"{prefecture_name} {store_content}"
                
                # Add Kagetsu keyword
                if "kagetsu" not in store_content.lower() and "花月嵐" not in store_content:
                    store_content = f"Kagetsu 花月嵐 {store_content}"
                
                store_data = {
                    'url': url,
                    'title': f'Store - {store_name}',
                    'content': self.fix_encoding(store_content),
                    'section': 'Store Information',
                    'store_name': self.fix_encoding(store_name),
                    'date': '',
                    'author': '',
                    'tags': ['kagetsu', '花月嵐'],
                    'categories': []
                }
                
                stores.append(store_data)
                
            except Exception as e:
                print(f"    Error parsing store row: {e}")
                continue
        
        return stores
    
    def scrape_kagetsu_stores(self, base_url="https://www.kg2.jp/"):
        """Scrape Kagetsu store information from all prefectures"""
        print(f"\n{'='*60}")
        print(f"Starting to scrape Kagetsu store information from: {base_url}")
        print(f"{'='*60}")
        
        # First, get the main page to extract prefecture options
        main_html = self.get_page(base_url, delay=0.6)
        if not main_html:
            print(f"✗ Unable to fetch main page: {base_url}")
            return
        
        main_soup = BeautifulSoup(main_html, 'html.parser')
        
        # Find the select element with prefecture options
        select_elem = main_soup.find('select', {'name': 'sel'}) or main_soup.find('select', class_='formParts03')
        if not select_elem:
            print("✗ Could not find prefecture select element")
            return
        
        # Extract all prefecture options
        prefecture_options = []
        options = select_elem.find_all('option')
        for option in options:
            value = option.get('value', '').strip()
            text = option.get_text().strip()
            if value and value != '' and text and text != '都道府県で絞り込む':
                prefecture_options.append({
                    'value': value,
                    'name': text
                })
        
        print(f"✓ Found {len(prefecture_options)} prefectures to scrape")
        
        total_stores = 0
        
        # Scrape stores from each prefecture
        for prefecture in prefecture_options:
            prefecture_url = urljoin(base_url, prefecture['value'])
            prefecture_name = prefecture['name']
            
            print(f"\n  → Scraping {prefecture_name}: {prefecture_url}")
            
            prefecture_html = self.get_page(prefecture_url, delay=0.6)
            if not prefecture_html:
                print(f"    ✗ Unable to fetch page: {prefecture_url}")
                continue
            
            prefecture_soup = BeautifulSoup(prefecture_html, 'html.parser')
            
            stores = self.parse_kagetsu_stores(prefecture_soup, prefecture_url, prefecture_name)
            
            if stores:
                for store in stores:
                    self.articles.append(store)
                    print(f"    ✓ Store: {store['store_name']}")
                total_stores += len(stores)
                print(f"    Retrieved {len(stores)} stores from {prefecture_name}")
            else:
                print(f"    ⚠ No stores found in {prefecture_name}")
        
        print(f"\n{'='*60}")
        print(f"Kagetsu store scraping completed! Retrieved {total_stores} total stores")
        print(f"{'='*60}")
    
    def parse_ippudo_store_detail(self, soup, url, prefecture_name=''):
        """Parse a single Ippudo store detail page"""
        try:
            # Extract store name
            store_name = ''
            
            # Try multiple methods to find store name
            name_selectors = [
                soup.find('h1'),
                soup.find('h2'),
                soup.find(['h1', 'h2'], class_=re.compile('title|name|brand', re.I)),
                soup.find('span', class_=re.compile('LocationName|brand|name', re.I)),
                soup.find('div', class_=re.compile('store.*name|location.*name', re.I))
            ]
            
            for selector in name_selectors:
                if selector:
                    text = selector.get_text().strip()
                    if text and ('一風堂' in text or 'ippudo' in text.lower() or len(text) > 3):
                        store_name = text
                        break
            
            if not store_name:
                # Try to extract from page title
                title = soup.find('title')
                if title:
                    title_text = title.get_text().strip()
                    if '一風堂' in title_text or 'ippudo' in title_text.lower():
                        store_name = title_text.split('|')[0].split('-')[0].strip()
            
            if not store_name:
                return None
            
            # Extract address
            address = ''
            address_heading = soup.find(['h2', 'h3', 'h4'], string=re.compile(r'Address|住所', re.I))
            if address_heading:
                address_elem = address_heading.find_next(['div', 'p', 'address'])
                if address_elem:
                    address = address_elem.get_text().strip()
                    address = ' '.join(address.split())
            
            if not address:
                address_elem = soup.find('address', class_=re.compile('address', re.I))
                if address_elem:
                    address = address_elem.get_text().strip()
                    address = ' '.join(address.split())
            
            if not address:
                all_text = soup.get_text()
                address_match = re.search(r'Address\s*\n\s*([^\n]+(?:\n[^\n]+){0,5})', all_text, re.I)
                if address_match:
                    address = address_match.group(1).strip()
                    address = ' '.join(address.split())
                else:
                    address_match = re.search(r'住所[：:]\s*([^\n]+)', all_text)
                    if address_match:
                        address = address_match.group(1).strip()
            
            # Extract phone
            phone = ''
            phone_heading = soup.find(['h2', 'h3', 'h4', 'strong', 'b'], string=re.compile(r'TEL|Phone|電話', re.I))
            if phone_heading:
                phone_text = phone_heading.get_text()
                phone_match = re.search(r'TEL[：:]\s*([^\n]+)', phone_text, re.I)
                if phone_match:
                    phone = phone_match.group(1).strip()
                else:
                    next_elem = phone_heading.find_next(['div', 'p', 'span', 'a'])
                    if next_elem:
                        phone = next_elem.get_text().strip()
            
            if not phone:
                phone_elem = soup.find(['a', 'div', 'span'], class_=re.compile('phone|tel', re.I))
                if phone_elem:
                    phone = phone_elem.get_text().strip()
            
            if phone:
                phone_match = re.search(r'(\d{2,4}[-\(\)\s]*\d{1,4}[-\(\)\s]*\d{1,4})', phone)
                if phone_match:
                    phone = phone_match.group(1)
                    phone = re.sub(r'[^\d\-\(\)\s]', '', phone)
                else:
                    phone = re.sub(r'[^\d\-\(\)\s]', '', phone)
            
            if not phone:
                all_text = soup.get_text()
                phone_match = re.search(r'TEL[：:]\s*([^\n]+)', all_text, re.I)
                if not phone_match:
                    phone_match = re.search(r'Phone[：:]\s*([^\n]+)', all_text, re.I)
                if phone_match:
                    phone = phone_match.group(1).strip()
                    phone_num_match = re.search(r'(\d{2,4}[-\(\)\s]*\d{1,4}[-\(\)\s]*\d{1,4})', phone)
                    if phone_num_match:
                        phone = phone_num_match.group(1)
                    phone = re.sub(r'[^\d\-\(\)\s]', '', phone)
            
            # Extract hours
            hours = ''
            hours_heading = soup.find(['h2', 'h3', 'h4'], string=re.compile(r'Store Hours|営業時間', re.I))
            if hours_heading:
                hours_table = hours_heading.find_next('table')
                if hours_table:
                    rows = hours_table.find_all('tr')
                    if len(rows) > 1:
                        first_row = rows[1]
                        cells = first_row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            hours = cells[1].get_text().strip()
                else:
                    hours_elem = hours_heading.find_next(['div', 'p', 'span'])
                    if hours_elem:
                        hours = hours_elem.get_text().strip()
                        hours_match = re.search(r'(\d{1,2}:\d{2}\s*[~〜]\s*\d{1,2}:\d{2})', hours)
                        if hours_match:
                            hours = hours_match.group(1)
            
            if not hours:
                hours_elem = soup.find(['div', 'span', 'p'], class_=re.compile('hours|time|営業', re.I))
                if hours_elem:
                    hours = hours_elem.get_text().strip()
                    hours_match = re.search(r'(\d{1,2}:\d{2}\s*[~〜]\s*\d{1,2}:\d{2})', hours)
                    if hours_match:
                        hours = hours_match.group(1)
            
            if not hours:
                all_text = soup.get_text()
                hours_match = re.search(r'Store Hours[：:]\s*(\d{1,2}:\d{2}\s*[~〜]\s*\d{1,2}:\d{2})', all_text, re.I)
                if not hours_match:
                    hours_match = re.search(r'営業時間[：:]\s*([^\n]+)', all_text)
                if not hours_match:
                    hours_match = re.search(r'(\d{1,2}:\d{2}\s*[~〜]\s*\d{1,2}:\d{2})', all_text)
                if hours_match:
                    hours = hours_match.group(1).strip() if hours_match.lastindex else hours_match.group(0).strip()
            
            # Build store content
            content_parts = [store_name]
            if address:
                content_parts.append(f"住所: {address}")
            if phone:
                content_parts.append(f"TEL: {phone}")
            if hours:
                content_parts.append(f"営業時間: {hours}")
            
            store_content = '\n'.join(content_parts)
            
            if prefecture_name:
                store_content = f"{prefecture_name} {store_content}"
            
            if "ippudo" not in store_content.lower() and "一風堂" not in store_content:
                store_content = f"Ippudo 一風堂 {store_content}"
            
            store_data = {
                'url': url,
                'title': f'Store - {store_name}',
                'content': self.fix_encoding(store_content),
                'section': 'Store Information',
                'store_name': self.fix_encoding(store_name),
                'date': '',
                'author': '',
                'tags': ['ippudo', '一風堂'],
                'categories': []
            }
            
            return store_data
        except Exception as e:
            print(f"    Error parsing store detail page: {e}")
            return None
    
    def extract_directory_links(self, soup, base_url):
        """Extract directory links from Directory-listLinks"""
        links = []
        directory_list = soup.find('ul', class_='Directory-listLinks')
        if not directory_list:
            return links
        
        list_items = directory_list.find_all('li', class_='Directory-listItem')
        for item in list_items:
            link = item.find('a', class_='Directory-listLink', href=True)
            if link:
                href = link.get('href', '')
                text_elem = link.find('span', class_='Directory-listLinkText')
                text = text_elem.get_text().strip() if text_elem else link.get_text().strip()
                
                if href and text:
                    full_url = urljoin(base_url, href)
                    links.append({
                        'url': full_url,
                        'name': text
                    })
        
        return links
    
    def scrape_ippudo_stores_recursive(self, url, prefecture_name='', visited_urls=None, max_depth=5, current_depth=0):
        """Recursively scrape Ippudo stores from directory pages"""
        if visited_urls is None:
            visited_urls = set()
        
        if url in visited_urls or current_depth > max_depth:
            return []
        
        visited_urls.add(url)
        stores = []
        
        print(f"    {'  ' * current_depth}→ Scraping: {url}")
        
        html = self.get_page(url, delay=0.4)
        if not html:
            return stores
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check if this is a store detail page (URL contains /en/ followed by numbers)
        if re.search(r'/en/\d+', url):
            store_data = self.parse_ippudo_store_detail(soup, url, prefecture_name)
            if store_data:
                stores.append(store_data)
                print(f"    {'  ' * current_depth}  ✓ Store: {store_data['store_name']}")
            return stores
        
        # Otherwise, this is a directory page - extract sub-links
        directory_links = self.extract_directory_links(soup, url)
        
        # Also check if this page contains store listings (ResultList)
        store_listings = []
        result_list = soup.find('ol', class_=re.compile('ResultList', re.I))
        if result_list:
            list_items = result_list.find_all('li', class_=re.compile('ResultList-item', re.I))
            for item in list_items:
                # Extract store link from listing
                store_link = item.find('a', href=True)
                if store_link:
                    store_href = store_link.get('href', '')
                    if store_href:
                        store_url = urljoin(url, store_href)
                        # Check if it's a store detail page
                        if re.search(r'/en/\d+', store_url):
                            store_listings.append(store_url)
        
        # Also search for all links that point to store detail pages
        if not store_listings:
            all_links = soup.find_all('a', href=True)
            seen_store_urls = set()
            for link in all_links:
                href = link.get('href', '')
                if href and re.search(r'/en/\d+', href):
                    store_url = urljoin(url, href)
                    # Skip if it's already in visited_urls, directory_links, or seen
                    if store_url not in visited_urls and store_url not in seen_store_urls:
                        # Check if it's not in directory_links
                        is_in_directory = False
                        if directory_links:
                            for dir_link in directory_links:
                                if dir_link['url'] == store_url:
                                    is_in_directory = True
                                    break
                        if not is_in_directory:
                            store_listings.append(store_url)
                            seen_store_urls.add(store_url)
        
        # Remove duplicates from store_listings
        store_listings = list(dict.fromkeys(store_listings))
        
        # If we found store listings, parse them
        if store_listings:
            print(f"    {'  ' * current_depth}  Found {len(store_listings)} store listings on this page")
            for store_url in store_listings:
                if store_url not in visited_urls:
                    store_html = self.get_page(store_url, delay=0.3)
                    if store_html:
                        store_soup = BeautifulSoup(store_html, 'html.parser')
                        store_data = self.parse_ippudo_store_detail(store_soup, store_url, prefecture_name)
                        if store_data:
                            stores.append(store_data)
                            print(f"    {'  ' * current_depth}  ✓ Store: {store_data['store_name']}")
        
        # Also process directory links if they exist
        if directory_links:
            print(f"    {'  ' * current_depth}  Found {len(directory_links)} sub-links")
            for link in directory_links:
                link_url = link['url']
                link_name = link['name']
                
                # Recursively scrape sub-links
                sub_stores = self.scrape_ippudo_stores_recursive(
                    link_url, 
                    prefecture_name or link_name,
                    visited_urls,
                    max_depth,
                    current_depth + 1
                )
                stores.extend(sub_stores)
        elif not store_listings:
            # No directory links and no store listings, try to parse as store detail page
            store_data = self.parse_ippudo_store_detail(soup, url, prefecture_name)
            if store_data:
                # Check if it's actually a store (not a directory page title)
                store_name = store_data['store_name']
                if not any(keyword in store_name for keyword in ['Stores in', 'Store in', '店舗', 'Directory']):
                    stores.append(store_data)
                    print(f"    {'  ' * current_depth}  ✓ Store: {store_data['store_name']}")
        
        return stores
    
    def scrape_ippudo_stores(self, base_url="https://stores.ippudo.com/en/japan"):
        """Scrape Ippudo store information from all prefectures"""
        print(f"\n{'='*60}")
        print(f"Starting to scrape Ippudo store information from: {base_url}")
        print(f"{'='*60}")
        
        # Get the main page
        main_html = self.get_page(base_url, delay=0.6)
        if not main_html:
            print(f"✗ Unable to fetch main page: {base_url}")
            return
        
        main_soup = BeautifulSoup(main_html, 'html.parser')
        
        # Extract all prefecture links from Directory-listLinks
        prefecture_links = self.extract_directory_links(main_soup, base_url)
        
        if not prefecture_links:
            print("✗ Could not find prefecture links")
            return
        
        print(f"✓ Found {len(prefecture_links)} prefecture links")
        
        all_stores = []
        all_store_names = set()
        visited_urls = set()
        
        # Scrape stores from each prefecture
        for prefecture in prefecture_links:
            prefecture_url = prefecture['url']
            prefecture_name = prefecture['name']
            
            print(f"\n  → Scraping {prefecture_name}: {prefecture_url}")
            
            # Recursively scrape stores from this prefecture
            stores = self.scrape_ippudo_stores_recursive(
                prefecture_url,
                prefecture_name,
                visited_urls,
                max_depth=5
            )
            
            # Add stores, avoiding duplicates
            for store in stores:
                if store['store_name'] not in all_store_names:
                    self.articles.append(store)
                    all_store_names.add(store['store_name'])
                    all_stores.append(store)
            
            print(f"    Retrieved {len(stores)} stores from {prefecture_name}")
        
        print(f"\n{'='*60}")
        print(f"Ippudo store scraping completed! Retrieved {len(all_stores)} total stores")
        print(f"{'='*60}")
    
    def save_data(self, filename='scraped_data.json'):
        """Save scraped data"""
        output_dir = 'data'
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.articles, f, ensure_ascii=False, indent=2)
        
        print(f"\nData saved to: {filepath}")
        return filepath
