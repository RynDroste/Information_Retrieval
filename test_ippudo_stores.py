#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：测试一风堂店铺信息爬取功能
Test script for Ippudo store scraping functionality
"""

import sys
import os
import json
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper import RamenScraper


def test_ippudo_stores(quick_mode=False):
    """测试一风堂店铺爬取功能"""
    print("=" * 80)
    print("🧪 测试一风堂店铺信息爬取功能")
    print("=" * 80)
    print()
    
    # 创建爬虫实例
    scraper = RamenScraper()
    
    # 测试单个都道府県（可选，用于快速测试）
    test_prefecture_url = "https://stores.ippudo.com/en/japan/東京都"
    
    if quick_mode:
        print(f"📌 测试模式：仅爬取单个都道府県")
        print(f"   测试URL: {test_prefecture_url}")
        print()
        
        # 测试递归爬取单个都道府県
        visited_urls = set()
        stores = scraper.scrape_ippudo_stores_recursive(
            test_prefecture_url,
            "東京都",
            visited_urls,
            max_depth=5
        )
        
        print(f"\n{'='*80}")
        print(f"✅ 测试完成！")
        print(f"   找到 {len(stores)} 家店铺")
        print(f"{'='*80}")
        
        # 显示前几个店铺
        if stores:
            print("\n前5家店铺信息：")
            for i, store in enumerate(stores[:5], 1):
                print(f"\n{i}. {store['store_name']}")
                print(f"   URL: {store['url']}")
                print(f"   内容预览: {store['content'][:100]}...")
    else:
        print("📌 完整测试模式：爬取所有都道府県的店铺")
        print()
        
        # 测试完整爬取
        scraper.scrape_ippudo_stores()
        
        # 统计结果
        ippudo_stores = [article for article in scraper.articles 
                        if 'ippudo' in article.get('tags', []) 
                        and article.get('section') == 'Store Information']
        
        print(f"\n{'='*80}")
        print(f"✅ 测试完成！")
        print(f"   总共找到 {len(ippudo_stores)} 家一风堂店铺")
        print(f"{'='*80}")
        
        # 显示统计信息
        if ippudo_stores:
            print("\n📊 统计信息：")
            
            # 按都道府県统计（从URL中提取）
            prefecture_count = {}
            for store in ippudo_stores:
                url = store.get('url', '')
                if '/japan/' in url:
                    # 提取都道府県名称
                    parts = url.split('/japan/')
                    if len(parts) > 1:
                        prefecture = parts[1].split('/')[0]
                        prefecture_count[prefecture] = prefecture_count.get(prefecture, 0) + 1
                else:
                    prefecture_count['其他'] = prefecture_count.get('其他', 0) + 1
            
            print(f"\n按都道府県分布：")
            for prefecture, count in sorted(prefecture_count.items(), key=lambda x: x[1], reverse=True):
                print(f"  {prefecture}: {count} 家")
            
            # 显示前10家店铺
            print(f"\n前10家店铺信息：")
            for i, store in enumerate(ippudo_stores[:10], 1):
                print(f"\n{i}. {store['store_name']}")
                print(f"   URL: {store['url']}")
                content_preview = store['content'][:150].replace('\n', ' | ')
                print(f"   内容: {content_preview}...")
    
    # 询问是否保存测试数据
    print(f"\n{'='*80}")
    save_data = input("是否保存测试数据到文件？(y/n): ").strip().lower()
    if save_data == 'y':
        output_file = 'data/test_ippudo_stores.json'
        os.makedirs('data', exist_ok=True)
        
        ippudo_stores = [article for article in scraper.articles 
                        if 'ippudo' in article.get('tags', []) 
                        and article.get('section') == 'Store Information']
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(ippudo_stores, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 测试数据已保存到: {output_file}")
        print(f"   共保存 {len(ippudo_stores)} 家店铺信息")
    
    print(f"\n{'='*80}")
    print("测试完成！")
    print(f"{'='*80}")


def test_extract_directory_links():
    """测试提取目录链接功能"""
    print("=" * 80)
    print("🧪 测试提取目录链接功能")
    print("=" * 80)
    print()
    
    scraper = RamenScraper()
    
    # 测试主页
    test_url = "https://stores.ippudo.com/en/japan"
    print(f"测试URL: {test_url}")
    print()
    
    html = scraper.get_page(test_url, delay=0.6)
    if not html:
        print("❌ 无法获取页面")
        return
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    links = scraper.extract_directory_links(soup, test_url)
    
    print(f"✅ 找到 {len(links)} 个目录链接")
    print()
    
    if links:
        print("前10个链接：")
        for i, link in enumerate(links[:10], 1):
            print(f"{i}. {link['name']}: {link['url']}")
    
    print(f"\n{'='*80}")
    print("测试完成！")
    print(f"{'='*80}")


def test_parse_store_detail():
    """测试解析店铺详情页面"""
    print("=" * 80)
    print("🧪 测试解析店铺详情页面")
    print("=" * 80)
    print()
    
    scraper = RamenScraper()
    
    # 测试一个店铺详情页面（需要替换为实际的店铺URL）
    test_url = "https://stores.ippudo.com/en/1813"  # 示例URL，可能需要替换
    print(f"测试URL: {test_url}")
    print()
    
    html = scraper.get_page(test_url, delay=0.6)
    if not html:
        print("❌ 无法获取页面")
        return
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    store_data = scraper.parse_ippudo_store_detail(soup, test_url, "测试都道府県")
    
    if store_data:
        print("✅ 成功解析店铺信息：")
        print()
        print(f"店铺名称: {store_data['store_name']}")
        print(f"URL: {store_data['url']}")
        print(f"内容:")
        print(store_data['content'])
    else:
        print("❌ 未能解析店铺信息")
    
    print(f"\n{'='*80}")
    print("测试完成！")
    print(f"{'='*80}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='测试一风堂店铺爬取功能',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 test_ippudo_stores.py                    # 完整测试
  python3 test_ippudo_stores.py --quick             # 快速测试（仅测试单个都道府県）
  python3 test_ippudo_stores.py --test-links        # 测试提取目录链接
  python3 test_ippudo_stores.py --test-detail       # 测试解析店铺详情
        """
    )
    
    parser.add_argument('--quick', action='store_true',
                       help='快速测试模式（仅测试单个都道府県）')
    parser.add_argument('--test-links', action='store_true',
                       help='仅测试提取目录链接功能')
    parser.add_argument('--test-detail', action='store_true',
                       help='仅测试解析店铺详情功能')
    
    args = parser.parse_args()
    
    try:
        if args.test_links:
            test_extract_directory_links()
        elif args.test_detail:
            test_parse_store_detail()
        elif args.quick:
            # 快速测试模式
            print("=" * 80)
            print("🧪 快速测试模式：仅测试单个都道府県")
            print("=" * 80)
            print()
            
            scraper = RamenScraper()
            test_prefecture_url = "https://stores.ippudo.com/en/japan/東京都"
            
            print(f"📌 测试URL: {test_prefecture_url}")
            print()
            
            visited_urls = set()
            stores = scraper.scrape_ippudo_stores_recursive(
                test_prefecture_url,
                "東京都",
                visited_urls,
                max_depth=5
            )
            
            print(f"\n{'='*80}")
            print(f"✅ 测试完成！")
            print(f"   找到 {len(stores)} 家店铺")
            print(f"{'='*80}")
            
            if stores:
                print("\n店铺信息：")
                for i, store in enumerate(stores, 1):
                    print(f"\n{i}. {store['store_name']}")
                    print(f"   URL: {store['url']}")
                    content_preview = store['content'][:150].replace('\n', ' | ')
                    print(f"   内容: {content_preview}...")
        else:
            test_ippudo_stores(quick_mode=False)
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    # 如果直接运行，执行完整测试
    if len(sys.argv) == 1:
        test_ippudo_stores()
    else:
        main()

