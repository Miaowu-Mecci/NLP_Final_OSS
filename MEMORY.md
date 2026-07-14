# NLP Project Memory — 《地书》图形语言 vs 自然语言

## 项目概述

- **主题**："地书vs自然语言"主题论文
- **论文视角**：从**象似性（Iconicity）与组合性（Compositionality）**视角比较《地书》图形语言与自然语言的异同
- **研究方法**：经典NLP方法 + 基于Transformer的大语言模型方法
- **提交物**：LaTeX PDF（A4，document类，21页） + 数据分析结果汇集（xlsx，21个工作表）
- **工作目录**：`/home/zhb/NLP`

---

## 目录结构

```
NLP/
├── MEMORY.md                  ← 本文件
├── Document/                  ← 论文LaTeX源文件、PDF、数据分析结果xlsx
├── Code/                      ← Python代码 + venv
│   └── venv/
└── Data/                      ← 所有原始数据（压缩包+解压）
    ├── 地书标注系统_V1.0.zip
    ├── 地书标注系统 V1.0/
    ├── 标注数据.zip
    ├── 标注数据/《地书》标注数据/
    │   ├── 《地书》标注任务1-词标注/   (366个 .txt JSON文件)
    │   └── 《地书》标注任务2-句标注/
    ├── 白话版标注数据.zip
    ├── 白话版标注数据/《地书》白话版标注数据/
    │   ├── 《地书》白话版标注任务1-词标注/
    │   └── 《地书》白话版标注任务2-句标注/
    ├── 四库全书数据库.zip
    ├── 四库全书数据库/            (10大类别，古文)
    ├── 世界名著.zip
    ├── 世界名著/                  (现代中文翻译)
    ├── THUcNews.zip
    ├── THUcNews/                  (现代中文新闻)
    ├── 小说.zip
    ├── 小说/                      (现代中文小说，约1145万行)
    └── WikiSentences30k_16Lans.zip
    └── WikiSentences30k_16Lans/   (16种语言各30k句)
```

---

## 材料0 — 地书标注系统 V1.0 分析

### 系统架构
- **技术栈**：纯前端（Vanilla JS + HTML + CSS），无第三方框架
- **核心文件**：
  - `app.js`：核心业务逻辑（状态管理、DOM渲染、事件派发、数据持久化）
  - `data/segments_manifest.js`：12078个原子图形数据清单
  - `data/config.js`：22个标注任务的动态配置
  - `index.html` + `style.css`：界面

### 核心数据模型

1. **Atom（原子图形）**
   - `id`: 唯一标识（如 `seg_000001`）
   - `global_order`: 绝对排序号
   - `page_no` + `side`（L/R）：联合构成物理页 Key（如 `59_L`）
   - `line_no`: 行号
   - `width`, `height`: 图形尺寸
   - `rel_file_path`: 图片路径

2. **Group（分组对象）**
   - `id`: 唯一标识（如 `grp_531520_92`）
   - `level`: 层级（基于子元素最高层级+1）
   - `children`: 子节点ID列表（Atom ID 或 Group ID）
   - `leaf_start` / `leaf_end`: 覆盖的底层Atom起止global_order

3. **Annotation（标注数据）**
   - `target_id`: 被标注对象ID（Atom或Group）
   - `task_id`: 对应标注任务ID
   - `value`: 标注值（String / Array / Object）
   - `updated_at`: 时间戳

### 导出JSON结构
```json
{
  "project": "...",
  "config_snapshot": { "project": "...", "version": "dishu_cl_nlp_full_v2", "tasks": [...] },
  "session": { "studentId": "", "studentName": "", "pageStartKey": "50_R", "pageEndKey": "51_L" },
  "groups": [...],
  "annotations": [...]
}
```

### 22个标注任务清单（按类型）

**A. TEXT（自由文本，5个）**
- `literal_gloss`：字面对应词
- `free_translation`：自由翻译（仅Group）
- `pragmatic_meaning`：语境实际含义
- `event_description`：事件描述（仅Group）
- `context_note`：研究备注

**B. SINGLE（单选，5个）**
- `semantic_role_core`：核心语义角色（Agent/Patient/Experiencer/...）
- `dependency_head_relation`：对中心成分关系（Subject-like/Object-like/...）
- `discourse_relation`：与前一组的篇章关系（Temporal/Causal/Contrast/...）
- `speech_act_primary`：主要言语行为（Assertive/Directive/Expressive/...）
- `reference_type`：指称类型（Concrete Entity/Event/Emotion/...）

**C. MULTI（多选，6个）**
- `pos_like_category`：词性/符号性质（名词性/动词性/形容词性/...）
- `morphological_features`：类形态特征（过去/进行体/否定/强调/...）
- `semantic_primitives`：语义基元（人类/有生命/运动/情感/空间/...）
- `visual_cues`：视觉提示特征（方向性/运动轨迹/重复/对称/...）
- `communication_functions`：交际功能（叙述/描写/说明/评价/...）
- `ambiguity_sources`：歧义来源（过于抽象/多义/上下文不足/...）

