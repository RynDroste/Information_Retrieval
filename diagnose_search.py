#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断搜索功能问题
检查 Solr 连接、数据索引和代理服务器状态
"""

import urllib.request
import urllib.error
import json
import sys

def check_solr_server():
    """检查 Solr 服务器是否运行"""
    print("=" * 60)
    print("1. 检查 Solr 服务器 (http://localhost:8983)")
    print("=" * 60)
    try:
        req = urllib.request.Request('http://localhost:8983/solr/admin/ping')
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('status') == 'OK':
                print("✓ Solr 服务器正在运行")
                return True
            else:
                print("✗ Solr 服务器响应异常")
                return False
    except urllib.error.URLError as e:
        print(f"✗ 无法连接到 Solr 服务器: {e}")
        print("  请确保 Solr 正在运行: solr start")
        return False
    except Exception as e:
        print(f"✗ 检查 Solr 时出错: {e}")
        return False

def check_solr_core():
    """检查 afuri_menu core 是否存在"""
    print("\n" + "=" * 60)
    print("2. 检查 Solr Core (afuri_menu)")
    print("=" * 60)
    try:
        req = urllib.request.Request('http://localhost:8983/solr/admin/cores?action=STATUS&core=afuri_menu')
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if 'status' in data and 'afuri_menu' in data['status']:
                print("✓ afuri_menu core 存在")
                return True
            else:
                print("✗ afuri_menu core 不存在")
                print("  请创建 core: solr create -c afuri_menu")
                return False
    except Exception as e:
        print(f"✗ 检查 core 时出错: {e}")
        return False

def check_solr_data():
    """检查 Solr 中是否有数据"""
    print("\n" + "=" * 60)
    print("3. 检查 Solr 中的数据")
    print("=" * 60)
    try:
        req = urllib.request.Request('http://localhost:8983/solr/afuri_menu/select?q=*:*&rows=0&wt=json')
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            num_found = data.get('response', {}).get('numFound', 0)
            if num_found > 0:
                print(f"✓ 找到 {num_found} 条数据")
                return True
            else:
                print("✗ Solr 中没有数据")
                print("  请运行索引脚本: python3 solr_indexer.py")
                return False
    except Exception as e:
        print(f"✗ 检查数据时出错: {e}")
        return False

def check_proxy_server():
    """检查代理服务器是否运行"""
    print("\n" + "=" * 60)
    print("4. 检查代理服务器 (http://localhost:8888)")
    print("=" * 60)
    try:
        req = urllib.request.Request('http://localhost:8888/solr/afuri_menu/select?q=*:*&rows=0&wt=json')
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            num_found = data.get('response', {}).get('numFound', 0)
            print(f"✓ 代理服务器正在运行，可以访问 {num_found} 条数据")
            return True
    except urllib.error.URLError as e:
        print(f"✗ 无法连接到代理服务器: {e}")
        print("  请运行代理服务器: python3 solr_proxy.py")
        print("  或使用启动脚本: ./start_frontend.sh")
        return False
    except Exception as e:
        print(f"✗ 检查代理服务器时出错: {e}")
        return False

def test_search():
    """测试搜索功能"""
    print("\n" + "=" * 60)
    print("5. 测试搜索功能")
    print("=" * 60)
    test_queries = ['*:*', 'yuzu', 'ramen']
    
    for query in test_queries:
        try:
            url = f'http://localhost:8888/solr/afuri_menu/select?q={query}&rows=5&wt=json'
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                num_found = data.get('response', {}).get('numFound', 0)
                print(f"  查询 '{query}': 找到 {num_found} 条结果")
        except Exception as e:
            print(f"  查询 '{query}': 失败 - {e}")

def main():
    print("\n🔍 搜索功能诊断工具")
    print("=" * 60)
    print()
    
    solr_ok = check_solr_server()
    core_ok = check_solr_core() if solr_ok else False
    data_ok = check_solr_data() if core_ok else False
    proxy_ok = check_proxy_server()
    
    if proxy_ok and data_ok:
        test_search()
    
    print("\n" + "=" * 60)
    print("诊断总结")
    print("=" * 60)
    
    if not solr_ok:
        print("❌ Solr 服务器未运行")
        print("   解决方案: solr start")
    elif not core_ok:
        print("❌ Solr core 不存在")
        print("   解决方案: solr create -c afuri_menu")
    elif not data_ok:
        print("❌ Solr 中没有数据")
        print("   解决方案: python3 solr_indexer.py")
    elif not proxy_ok:
        print("❌ 代理服务器未运行")
        print("   解决方案: python3 solr_proxy.py 或 ./start_frontend.sh")
    else:
        print("✓ 所有检查通过！搜索功能应该可以正常工作。")
        print("   如果仍然无法搜索，请检查浏览器控制台的错误信息。")
    
    print()

if __name__ == '__main__':
    main()

