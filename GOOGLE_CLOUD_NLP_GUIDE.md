# Google Cloud Natural Language API 完整指南

## 什么是 Google Cloud NLP？

**Google Cloud Natural Language API** 是 Google 提供的自然语言处理服务，可以分析文本的语义、情感、实体、语法结构等。它可以用于增强搜索功能，特别是关键词分类和语义理解。

## 核心功能

### 1. **实体识别（Entity Recognition）**
识别文本中的实体及其类型：
- **PERSON**：人名
- **LOCATION**：地点
- **ORGANIZATION**：组织
- **CONSUMER_GOOD**：消费品（如产品、品牌）
- **WORK_OF_ART**：艺术品、作品
- 等等...

### 2. **情感分析（Sentiment Analysis）**
分析文本的情感倾向：
- **情感分数**：-1.0（负面）到 1.0（正面）
- **情感强度**：0.0（中性）到 1.0（强烈）

### 3. **语法分析（Syntax Analysis）**
分析文本的语法结构：
- 词性标注（POS tagging）
- 依存句法分析
- 词形还原

### 4. **分类（Classification）**
将文本分类到预定义的类别中

### 5. **内容分类（Content Classification）**
识别文本的主题类别

## 在搜索中的应用

### 应用场景

#### 1. **关键词类型识别**
```javascript
// 查询："afuri drinks"
// 使用 NLP API 识别：
// - "afuri" → ORGANIZATION (品牌)
// - "drinks" → CONSUMER_GOOD (产品类别)
```

#### 2. **查询意图理解**
```javascript
// 查询："find afuri ramen near me"
// 识别意图：
// - 品牌：afuri
// - 产品：ramen
// - 位置：near me
// - 意图：查找附近的店铺
```

#### 3. **同义词和实体扩展**
```javascript
// 查询："yuzu shio"
// 识别实体：
// - "yuzu" → 柚子（可以扩展为相关产品）
// - "shio" → 盐（可以扩展为盐味拉面）
```

## 安装和配置

### 1. **创建 Google Cloud 项目**

```bash
# 安装 Google Cloud SDK
# macOS
brew install google-cloud-sdk

# 初始化
gcloud init

# 创建项目
gcloud projects create afuri-search-nlp

# 设置项目
gcloud config set project afuri-search-nlp
```

### 2. **启用 Natural Language API**

```bash
# 启用 API
gcloud services enable language.googleapis.com

# 创建服务账户
gcloud iam service-accounts create nlp-service \
  --display-name="NLP Service Account"

# 授予权限
gcloud projects add-iam-policy-binding afuri-search-nlp \
  --member="serviceAccount:nlp-service@afuri-search-nlp.iam.gserviceaccount.com" \
  --role="roles/language.admin"

# 创建密钥
gcloud iam service-accounts keys create nlp-key.json \
  --iam-account=nlp-service@afuri-search-nlp.iam.gserviceaccount.com
```

### 3. **安装客户端库**

```bash
# Python
pip install google-cloud-language

# Node.js
npm install @google-cloud/language

# 或者使用 REST API（无需安装库）
```

## API 使用方法

### 1. **REST API（推荐用于前端）**

#### 实体识别

```javascript
async function analyzeEntities(text) {
    const apiKey = 'YOUR_API_KEY';
    const url = `https://language.googleapis.com/v1/documents:analyzeEntities?key=${apiKey}`;
    
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            document: {
                type: 'PLAIN_TEXT',
                content: text
            },
            encodingType: 'UTF8'
        })
    });
    
    const data = await response.json();
    return data;
}

