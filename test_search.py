#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试搜索功能
验证修复后的查询是否能正常工作
"""

import urllib.request
import urllib.parse
import json

def test_search(query):
    """测试搜索查询"""
    # 构建查询 - 模拟前端代码的逻辑
    words = query.split()
    if words:
        word_queries = []
        for word in words:
            word_queries.append(
                f"(title:*{word}* OR content:*{word}* OR menu_item:*{word}* OR ingredients:*{word}*)"
            )
        solr_query = ' AND '.join(word_queries)
    else:
        solr_query = '*:*'
    
    # 通过代理服务器查询
    url = f'http://localhost:8888/solr/afuri_menu/select?q={urllib.parse.quote(solr_query)}&rows=10&wt=json'
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            num_found = data.get('response', {}).get('numFound', 0)
            docs = data.get('response', {}).get('docs', [])
            
            print(f"\n查询: '{query}'")
            print(f"Solr 查询: {solr_query}")
            print(f"找到 {num_found} 条结果")
            
            if docs:
                print("\n前 3 条结果:")
                for i, doc in enumerate(docs[:3], 1):
                    title = doc.get('title', ['无标题'])[0] if isinstance(doc.get('title'), list) else doc.get('title', '无标题')
                    print(f"  {i}. {title}")
            else:
                print("  没有结果")
            
            return num_found > 0
    except Exception as e:
        print(f"查询 '{query}' 失败: {e}")
        return False

def main():
    print("=" * 60)
    print("测试搜索功能")
    print("=" * 60)
    
    test_queries = ['yuzu', 'ramen', 'tsukemen', 'chashu', 'yuzu ramen']
    
    success_count = 0
    for query in test_queries:
        if test_search(query):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"测试完成: {success_count}/{len(test_queries)} 个查询成功")
    print("=" * 60)

if __name__ == '__main__':
    main()

