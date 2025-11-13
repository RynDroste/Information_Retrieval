#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看爬取结果的工具脚本
"""

import json
import os
import sys

def view_results(filename='data/scraped_data.json', show_content=False, limit=None):
    """查看爬取结果"""
    if not os.path.exists(filename):
        print(f"错误: 文件 {filename} 不存在")
        print("请先运行 scraper.py 爬取数据")
        return
    
    with open(filename, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print("=" * 80)
    print(f"📊 爬取结果统计")
    print("=" * 80)
    print(f"总文章数: {len(articles)}")
    print(f"数据文件: {filename}")
    print(f"文件大小: {os.path.getsize(filename) / 1024:.2f} KB")
    print()
    
    # 显示文章列表
    print("=" * 80)
    print("📝 文章列表")
    print("=" * 80)
    
    articles_to_show = articles[:limit] if limit else articles
    
    for i, article in enumerate(articles_to_show, 1):
        print(f"\n[{i}] {article.get('title', '无标题')}")
        print(f"    URL: {article.get('url', 'N/A')}")
        if article.get('date'):
            print(f"    日期: {article.get('date')}")
        if article.get('author'):
            print(f"    作者: {article.get('author')}")
        
        content = article.get('content', '')
        if content:
            content_preview = content[:100].replace('\n', ' ')
            print(f"    内容预览: {content_preview}...")
            if show_content:
                print(f"    完整内容:\n    {content}")
        
        if article.get('tags'):
            print(f"    标签: {', '.join(article.get('tags', []))}")
    
    if limit and len(articles) > limit:
        print(f"\n... 还有 {len(articles) - limit} 篇文章未显示")
    
    print("\n" + "=" * 80)
    print("💡 提示:")
    print("  - 使用 python3 view_results.py --content 查看完整内容")
    print("  - 使用 python3 view_results.py --limit 5 只显示前5篇")
    print("  - 数据保存在 data/scraped_data.json")
    print("=" * 80)

def main():
    show_content = '--content' in sys.argv or '-c' in sys.argv
    limit = None
    
    # 解析 limit 参数
    if '--limit' in sys.argv:
        idx = sys.argv.index('--limit')
        if idx + 1 < len(sys.argv):
            try:
                limit = int(sys.argv[idx + 1])
            except ValueError:
                print("错误: --limit 参数必须是数字")
                return
    
    view_results(show_content=show_content, limit=limit)

if __name__ == '__main__':
    main()