// 使用示例
const result = await analyzeEntities('afuri drinks');
console.log(result.entities);
// 输出：
// [
//   {
//     name: "afuri",
//     type: "ORGANIZATION",
//     salience: 0.8,  // 重要性分数
//     metadata: {...}
//   },
//   {
//     name: "drinks",
//     type: "CONSUMER_GOOD",
//     salience: 0.7
//   }
// ]
```

#### 情感分析

```javascript
async function analyzeSentiment(text) {
    const apiKey = 'YOUR_API_KEY';
    const url = `https://language.googleapis.com/v1/documents:analyzeSentiment?key=${apiKey}`;
    
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            document: {
                type: 'PLAIN_TEXT',
                content: text
            },
            encodingType: 'UTF8'
        })
    });
    
    const data = await response.json();
    return data;
}
```

#### 分类

```javascript
async function classifyText(text) {
    const apiKey = 'YOUR_API_KEY';
    const url = `https://language.googleapis.com/v1/documents:classifyText?key=${apiKey}`;
    
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            document: {
                type: 'PLAIN_TEXT',
                content: text
            }
        })
    });
    
    const data = await response.json();
    return data;
}
```

### 2. **Node.js 客户端库**

```javascript
const language = require('@google-cloud/language');
const client = new language.LanguageServiceClient({
    keyFilename: 'nlp-key.json'
});

async function analyzeQuery(query) {
    const document = {
        content: query,
        type: 'PLAIN_TEXT'
    };
    
    // 实体识别
    const [entities] = await client.analyzeEntities({ document });
    
    // 情感分析
    const [sentiment] = await client.analyzeSentiment({ document });
    
    // 分类
    const [classification] = await client.classifyText({ document });
    
    return {
        entities: entities.entities,
        sentiment: sentiment.documentSentiment,
        categories: classification.categories
    };
}
```

### 3. **Python 客户端库**

```python
from google.cloud import language_v1

def analyze_query(query):
    client = language_v1.LanguageServiceClient()
    
    document = language_v1.Document(
        content=query,
        type_=language_v1.Document.Type.PLAIN_TEXT
    )
    
    # 实体识别
    entities_response = client.analyze_entities(
        request={'document': document}
    )
    
    # 情感分析
    sentiment_response = client.analyze_sentiment(
        request={'document': document}
    )
    
    return {
        'entities': entities_response.entities,
        'sentiment': sentiment_response.document_sentiment
    }
```

## 集成到当前项目

### 1. **增强搜索算法**

修改 `frontend/app.js`，使用 Google Cloud NLP 识别关键词类型：

```javascript
class EnhancedSearchWithNLP {
    constructor() {
        this.googleApiKey = 'YOUR_GOOGLE_API_KEY';
        this.cache = new Map(); // 缓存结果
    }
    
