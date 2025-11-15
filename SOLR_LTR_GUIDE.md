# Solr Learning to Rank (LTR) 完整指南

## 什么是 Solr LTR？

**Learning to Rank (LTR)** 是 Apache Solr 的一个插件，它使用机器学习模型来改进搜索结果的相关性排序。与传统的基于规则和权重的排序方法不同，LTR 可以通过训练数据学习最优的排序策略。

## 核心概念

### 1. **传统排序 vs 学习排序**

#### 传统方法（我们当前使用的）
```javascript
// 手动设置权重
qf: 'title^2.0 content^1.5 menu_item^2.5'
bq: 'menu_category:"Drinks"^7.0'
```
- ✅ 简单直接
- ❌ 需要人工调优
- ❌ 难以处理复杂相关性

#### LTR 方法
```xml
<!-- 使用训练好的模型自动排序 -->
<str name="rq">{!ltr model=myModel reRankDocs=200}</str>
```
- ✅ 自动学习最优排序
- ✅ 可以处理复杂模式
- ❌ 需要训练数据

### 2. **LTR 工作流程**

```
1. 收集训练数据
   ↓
2. 提取特征（Features）
   ↓
3. 训练模型
   ↓
4. 部署模型到 Solr
   ↓
5. 查询时使用模型排序
```

## 安装和配置

### 1. **安装 LTR 插件**

#### 方法一：使用 Solr 内置安装（Solr 8.0+）
```bash
# Solr 8.0+ 已内置 LTR，只需启用
```

#### 方法二：手动安装插件
```bash
# 下载 LTR JAR 文件
wget https://repo1.maven.org/maven2/org/apache/solr/solr-ltr/8.11.2/solr-ltr-8.11.2.jar

# 复制到 Solr 的 lib 目录
cp solr-ltr-8.11.2.jar $SOLR_HOME/server/solr-webapp/webapp/WEB-INF/lib/
```

### 2. **配置 solrconfig.xml**

```xml
<config>
  <!-- 启用 LTR 组件 -->
  <lib dir="${solr.install.dir:../../../..}/contrib/ltr/lib/" regex=".*\.jar" />
  <lib dir="${solr.install.dir:../../../..}/dist/" regex="solr-ltr-\d.*\.jar" />
  
  <!-- 配置 LTR 请求处理器 -->
  <requestHandler name="/select" class="solr.SearchHandler">
    <lst name="defaults">
      <str name="defType">edismax</str>
      <str name="qf">title^2.0 content^1.5 menu_item^2.5</str>
      <!-- 使用 LTR 重新排序 -->
      <str name="rq">{!ltr model=myModel reRankDocs=200}</str>
    </lst>
  </requestHandler>
</config>
```

### 3. **配置 Schema**

```xml
<schema>
  <!-- 定义特征存储 -->
  <fieldType name="features" class="solr.FeatureField" />
  
  <!-- 可选：存储特征值用于调试 -->
  <field name="features" type="features" indexed="true" stored="true" multiValued="true" />
</schema>
```

## 特征（Features）定义

### 1. **什么是特征？**

特征是用于描述文档相关性的数值，例如：
- 查询词在标题中的出现次数
- 查询词在内容中的 TF-IDF 分数
- 文档的类别匹配度
- 文档的日期新鲜度

### 2. **定义特征**

创建 `features.json` 文件：

```json
{
  "features": [
    {
      "name": "titleMatch",
      "class": "org.apache.solr.ltr.feature.SolrFeature",
      "params": {
        "q": "{!func}termfreq(title,'${query}')"
      }
    },
    {
      "name": "contentTfIdf",
      "class": "org.apache.solr.ltr.feature.SolrFeature",
      "params": {
        "q": "{!func}tf('content','${query}') * idf('content','${query}')"
      }
    },
    {
      "name": "categoryMatch",
      "class": "org.apache.solr.ltr.feature.SolrFeature",
      "params": {
        "q": "{!func}if(termfreq(menu_category,'${query}'),1,0)"
      }
    },
    {
      "name": "titleBoost",
      "class": "org.apache.solr.ltr.feature.SolrFeature",
      "params": {
        "q": "{!func}termfreq(title,'${query}')^2.0"
      }
    },
    {
      "name": "phraseMatch",
      "class": "org.apache.solr.ltr.feature.SolrFeature",
      "params": {
        "q": "{!func}phrasefreq(title,'${query}')"
      }
    }
  ]
}
```