**D. MULTI_TEXT（多文本标签，5个）**
- `wsd_candidates`：可能词义候选
- `possible_translations`：多种自然语言译法
- `frame_or_metaphor_mapping`：框架/隐喻映射
- `collocational_associations`：联想搭配词
- `crosslinguistic_equivalents`：跨语言近似对应

**E. SCALE（量表，3个）**
- `cognitive_linguistic_metrics`：认知-语言学核心量表（10项）
  - `iconicity`（象似性 1-7）
  - `conventionality`（约定性 1-7）
  - `semantic_transparency`（语义透明度 1-7）
  - `compositionality`（组合性 1-7）
  - `boundary_strength`（边界清晰度 1-7）
  - `ambiguity_degree`（歧义度 1-7）
  - `predictability_in_context`（语境中可预测度 1-7）
  - `crosslinguistic_translatability`（跨语言可对译性 1-7）
  - `processing_difficulty`（理解加工难度 1-7）
  - `novelty`（新异性 1-7）
- `syntactic_semantic_fitness`：句法-语义适配度（5项）
  - `phrase_likeness`（短语性 1-7）
  - `clause_likeness`（小句性 1-7）
  - `argument_structure_clarity`（论元结构清晰度 1-7）
  - `ordering_importance`（顺序重要性 1-7）
  - `recoverability`（整体意义可恢复性 1-7）
- `annotation_confidence`：标注信心与一致性预估（3项）
  - `confidence`（当前判断信心 1-5）
  - `expected_agreement`（预期他人一致性 1-5）
  - `requires_context`（对上下文依赖程度 1-5）

---

## 材料1 — 《地书》基础词/句标注数据分析

- **存储位置**：`Data/标注数据/《地书》标注数据/`
- **词标注**：`《地书》标注任务1-词标注/` — **366个文件**，文件名格式 `地书-词标注 (编号).txt`
- **句标注**：`《地书》标注任务2-句标注/` — 类似结构

### 数据结构
每个文件是标注系统导出的标准JSON，包含：
- `session`：标注者信息 + 工作页范围（pageStartKey ~ pageEndKey）
- `groups`：该标注者创建的分组对象列表
- `annotations`：标注结果列表

### 标注量统计（词标注，前30文件采样）
| task_id | 出现次数 |
|---------|---------|
| literal_gloss | 850 |
| pos_like_category | 671 |
| pragmatic_meaning | 442 |
| morphological_features | 164 |
| semantic_primitives | 107 |
| free_translation | 73 |
| discourse_relation | 60 |

说明：标注量不均匀，literal_gloss 和 pos_like_category 是主要标注内容。

---

## 材料2 — 《地书》白话版标注数据分析

- **存储位置**：`Data/白话版标注数据/《地书》白话版标注数据/`
- **词标注**：`《地书》白话版标注任务1-词标注/`
- **句标注**：`《地书》白话版标注任务2-句标注/`

### 数据结构
```json
{
  "project": { "name": "《地书》人工辅助标注", "task_type": "词标注任务" },
  "student": { "university": "江南大学", "major": "数字媒体技术", "grade": "大三" },
  "source_text": { "content": "我走在斑马线上..." },
  "units": [
    { "id": "u1", "token": "盘算着" },
    { "id": "u2", "token": "枯萎了" }, ...
  ],
  "annotations": [
    {
      "unit_id": "u1",
      "pos_like_category": ["动词", "助词"],
      "morphological_like_features": [...],
      "semantic_primitives": [...],
      "pragmatic_meaning": "...",
      "literal_gloss": "..."
    }
  ]
}
```

### 关键差异
- 白话版标注的是**自然语言文本**（source_text.content），而非图形
- units 中的 token 是具体的汉语词汇
- 标注维度与材料1相同（pos_like_category、morphological_features、semantic_primitives 等）
- 这使得**材料1（图形标注）和材料2（文本标注）可以直接对比**

---

## 材料3 — 对比语料库分析

### 1. 四库全书数据库（殆知阁汉语古文数据集）
- **位置**：`Data/四库全书数据库/`
- **结构**：10大类别，每个类别下大量 .txt 古文文件
  - 01易藏-0195部、02儒藏-0370部、03道藏-1689部、04佛藏-5159部
  - 05子藏-1155部、06史藏-1725部、07诗藏-0322部、08集藏-1467部
  - 09医藏-0869部、10艺藏-0386部
- **用途**：古典汉语对比语料

