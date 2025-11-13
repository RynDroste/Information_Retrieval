# 🚀 快速开始指南

欢迎使用 AFURI 菜单爬取项目！本指南将帮助您快速开始使用。

## 📋 前置要求

- Python 3.7 或更高版本
- 网络连接（用于爬取网站）

## 🎯 快速开始（3步）

### 步骤 1: 安装依赖

```bash
pip3 install -r requirements.txt
```

### 步骤 2: 爬取数据

```bash
python3 scraper.py
```

这将：
- 爬取 AFURI 菜单页面
- 提取所有菜单项
- 保存到 `data/scraped_data.json`

### 步骤 3: 清理数据

```bash
python3 data_cleaner.py
```

这将：
- 清理和规范化数据
- 移除重复项
- 保存到 `data/cleaned_data.json`

## 🌐 使用前端界面

### 启动前端服务器

```bash
# 方法1: 使用提供的脚本
bash start_frontend.sh

# 方法2: 手动启动
python3 -m http.server 8000
```

然后在浏览器中打开：**http://localhost:8000/frontend/**

### 前端功能

- 🔍 **搜索菜单项**：输入关键词（如 "yuzu", "ramen", "tsukemen"）
- 🏷️ **查看分类**：每个菜单项都有彩色分类标签
- 📊 **排序**：按相关性、标题或分类排序
- 📱 **响应式设计**：支持手机和电脑

## 🔍 使用 Solr 搜索（可选）

如果您想要更强大的搜索功能，可以设置 Solr：

### 1. 安装 Solr

**macOS:**
```bash
brew install solr
```

**Linux:**
```bash
# 下载并安装 Solr
wget https://archive.apache.org/dist/solr/solr/8.11.2/solr-8.11.2.tgz
tar xzf solr-8.11.2.tgz
cd solr-8.11.2
```

### 2. 启动 Solr

```bash
solr start
```

### 3. 创建核心

```bash
solr create -c afuri_menu
```

### 4. 索引数据

```bash
python3 solr_indexer.py
```

### 5. 在前端使用 Solr 搜索

在前端界面中，选择 "Solr Search" 选项即可使用 Solr 搜索。

## 📊 查看数据

### 查看原始数据

```bash
python3 -c "import json; data = json.load(open('data/scraped_data.json')); print(f'共 {len(data)} 个菜单项')"
```

### 查看清理后的数据

```bash
python3 -c "import json; data = json.load(open('data/cleaned_data.json')); print(f'共 {len(data)} 个菜单项'); categories = {}; [categories.update({item.get('menu_category', 'Unknown'): categories.get(item.get('menu_category', 'Unknown'), 0) + 1}) for item in data]; print('分类统计:', categories)"
```

## 🎨 完整工作流程示例

```bash
# 1. 安装依赖
pip3 install -r requirements.txt

# 2. 爬取菜单数据
python3 scraper.py

# 3. 清理数据
python3 data_cleaner.py

# 4. 启动前端（新终端窗口）
python3 -m http.server 8000

# 5. 在浏览器中打开
# http://localhost:8000/frontend/
```

## 💡 常用命令

```bash
# 重新爬取数据
python3 scraper.py

# 重新清理数据
python3 data_cleaner.py

# 启动前端服务器
python3 -m http.server 8000

# 检查 Solr 状态
solr status

# 索引到 Solr
python3 solr_indexer.py
```

## ❓ 遇到问题？

### 问题：找不到模块

```bash
pip3 install -r requirements.txt
```

### 问题：无法访问网站

- 检查网络连接
- 确认 https://afuri.com/menu/ 可以访问

### 问题：前端无法加载数据

- 确认已运行 `python3 scraper.py` 和 `python3 data_cleaner.py`
- 确认 `data/cleaned_data.json` 文件存在
- 检查浏览器控制台是否有错误

### 问题：Solr 连接失败

- 确认 Solr 正在运行：`solr status`
- 确认核心已创建：`solr create -c afuri_menu`
- 查看 `solr_setup.md` 获取详细说明

## 📁 数据文件位置

- **原始数据**: `data/scraped_data.json`
- **清理后数据**: `data/cleaned_data.json`

## 🎯 下一步

- 探索前端搜索功能
- 尝试不同的搜索关键词
- 按分类浏览菜单项
- 设置 Solr 以获得更好的搜索体验

---

**祝您使用愉快！** 🍜