### 3. **上传特征定义**

```bash
# 使用 Solr API 上传特征
curl -X PUT \
  'http://localhost:8983/solr/RamenProject/schema/feature-store' \
  -H 'Content-Type: application/json' \
  -d @features.json
```

## 训练数据准备

### 1. **训练数据格式**

LTR 需要训练数据，格式为 **Learning to Rank 数据集**（通常使用 LETOR 格式）：

```
3 qid:1 1:0.5 2:0.3 3:1.0 4:0.0 5:0.2 # doc1
1 qid:1 1:0.2 2:0.1 3:0.5 4:0.8 5:0.1 # doc2
2 qid:1 1:0.8 2:0.9 3:0.0 4:0.2 5:0.5 # doc3
```

格式说明：
- **第一列**：相关性标签（0-4，4 最相关）
- **qid**：查询 ID
- **特征值**：`特征ID:特征值`
- **注释**：文档 ID

### 2. **收集训练数据**

#### 方法一：人工标注
```javascript
// 示例：收集用户点击数据
{
  query: "afuri drinks",
  clicked: "doc123",  // 用户点击的文档
  position: 1,        // 在结果中的位置
  relevance: 4        // 人工标注的相关性
}
```

#### 方法二：使用现有数据
- 用户点击日志
- 人工标注的相关性数据
- 业务规则生成的数据

### 3. **生成训练数据**

```python
# Python 脚本生成训练数据
import json

def generate_training_data(query, docs, relevance_scores):
    """生成 LTR 训练数据"""
    training_data = []
    
    for doc_id, relevance in relevance_scores.items():
        doc = docs[doc_id]
        features = extract_features(query, doc)
        
        # 格式：relevance qid:query_id feature1:value1 feature2:value2 # doc_id
        feature_str = ' '.join([f"{i+1}:{val}" for i, val in enumerate(features)])
        training_data.append(f"{relevance} qid:{query} {feature_str} # {doc_id}")
    
    return '\n'.join(training_data)

# 示例
query = "afuri drinks"
docs = {
    "doc1": {"title": "AFURI Yuzu IPA", "category": "Drinks", ...},
    "doc2": {"title": "AFURI Ramen", "category": "Ramen", ...}
}
relevance = {"doc1": 4, "doc2": 2}  # doc1 更相关

training_data = generate_training_data(query, docs, relevance)
```

## 模型训练

### 1. **支持的算法**

Solr LTR 支持多种学习算法：

#### LambdaMART（推荐）
- ✅ 最常用的算法
- ✅ 处理排序问题效果好
- ✅ 支持非线性关系

#### Random Forest
- ✅ 易于理解
- ✅ 不需要特征缩放
- ❌ 可能过拟合

#### Linear Regression
- ✅ 简单快速
- ❌ 只能学习线性关系

### 2. **使用 RankLib 训练**

```bash
# 下载 RankLib
wget https://sourceforge.net/projects/lemur/files/lemur/RankLib-2.18/RankLib-2.18.jar

# 训练 LambdaMART 模型
java -jar RankLib-2.18.jar \
  -train training_data.txt \
  -ranker 6 \  # LambdaMART
  -metric2t NDCG@10 \
  -save model.txt
```

### 3. **模型文件格式**