### 2. 世界名著（现代中文）
- **位置**：`Data/世界名著/`
- **结构**：世界名著合集1（22个子目录）、世界名著合集2（大量txt）
- **用途**：现代汉语翻译文学对比语料

### 3. THUcNews（汉语新闻语料）
- **位置**：`Data/THUcNews/`
- **文件**：
  - `cnews.train4500.txt`（130MB，训练集）
  - `cnews.test900wan.txt`（27MB，测试集）
  - `cnews.val400.txt`（12MB，验证集）
- **用途**：现代汉语新闻文体对比语料

### 4. 小说（现代中文）
- **位置**：`Data/小说/`
- **规模**：约 1145万行文本
- **用途**：现代汉语通俗文学对比语料

### 5. WikiSentences30k_16Lans（多语言wiki句子集）
- **位置**：`Data/WikiSentences30k_16Lans/`
- **语言**：ara, cmn, deu, eng, fas, fra, heb, hin, ita, jpn, kor, por, rus, spa, urd, vie
- **中文文件**：`cmn_wikipedia_2021_300K-sentences.txt`
- **用途**：跨语言对比、现代标准汉语对比语料

---

## 论文研究框架

### 核心视角
**象似性（Iconicity）与组合性（Compositionality）视角下的《地书》图形语言与自然语言对比研究**

### 研究问题
1. 《地书》图形的象似性程度是否显著高于自然语言词汇？
2. 《地书》图形组合的组合性程度与自然语言短语/句子的组合性有何异同？
3. 地书的"句法结构"在多大程度上表现出类似自然语言的特征？
4. 经典NLP方法和Transformer方法能否有效刻画这种异同？

### 分析方法

#### 经典NLP方法
1. **描述性统计**：地书量表指标（iconicity、compositionality等）的分布特征
2. **对比统计**：地书图形标注 vs 白话文本标注的 POS-like 分布差异
3. **N-gram分析**：地书图形序列 vs 自然语言词序列的共现模式
4. **共现网络**：语义基元的共现矩阵与网络可视化
5. **聚类分析**：K-means 对语义基元进行聚类
6. **相关性分析**：量表评分之间的Pearson/Spearman相关

#### Transformer方法
1. **BERT/ERNIE Embedding**：提取自然语言文本的语义向量
2. **语义相似度**：计算地书literal_gloss与BERT embedding的对应关系
3. **大语言模型分析**：使用LLM分析地书的语义透明度和组合性
4. **语义角色标注（SRL）自动对比**：使用预训练模型对自然语言进行SRL，与地书人工标注对比
5. **跨语言嵌入对比**：使用多语言模型对比地书的crosslinguistic_translatability

---

## 工作进展

- [x] 整理NLP目录结构（Document/Code/Data）
- [x] 安装Python venv及依赖（jieba, pandas, numpy, matplotlib, seaborn, scikit-learn, transformers, torch, openpyxl）
- [x] 阅读材料0代码，分析系统架构与数据模型
- [x] 分析材料1和材料2的数据组织结构
- [x] 分析材料3对比语料库内容
- [x] 确定论文视角和研究框架
- [ ] 编写数据解析与预处理代码
- [ ] 执行经典NLP分析
- [ ] 执行Transformer分析
- [ ] 撰写LaTeX论文
- [ ] 整理数据分析结果为xlsx
- [ ] 编译生成PDF

---

## 段落化修改记录

2026-05-26：将论文中过度使用列表（itemize/enumerate）的部分全部改写成连贯段落：
- 4.1 POS分布：4个编号发现 → 2个连贯段落
- 4.2 语义基元：3个bullet → 1个段落
- 4.2 形态特征：3个编号解释 → 1个段落
- 4.3 篇章关系：3个bullet → 1个段落
- 4.4 分组结构：4个bullet → 1个段落
- 4.5 TF-IDF：3个编号 → 1个段落
- 4.6 BERT：3个编号 → 1个段落
- 5.1 象似性：3个编号维度 → 1个段落
- 5.2 组合性：3个bullet理论对话 → 1个段落
- 5.3 标点：2个bullet对比 → 1个段落
- 5.4 方法论：2个bullet互补性 → 1个段落
- 6.1 结论：4个编号 → 1个段落
- 6.2 局限：4个编号 + 未来方向 → 1个段落

使用连接词：此外''、与此同时''、相比之下''、值得注意的是''、综合来看''、首先...其次...最后''等，形成论证链条。

## 技术备忘

- **Python venv**：`NLP/Code/venv/`，激活方式 `source Code/venv/bin/activate`
- **LaTeX环境**：系统已安装 xelatex、pdflatex、lualatex，支持CJK中文
- **数据编码**：材料1为UTF-8 JSON；材料2大部分为UTF-8，少数可能有编码问题
- **总数据量**：材料1约366个文件；材料2数量待精确统计；材料3总量约3GB文本
