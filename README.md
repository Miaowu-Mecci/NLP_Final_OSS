# 《地书》图形语言 vs 自然语言 —— NLP课程论文项目

本项目为江南大学人工智能与计算机学院《自然语言处理》课程论文，从**象似性（Iconicity）与组合性（Compositionality）**视角比较徐冰《地书》图形语言与自然语言的异同。

---

## 📁 项目结构

```
NLP/
├── README.md                      ← 本文件
├── MEMORY.md                      ← 项目记忆与工作日志
├── .gitignore                     ← Git忽略规则
│
├── Code/                          ← Python代码 + venv
│   ├── venv/                      ← Python虚拟环境
│   ├── dishu_analysis.py          ← 基础数据分析脚本（v1）
│   ├── dishu_analysis_v2.py       ← 全面数据分析脚本（v2，经典NLP）
│   └── bert_analysis.py           ← Transformer/BERT语义分析
│
├── Data/                          ← 原始数据（压缩包+解压）
│   ├── 地书标注系统 V1.0/          ← 材料0：标注系统源码
│   ├── 标注数据/《地书》标注数据/     ← 材料1：图形标注数据
│   │   ├── 《地书》标注任务1-词标注/
│   │   └── 《地书》标注任务2-句标注/
│   ├── 白话版标注数据/《地书》白话版标注数据/  ← 材料2
│   │   ├── 《地书》白话版标注任务1-词标注/
│   │   └── 《地书》白话版标注任务2-句标注/
│   ├── 四库全书数据库/             ← 材料3-1：古典汉语
│   ├── 世界名著/                  ← 材料3-2：现代中文翻译
│   ├── THUcNews/                  ← 材料3-3：新闻语料
│   ├── 小说/                      ← 材料3-4：通俗小说
│   ├── WikiSentences30k_16Lans/   ← 材料3-5：多语言Wiki
│   └── *.zip                      ← 原始压缩包备份
│
└── Document/                      ← 论文文档 + 数据分析结果
    ├── main.tex                   ← LaTeX论文源码（28页）
    ├── main.pdf                   ← 论文PDF（A4，document类）
    ├── 数据分析结果汇集.xlsx       ← 全部分析结果（21个工作表）
    ├── examples/                  ← 地书图形示例图片（6张）
    │   ├── ex1_work.jpg
    │   ├── ex2_smile.jpg
    │   ├── ex3_mustgo.jpg
    │   ├── ex4_rain.jpg
    │   ├── ex5_coffee.jpg
    │   └── ex6_happy.jpg
    └── *.png / *.csv              ← 分析图表与数据表
```

---

## 📊 核心发现

| 分析维度 | 关键发现 |
|---------|---------|
| **POS分布** | 标点/边界标记占32.3%，远超自然语言；动词性25.7%，名词性16.7% |
| **形态特征** | 地书有丰富的"类形态"视觉标记——进行体2,747次、现在时2,356次 |
| **篇章关系** | 时间先后43.7%、因果17.9%、并列递进15.4%——强时序性叙事 |
| **分组结构** | 平均组大小4.82±4.06，Level1占98.9%——"宽而浅"组合性 |
| **BERT相似度** | 地书Gloss组内0.770，白话0.786，跨组0.763 |
| **TF-IDF** | 地书特有词以标点符号为主，白话特有词以语法概念和叙事角色为主 |

---

## 🔧 技术栈

- **Python 3.12**：数据分析与NLP处理
- **pandas / numpy**：数据清洗与统计计算
- **scikit-learn**：TF-IDF、PCA、余弦相似度
- **transformers + torch**：BERT中文预训练模型（`bert-base-chinese`）
- **matplotlib / seaborn**：数据可视化
- **openpyxl**：Excel结果汇总
- **LaTeX (XeLaTeX)**：论文排版（xeCJK中文支持）

---

## 🚀 快速开始

### 1. 环境准备

```bash
cd /path/to/NLP/Code
source venv/bin/activate
```

Python依赖清单：
```bash
pip install pandas numpy matplotlib seaborn scikit-learn \
            transformers torch openpyxl jieba
```

### 2. 运行数据分析

```bash
# 经典NLP分析（POS分布、语义基元、形态特征、篇章关系、TF-IDF等）
python3 Code/dishu_analysis_v2.py

# BERT语义嵌入分析
python3 Code/bert_analysis.py

# 结果输出到 Document/ 目录
```

### 3. 编译论文

```bash
cd Document
xelatex -interaction=nonstopmode main.tex
xelatex -interaction=nonstopmode main.tex  # 运行两次以更新交叉引用
```

---

## 📄 论文信息

- **标题**：从象似性与组合性视角看《地书》图形语言与自然语言的异同
- **英文标题**：A Comparative Study of Iconicity and Compositionality between the "Earth Book" Graphic Language and Natural Language
- **类型**：课程论文（Document，A4）
- **页数**：28页
- **研究方法**：经典NLP + Transformer（BERT）
- **提交物**：PDF论文 + xlsx数据分析结果汇集

---

## 📚 研究问题（RQ）

1. **RQ1**：地书图形的象似性分布特征？与自然语言词汇分布有何异同？
2. **RQ2**：地书图形组合的组合性程度？是否表现出类似自然语言的层级组织？
3. **RQ3**：经典NLP与Transformer方法在刻画异同方面各有何优势？
4. **RQ4**：篇章关系分布反映了图形叙事的何种认知特征？

---

## 📝 数据来源

- **材料0**：[地书标注系统 V1.0] — 纯前端标注工具（Vanilla JS）
- **材料1**：《地书》基础词/句标注数据 — 365个词标注文件 + 342个句标注文件
- **材料2**：《地书》白话版标注数据 — 192个白话文本标注文件
- **材料3**：对比语料库
  - 四库全书数据库（古典汉语）
  - 世界名著（现代中文翻译）
  - THUcNews（新闻语料）
  - 小说（通俗文学，约1145万行）
  - WikiSentences30k_16Lans（16种语言Wiki子集）

---

## 👤 作者信息

- **学校**：江南大学
- **学院**：人工智能与计算机学院
- **专业**：数字媒体技术
- **提交日期**：2026年5月

---

## 📜 引用

如需引用本论文或数据集，请使用以下BibTeX条目：

```bibtex
@misc{dishu_nlp_final_2026,
  title={从象似性与组合性视角看《地书》图形语言与自然语言的异同},
  author={江南大学 人工智能与计算机学院},
  year={2026},
  howpublished={\url{https://github.com/Miaowu-Mecci/NLP_Final}}
}
```

---

## ⚠️ 注意事项

- 材料3中的原始数据文件较大（总计约3GB），未纳入Git版本控制
- `Data/*.zip` 为原始数据备份，解压后的目录包含完整数据
- Python venv 目录未纳入版本控制，请按依赖清单自行创建
- 论文使用 `SimSun`（宋体）作为中文正文、`SimHei`（黑体）作为标题字体

---

## 📧 联系

项目托管于 [GitHub - Miaowu-Mecci/NLP_Final](https://github.com/Miaowu-Mecci/NLP_Final.git)