```json
{
  "class": "org.apache.solr.ltr.model.LinearModel",
  "name": "myModel",
  "features": [
    {"name": "titleMatch"},
    {"name": "contentTfIdf"},
    {"name": "categoryMatch"}
  ],
  "params": {
    "weights": {
      "titleMatch": 2.5,
      "contentTfIdf": 1.8,
      "categoryMatch": 3.0
    }
  }
}
```

### 4. **上传模型到 Solr**

```bash
# 上传模型
curl -X PUT \
  'http://localhost:8983/solr/RamenProject/schema/model-store' \
  -H 'Content-Type: application/json' \
  -d @model.json
```

## 在查询中使用 LTR

### 1. **基本用法**

```javascript
// 在查询中使用 LTR 重新排序
const params = new URLSearchParams({
    q: 'afuri drinks',
    defType: 'edismax',
    qf: 'title^2.0 content^1.5',
    // 使用 LTR 模型重新排序前 200 个结果
    rq: '{!ltr model=myModel reRankDocs=200}',
    rows: 10
});
```

### 2. **两阶段排序**

LTR 通常使用两阶段排序：

**阶段 1：传统排序**
- 使用 eDismax 快速获取候选文档
- 返回前 N 个结果（如 200 个）

**阶段 2：LTR 重新排序**
- 对前 N 个结果使用 LTR 模型
- 计算每个文档的特征值
- 使用模型预测相关性分数
- 重新排序并返回最终结果

### 3. **性能优化**

```javascript
// 优化：只对前 200 个结果重新排序
rq: '{!ltr model=myModel reRankDocs=200}'

// 优化：缓存特征值
rq: '{!ltr model=myModel reRankDocs=200 cache=true}'
```

## 实际应用示例

### 1. **为 AFURI 项目配置 LTR**

#### 步骤 1：定义特征

```json
{
  "features": [
    {
      "name": "titleMatch",
      "class": "org.apache.solr.ltr.feature.SolrFeature",
      "params": {
        "q": "{!func}termfreq(title,'${query}')"
      }
    },
    {
      "name": "categoryMatch",
      "class": "org.apache.solr.ltr.feature.SolrFeature",
      "params": {
        "q": "{!func}if(termfreq(menu_category,'${query}'),1,0)"
      }
    },
    {
      "name": "brandMatch",
      "class": "org.apache.solr.ltr.feature.SolrFeature",
      "params": {
        "q": "{!func}if(termfreq(section,'Brand Information'),1,0)"
      }
    },
    {
      "name": "storeMatch",
      "class": "org.apache.solr.ltr.feature.SolrFeature",
      "params": {
        "q": "{!func}if(termfreq(section,'Store Information'),1,0)"
      }
    },
    {
      "name": "phraseMatch",
      "class": "org.apache.solr.ltr.feature.SolrFeature",
      "params": {
        "q": "{!func}phrasefreq(title,'${query}')"
      }
    }
  ]
}
```

#### 步骤 2：收集训练数据

```python
# 基于业务规则生成训练数据
training_examples = [
    {
        "query": "afuri drinks",
        "doc_id": "doc1",
        "relevance": 4,  # 高度相关
        "features": {
            "titleMatch": 1.0,
            "categoryMatch": 1.0,  # 是 Drinks 类别
            "brandMatch": 1.0,     # 是 AFURI 品牌
            "storeMatch": 0.0,
            "phraseMatch": 0.0
        }
    },
    {
        "query": "afuri drinks",
        "doc_id": "doc2",
        "relevance": 2,  # 中等相关
        "features": {
            "titleMatch": 0.5,
            "categoryMatch": 0.0,  # 不是 Drinks
            "brandMatch": 1.0,
            "storeMatch": 0.0,
            "phraseMatch": 0.0
        }
    }
]
```

#### 步骤 3：训练模型

```bash
# 使用 RankLib 训练
java -jar RankLib-2.18.jar \
  -train afuri_training_data.txt \
  -ranker 6 \
  -metric2t NDCG@10 \
  -save afuri_model.txt
```

#### 步骤 4：集成到前端

