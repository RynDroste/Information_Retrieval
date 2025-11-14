# AFURI 菜单爬取与搜索系统

从 AFURI 网站爬取菜单数据，进行清理和索引，提供前端搜索界面。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 2. 运行完整流程

```bash
# 运行完整流程（爬取 -> 清理 -> 索引）
python3 run_pipeline.py

# 如果 Solr 未运行，跳过索引步骤
python3 run_pipeline.py --skip-index

# 运行并启动前端服务
python3 run_pipeline.py --start-frontend
```

### 3. 使用前端界面

```bash
# 启动前端服务器
bash start_frontend.sh
# 或
python3 -m http.server 8000
```

在浏览器中打开：**http://localhost:8000/frontend/**

## 📖 功能说明

### 数据处理流程

1. **爬取** - 从 AFURI 网站爬取菜单、店铺和品牌信息
2. **清理** - 清理和规范化数据，移除重复项
3. **索引** - 将数据索引到 Solr（可选）
4. **搜索** - 通过前端界面搜索和浏览

### 搜索模式

- **本地搜索**：直接搜索 JSON 文件，无需 Solr
- **Solr 搜索**：使用 Solr 提供更强大的搜索功能（需要安装 Solr）

## 🔧 Solr 设置（可选）

### 安装和启动

```bash
# macOS
brew install solr
solr start
solr create -c afuri_menu

# Linux
wget https://archive.apache.org/dist/solr/solr/8.11.2/solr-8.11.2.tgz
tar xzf solr-8.11.2.tgz
cd solr-8.11.2
./bin/solr start
./bin/solr create -c afuri_menu
```

### 索引数据

```bash
python3 run_pipeline.py
# 或只执行索引
python3 run_pipeline.py --skip-scrape --skip-clean
```

### Solr 的优势

- ⚡ **快速搜索** - 索引优化，毫秒级响应
- 🎯 **智能排序** - 相关性评分，最相关的结果在前
- 🔍 **复杂查询** - 支持布尔查询、短语搜索等
- 📊 **高级功能** - 分面搜索、高亮显示、统计分析

## 📁 项目结构

```
Information_Retrieval/
├── run_pipeline.py          # 主流程脚本
├── scraper.py               # 爬取模块
├── data_cleaner.py          # 清理模块
├── solr_indexer.py          # 索引模块
├── solr_proxy.py            # Solr 代理服务器
├── start_frontend.sh        # 前端启动脚本
├── frontend/                # 前端界面
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── data/                    # 数据目录
    ├── scraped_data.json    # 原始数据
    └── cleaned_data.json    # 清理后数据
```

## 🛠️ 常用命令

```bash
# 运行完整流程
python3 run_pipeline.py

# 只执行爬取和清理
python3 run_pipeline.py --skip-index

# 只执行索引
python3 run_pipeline.py --skip-scrape --skip-clean

# 检查 Solr 状态
solr status

# 查看数据统计
python3 -c "import json; data = json.load(open('data/cleaned_data.json')); print(f'共 {len(data)} 个菜单项')"
```

## ❓ 故障排除

### 问题：找不到模块
```bash
pip3 install -r requirements.txt
```

### 问题：无法访问网站
- 检查网络连接
- 确认 https://afuri.com/menu/ 可以访问

### 问题：Solr 连接失败
- 确认 Solr 正在运行：`solr status`
- 确认核心已创建：`solr create -c afuri_menu`
- 检查端口 8983 是否被占用

### 问题：前端无法加载数据
- 确认已运行 `python3 run_pipeline.py`
- 确认 `data/cleaned_data.json` 文件存在
- 检查浏览器控制台是否有错误

## 📊 数据格式

每个菜单项包含以下字段：

```json
{
  "url": "https://afuri.com/menu/",
  "title": "Menu - Yuzu Shio Ramen",
  "content": "菜单描述...",
  "section": "Menu",
  "menu_item": "Yuzu Shio Ramen",
  "menu_category": "Ramen",
  "ingredients": "chicken & dashi based broth, yuzu..."
}
```

**分类**：Ramen, Noodles, Side Dishes, Drinks, Chi-yu

## 📝 注意事项

- 数据使用 UTF-8 编码，支持日文字符
- 脚本会自动创建 `data/` 目录
- 菜单项会自动分类
- Solr 是可选的，本地搜索也可以正常工作

---

**最后更新**：2025