    async analyzeQueryWithNLP(query) {
        // 检查缓存
        if (this.cache.has(query)) {
            return this.cache.get(query);
        }
        
        try {
            const url = `https://language.googleapis.com/v1/documents:analyzeEntities?key=${this.googleApiKey}`;
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    document: {
                        type: 'PLAIN_TEXT',
                        content: query
                    },
                    encodingType: 'UTF8'
                })
            });
            
            const data = await response.json();
            
            // 解析实体，识别关键词类型
            const classification = this.parseEntities(data.entities);
            
            // 缓存结果
            this.cache.set(query, classification);
            
            return classification;
        } catch (error) {
            console.error('NLP API error:', error);
            // 降级到规则匹配
            return this.fallbackClassification(query);
        }
    }
    
    parseEntities(entities) {
        const classification = {
            brand: [],
            category: [],
            type: [],
            location: []
        };
        
        entities.forEach(entity => {
            const name = entity.name.toLowerCase();
            const type = entity.type;
            
            // 根据实体类型分类
            if (type === 'ORGANIZATION') {
                // 检查是否是品牌
                if (this.isBrand(name)) {
                    classification.brand.push(name);
                }
            } else if (type === 'CONSUMER_GOOD') {
                // 检查是否是产品类别
                if (this.isCategory(name)) {
                    classification.category.push(name);
                }
            } else if (type === 'LOCATION') {
                classification.location.push(name);
            }
        });
        
        return classification;
    }
    
    isBrand(name) {
        const brands = ['afuri'];
        return brands.includes(name);
    }
    
    isCategory(name) {
        const categories = ['drinks', 'ramen', 'noodles', 'tsukemen'];
        return categories.includes(name);
    }
    
    fallbackClassification(query) {
        // 降级到原有的规则匹配
        // 使用当前的 buildBoostQuery 逻辑
        return null;
    }
    
    async buildBoostQueryWithNLP(query) {
        // 使用 NLP 分析查询
        const classification = await this.analyzeQueryWithNLP(query);
        
        if (!classification) {
            // 如果 NLP 失败，使用原有逻辑
            return this.buildBoostQuery(query);
        }
        
        // 根据 NLP 结果构建 boost 查询
        const bqParts = [];
        
        // 品牌关键词
        if (classification.brand.length > 0) {
            bqParts.push('section:"Brand Information"^7.0');
            bqParts.push('section:"Store Information"^6.5');
        }
        
        // 类别关键词
        classification.category.forEach(cat => {
            const categoryMap = {
                'drinks': 'menu_category:"Drinks"',
                'ramen': 'menu_category:"Ramen"',
                'noodles': 'menu_category:"Noodles"',
                'tsukemen': 'menu_category:"Tsukemen"'
            };
            
            if (categoryMap[cat]) {
                bqParts.push(`${categoryMap[cat]}^7.0`);
            }
        });
        
        return bqParts.join(' ');
    }
}
```

### 2. **混合方案：NLP + 规则**

```javascript
class HybridSearch {
    async buildBoostQuery(query) {
        // 尝试使用 NLP
        let bq = null;
        
        try {
            const nlpResult = await this.analyzeWithNLP(query);
            if (nlpResult && nlpResult.confidence > 0.7) {
                // NLP 结果可信度高，使用 NLP
                bq = this.buildBoostFromNLP(nlpResult);
            } else {
                // NLP 结果不可靠，使用规则
                bq = this.buildBoostFromRules(query);
            }
        } catch (error) {
            // NLP 失败，降级到规则
            bq = this.buildBoostFromRules(query);
        }
        
        return bq;
    }
    
    buildBoostFromRules(query) {
        // 使用当前的 buildBoostQuery 逻辑
        // ...
    }
}
```

### 3. **后端代理（推荐）**

由于 API 密钥安全考虑，建议在后端创建代理：

```python
# backend/nlp_proxy.py
from flask import Flask, request, jsonify
from google.cloud import language_v1
import os

app = Flask(__name__)

# 使用环境变量存储密钥
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'nlp-key.json'
client = language_v1.LanguageServiceClient()

@app.route('/api/nlp/analyze', methods=['POST'])
def analyze_text():
    data = request.json
    query = data.get('query', '')
    
    document = language_v1.Document(
        content=query,
        type_=language_v1.Document.Type.PLAIN_TEXT
    )
    
    # 分析实体
    entities_response = client.analyze_entities(
        request={'document': document}
    )
    
    # 解析结果
    classification = parse_entities(entities_response.entities)
    
    return jsonify(classification)

def parse_entities(entities):
    # 解析逻辑...
    pass

if __name__ == '__main__':
    app.run(port=5000)
```

前端调用：

```javascript
async function analyzeWithNLP(query) {
    const response = await fetch('http://localhost:5000/api/nlp/analyze', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query })
    });
    
    return await response.json();
}
```

## 实体类型映射

### Google Cloud NLP 实体类型 → 我们的分类

```javascript
const entityTypeMap = {
    // 品牌相关
    'ORGANIZATION': 'brand',      // 组织 → 品牌
    'PERSON': 'brand',            // 人名（可能是品牌创始人）
    
    // 产品类别相关
    'CONSUMER_GOOD': 'category',  // 消费品 → 产品类别
    'WORK_OF_ART': 'category',    // 作品（可能是产品名称）
    
    // 类型相关
    'LOCATION': 'type',          // 地点 → 店铺类型
    'EVENT': 'type',             // 事件
    
    // 其他
    'OTHER': 'other'
};