```javascript
// 修改 app.js 使用 LTR
async searchSolr(query) {
    const params = new URLSearchParams({
        q: query,
        defType: 'edismax',
        qf: 'title^2.0 content^1.5 menu_item^2.5',
        // 使用 LTR 模型
        rq: '{!ltr model=afuriModel reRankDocs=200}',
        rows: 1000
    });
    
    // ... 执行查询
}
```

## 优缺点分析

### ✅ 优点

1. **自动学习最优排序**
   - 不需要手动调优权重
   - 可以学习复杂的相关性模式

2. **处理复杂场景**
   - 可以处理非线性关系
   - 可以学习特征之间的交互

3. **持续改进**
   - 可以定期用新数据重新训练
   - 模型会随着数据改进

4. **可解释性**
   - 可以查看特征重要性
   - 可以分析模型决策

### ❌ 缺点

1. **需要训练数据**
   - 需要大量标注数据
   - 数据质量影响模型效果

2. **配置复杂**
   - 需要定义特征
   - 需要训练模型
   - 需要部署和维护

3. **计算开销**
   - 需要计算特征值
   - 重新排序增加延迟

4. **需要专业知识**
   - 需要机器学习知识
   - 需要调优经验

## 与当前实现的对比

| 特性 | 当前实现 | Solr LTR |
|------|----------|----------|
| **配置难度** | 低 | 高 |
| **需要训练数据** | 否 | 是 |
| **灵活性** | 中 | 高 |
| **可维护性** | 高 | 中 |
| **性能** | 高 | 中（需要重新排序） |
| **学习能力** | 无 | 有 |
| **成本** | 免费 | 免费（但需要时间） |

## 何时使用 LTR？

### ✅ 适合使用 LTR 的场景

1. **有大量训练数据**
   - 用户点击日志
   - 人工标注数据
   - 历史查询数据

2. **相关性规则复杂**
   - 难以用简单规则表达
   - 需要学习特征交互

3. **需要持续优化**
   - 有数据收集机制
   - 可以定期重新训练

4. **有机器学习资源**
   - 有 ML 专业知识
   - 有时间调优模型

### ❌ 不适合使用 LTR 的场景

1. **数据量小**
   - 没有足够训练数据
   - 数据质量差

2. **规则简单**
   - 可以用简单规则解决
   - 当前实现已满足需求

3. **快速迭代**
   - 需要频繁调整规则
   - LTR 重新训练成本高

4. **资源有限**
   - 没有 ML 专业知识
   - 没有时间维护模型

## 最佳实践

### 1. **特征设计**

- ✅ 选择有区分度的特征
- ✅ 特征值应该归一化
- ✅ 避免特征冗余
- ❌ 不要使用太多特征（容易过拟合）

### 2. **训练数据**

- ✅ 数据要多样化
- ✅ 标注要一致
- ✅ 数据量要足够（至少几千条）
- ❌ 避免数据偏差

### 3. **模型选择**

- ✅ 从简单模型开始（Linear）
- ✅ 效果不好再尝试复杂模型（LambdaMART）
- ✅ 使用交叉验证评估

### 4. **性能优化**

- ✅ 限制重新排序的文档数（reRankDocs）
- ✅ 缓存特征值
- ✅ 定期评估模型效果

## 总结

**Solr LTR 是一个强大的工具**，但它不是万能的。对于您的 AFURI 项目：

### 当前阶段
- ✅ **保持当前实现**：简单、有效、易维护
- ✅ **满足需求**：已经能很好地处理组合查询

### 未来考虑 LTR 如果：
1. 积累了足够的用户行为数据
2. 发现相关性规则越来越复杂
3. 有资源投入模型训练和维护

### 建议
- **短期**：继续使用当前实现，优化规则
- **中期**：收集训练数据（用户点击、标注等）
- **长期**：如果数据充足，考虑引入 LTR

记住：**最好的工具是适合你当前需求的工具**。LTR 很强大，但当前实现已经很好地解决了问题！

