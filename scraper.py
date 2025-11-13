#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
5AM Ramen 网站爬虫
爬取博客文章数据
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
        """获取网页内容"""
        try:
            print(f"正在爬取: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"获取页面失败 {url}: {e}")
            return None
    
    def parse_article_list(self, html):
        """解析文章列表页面"""
        soup = BeautifulSoup(html, 'html.parser')
        article_links = []
        
        # 查找所有文章链接
        # 根据网站结构，文章可能在各种标签中
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            # 查找博客文章链接
            if '/blog/' in href or href.startswith('/blog/'):
                full_url = urljoin(self.base_url, href)
                if full_url not in article_links:
                    article_links.append(full_url)
        
        # 也查找可能的文章卡片或列表项
        for article in soup.find_all(['article', 'div'], class_=re.compile(r'article|post|blog', re.I)):
            link = article.find('a', href=True)
            if link:
                href = link.get('href', '')
                full_url = urljoin(self.base_url, href)
                if full_url not in article_links:
                    article_links.append(full_url)
        
        return article_links
    
    def parse_article_detail(self, html, url):
        """解析单篇文章详情"""
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
        
        # 提取标题
        title_tag = soup.find('h1') or soup.find('title')
        if title_tag:
            article_data['title'] = title_tag.get_text().strip()
        
        # 提取日期
        # 查找常见的日期格式
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
        
        # 提取文章内容
        # 查找主要内容区域
        content_selectors = [
            soup.find('article'),
            soup.find('div', class_=re.compile(r'content|post-content|article-content|entry', re.I)),
            soup.find('main'),
            soup.find('div', class_=re.compile(r'blog-post|post-body', re.I))
        ]
        
        content_text = []
        for selector in content_selectors:
            if selector:
                # 提取所有段落
                paragraphs = selector.find_all('p')
                for p in paragraphs:
                    text = p.get_text().strip()
                    if text and len(text) > 20:  # 过滤太短的文本
                        content_text.append(text)
                if content_text:
                    break
        
        # 如果没有找到，尝试提取所有p标签
        if not content_text:
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.get_text().strip()
                if text and len(text) > 20:
                    content_text.append(text)
        
        article_data['content'] = '\n\n'.join(content_text)
        
        # 提取作者
        author_tag = soup.find('span', class_=re.compile(r'author', re.I)) or \
                     soup.find('div', class_=re.compile(r'author', re.I))
        if author_tag:
            article_data['author'] = author_tag.get_text().strip()
        
        # 提取标签和分类
        tag_tags = soup.find_all('a', class_=re.compile(r'tag', re.I)) or \
                   soup.find_all('span', class_=re.compile(r'tag', re.I))
        for tag in tag_tags:
            tag_text = tag.get_text().strip()
            if tag_text:
                article_data['tags'].append(tag_text)
        
        return article_data
    
    def scrape_blog(self, max_pages=10):
        """爬取博客文章"""
        print("开始爬取 5AM Ramen 博客...")
        
        # 首先获取主页
        homepage_html = self.get_page(self.base_url)
        if not homepage_html:
            print("无法获取主页")
            return
        
        # 获取博客页面
        blog_url = urljoin(self.base_url, '/blog')
        blog_html = self.get_page(blog_url)
        if not blog_html:
            blog_html = homepage_html  # 如果博客页面不存在，使用主页
        
        # 解析文章列表
        article_links = self.parse_article_list(blog_html)
        
        # 也从主页解析
        homepage_links = self.parse_article_list(homepage_html)
        article_links.extend(homepage_links)
        
        # 去重
        article_links = list(set(article_links))
        
        print(f"找到 {len(article_links)} 篇文章")
        
        # 爬取每篇文章
        for i, article_url in enumerate(article_links[:max_pages], 1):
            print(f"\n[{i}/{len(article_links)}] 正在处理: {article_url}")
            
            article_html = self.get_page(article_url)
            if article_html:
                article_data = self.parse_article_detail(article_html, article_url)
                if article_data['title'] or article_data['content']:
                    self.articles.append(article_data)
                    print(f"✓ 成功提取: {article_data['title'][:50]}...")
                else:
                    print(f"⚠ 文章内容为空，跳过")
            
            # 礼貌延迟
            time.sleep(1)
        
        print(f"\n爬取完成！共获取 {len(self.articles)} 篇文章")
    
    def save_data(self, filename='scraped_data.json'):
        """保存爬取的数据"""
        output_dir = 'data'
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.articles, f, ensure_ascii=False, indent=2)
        
        print(f"\n数据已保存到: {filepath}")
        return filepath

def main():
    scraper = RamenScraper()
    scraper.scrape_blog(max_pages=50)  # 最多爬取50篇文章
    scraper.save_data()

if __name__ == '__main__':
    main()