function mapEntityToCategory(entity) {
    const type = entity.type;
    return entityTypeMap[type] || 'other';
}
```

## 成本和使用限制

### 1. **定价**

| 功能 | 免费额度 | 付费价格 |
|------|----------|----------|
| **实体识别** | 每月 5,000 次 | $1.50 / 1,000 次 |
| **情感分析** | 每月 5,000 次 | $1.50 / 1,000 次 |
| **分类** | 每月 5,000 次 | $1.50 / 1,000 次 |
| **语法分析** | 每月 5,000 次 | $1.50 / 1,000 次 |

**新用户**：Google Cloud 提供 $300 免费额度（12 个月）

### 2. **使用限制**

- **请求大小**：最大 1MB
- **文本长度**：建议 < 10,000 字符
- **速率限制**：默认 600 请求/分钟

### 3. **成本优化策略**

```javascript
class CostOptimizedNLP {
    constructor() {
        this.cache = new Map();
        this.requestCount = 0;
        this.freeLimit = 5000; // 每月免费额度
    }
    
    async analyzeWithCache(query) {
        // 1. 检查缓存
        if (this.cache.has(query)) {
            return this.cache.get(query);
        }
        
        // 2. 检查是否超过免费额度
        if (this.requestCount >= this.freeLimit) {
            // 降级到规则匹配
            return this.fallbackAnalysis(query);
        }
        
        // 3. 调用 API
        const result = await this.callNLPAPI(query);
        this.cache.set(query, result);
        this.requestCount++;
        
        return result;
    }
    
    fallbackAnalysis(query) {
        // 使用原有的规则匹配逻辑
        // ...
    }
}
```

## 优缺点分析

### ✅ 优点

1. **强大的实体识别**
   - 可以识别品牌、产品、地点等
   - 准确率高
   - 支持多种语言

2. **开箱即用**
   - 无需训练数据
   - 无需模型训练
   - API 调用简单

3. **持续更新**
   - Google 持续改进模型
   - 自动获得最新能力

4. **多语言支持**
   - 支持 100+ 种语言
   - 对中文支持良好

### ❌ 缺点

1. **成本**
   - 超出免费额度需要付费
   - 大量请求成本较高

2. **延迟**
   - API 调用有网络延迟
   - 需要缓存优化

3. **依赖外部服务**
   - 需要网络连接
   - 服务不可用时需要降级

4. **隐私考虑**
   - 查询内容发送到 Google
   - 可能涉及隐私问题

5. **定制化有限**
   - 无法针对特定领域训练
   - 可能无法识别领域特定术语

## 与当前实现的对比

| 特性 | 当前实现 | Google Cloud NLP |
|------|----------|------------------|
| **成本** | 免费 | 付费（超出免费额度） |
| **延迟** | 极低（本地） | 中等（API 调用） |
| **准确性** | 中等（规则匹配） | 高（ML 模型） |
| **定制化** | 高（完全可控） | 低（预训练模型） |
| **维护** | 需要手动更新规则 | 自动更新 |
| **隐私** | 完全本地 | 数据发送到 Google |
| **依赖** | 无外部依赖 | 需要网络和 API |

## 实际应用示例

### 示例 1：识别 "afuri drinks"

```javascript
// 查询："afuri drinks"
const result = await analyzeEntities('afuri drinks');

// NLP 识别结果：
{
    entities: [
        {
            name: "afuri",
            type: "ORGANIZATION",
            salience: 0.8,
            // → 识别为品牌
        },
        {
            name: "drinks",
            type: "CONSUMER_GOOD",
            salience: 0.7,
            // → 识别为产品类别
        }
    ]
}

// 构建 boost 查询：
// menu_category:"Drinks"^7.0 section:"Brand Information"^5.5
```

### 示例 2：识别 "find ramen store"

```javascript
// 查询："find ramen store"
const result = await analyzeEntities('find ramen store');

// NLP 识别结果：
{
    entities: [
        {
            name: "ramen",
            type: "CONSUMER_GOOD",
            salience: 0.6
        },
        {
            name: "store",
            type: "OTHER",
            salience: 0.4
        }
    ]
}

// 构建 boost 查询：
// menu_category:"Ramen"^7.0 section:"Store Information"^5.0
```

## 最佳实践

### 1. **缓存策略**

```javascript
// 缓存常见查询
const commonQueries = [
    'afuri', 'drinks', 'ramen', 'store'
];

// 预加载缓存
commonQueries.forEach(query => {
    analyzeWithNLP(query).then(result => {
        cache.set(query, result);
    });
});
```

### 2. **降级策略**

```javascript
async function analyzeQuery(query) {
    try {
        // 尝试使用 NLP
        return await analyzeWithNLP(query);
    } catch (error) {
        // 降级到规则匹配
        console.warn('NLP failed, using fallback:', error);
        return analyzeWithRules(query);
    }
}
```

### 3. **批量处理**

```javascript
// 批量分析多个查询（如果支持）
async function analyzeBatch(queries) {
    // Google Cloud NLP 支持批量分析
    // 可以减少 API 调用次数
}
```

### 4. **成本监控**

```javascript
class CostMonitor {
    constructor() {
        this.dailyRequests = 0;
        this.monthlyRequests = 0;
        this.dailyLimit = 200; // 每天限制
        this.monthlyLimit = 5000; // 每月限制
    }
    
    canMakeRequest() {
        return this.dailyRequests < this.dailyLimit &&
               this.monthlyRequests < this.monthlyLimit;
    }
    
    recordRequest() {
        this.dailyRequests++;
        this.monthlyRequests++;
    }
}
```

## 何时使用 Google Cloud NLP？

### ✅ 适合使用的场景

1. **需要高准确率**
   - 规则匹配无法满足需求
   - 需要识别复杂实体

2. **多语言支持**
   - 需要支持多种语言
   - 需要处理多语言查询

3. **快速部署**
   - 没有时间开发规则系统
   - 需要快速上线

4. **有预算**
   - 可以承担 API 成本
   - 查询量在合理范围内

### ❌ 不适合使用的场景

1. **成本敏感**
   - 查询量很大
   - 预算有限

2. **延迟敏感**
   - 需要极低延迟
   - 无法接受 API 调用延迟

3. **隐私敏感**
   - 不能将数据发送到外部
   - 需要完全本地处理

4. **领域特定**
   - 需要识别领域特定术语
   - 预训练模型无法满足

## 混合方案推荐

### 方案：NLP + 规则混合

```javascript
class HybridSearchStrategy {
    async buildBoostQuery(query) {
        // 1. 先检查缓存
        if (this.cache.has(query)) {
            return this.cache.get(query);
        }
        
        // 2. 简单查询使用规则（快速、免费）
        if (this.isSimpleQuery(query)) {
            return this.buildBoostFromRules(query);
        }
        
        // 3. 复杂查询使用 NLP（准确、付费）
        try {
            const nlpResult = await this.analyzeWithNLP(query);
            if (nlpResult.confidence > 0.7) {
                return this.buildBoostFromNLP(nlpResult);
            }
        } catch (error) {
            // NLP 失败，降级到规则
        }
        
        // 4. 降级到规则匹配
        return this.buildBoostFromRules(query);
    }
    
    isSimpleQuery(query) {
        // 简单查询：单关键词、常见组合
        const simplePatterns = [
            /^afuri$/i,
            /^drinks?$/i,
            /^ramen$/i,
            /^afuri\s+drinks?$/i
        ];
        
        return simplePatterns.some(pattern => pattern.test(query));
    }
}
```

## 总结

**Google Cloud NLP 是一个强大的工具**，但需要权衡成本和收益：

### 对于您的项目

**当前阶段**：
- ✅ **保持当前实现**：免费、快速、满足需求
- ✅ **规则系统已足够**：可以处理大部分查询

**考虑使用 NLP 如果**：
1. 发现规则系统无法处理的复杂查询
2. 需要支持多语言
3. 有预算且查询量可控
4. 可以接受 API 延迟

**推荐方案**：
- **短期**：继续使用当前实现
- **中期**：对复杂查询使用 NLP（混合方案）
- **长期**：根据实际需求决定是否全面采用

记住：**最好的工具是适合你当前需求的工具**。Google Cloud NLP 很强大，但当前实现已经很好地解决了问题！

