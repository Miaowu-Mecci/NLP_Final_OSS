#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《地书》图形语言 vs 自然语言 —— 全面数据分析 v2
视角：象似性（Iconicity）与组合性（Compositionality）
"""

import json, glob, os, sys, collections, re
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Noto Sans CJK SC', 'WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False

BASE_DIR = Path('/home/zhb/NLP')
DATA_DIR = BASE_DIR / 'Data'
OUTPUT_DIR = BASE_DIR / 'Document'
OUTPUT_DIR.mkdir(exist_ok=True)

MAT1_WORD_DIR = DATA_DIR / '标注数据/《地书》标注数据/《地书》标注任务1-词标注'
MAT1_SENT_DIR = DATA_DIR / '标注数据/《地书》标注数据/《地书》标注任务2-句标注'
MAT2_WORD_DIR = DATA_DIR / '白话版标注数据/《地书》白话版标注数据/《地书》白话版标注任务1-词标注'
MAT2_SENT_DIR = DATA_DIR / '白话版标注数据/《地书》白话版标注数据/《地书》白话版标注任务2-句标注'

# ==================== 通用解析函数 ====================

def load_json_files(path_pattern):
    """加载所有JSON文件，忽略错误"""
    files = glob.glob(path_pattern)
    valid = []
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                raw = fp.read().strip()
                if not raw: continue
                data = json.loads(raw)
            if isinstance(data, dict) and isinstance(data.get('annotations'), list):
                valid.append((f, data))
        except:
            pass
    return valid

def extract_flat_values(records, task_id):
    """从annotations记录中提取某task的flat值列表"""
    values = []
    for _, data in records:
        for ann in data.get('annotations', []):
            if ann.get('task_id') == task_id:
                v = ann.get('value')
                if isinstance(v, list):
                    values.extend([str(x) for x in v if x])
                elif v is not None and str(v).strip():
                    values.append(str(v))
    return values

def extract_records(records, task_id):
    """提取某task的所有记录为DataFrame"""
    rows = []
    for f, data in records:
        for ann in data.get('annotations', []):
            if ann.get('task_id') == task_id:
                rows.append({
                    'file': Path(f).name,
                    'target_id': ann.get('target_id'),
                    'value': ann.get('value'),
                    'updated_at': ann.get('updated_at'),
                })
    return pd.DataFrame(rows)

# ==================== 分析1: POS-like分布 ====================

def analyze_pos(records1_word, records2_word):
    print("\n[分析1] POS-like Category 分布对比")
    
    pos1 = extract_flat_values(records1_word, 'pos_like_category')
    pos2 = extract_flat_values(records2_word, 'pos_like_category')
    
    c1 = collections.Counter(pos1)
    c2 = collections.Counter(pos2)
    
    all_labels = sorted(set(c1.keys()) | set(c2.keys()))
    df = pd.DataFrame({
        'label': all_labels,
        'dishu_count': [c1.get(l, 0) for l in all_labels],
        'baihua_count': [c2.get(l, 0) for l in all_labels],
    })
    df['dishu_pct'] = df['dishu_count'] / sum(c1.values()) * 100 if sum(c1.values()) > 0 else 0
    df['baihua_pct'] = df['baihua_count'] / sum(c2.values()) * 100 if sum(c2.values()) > 0 else 0
    
    df.to_csv(OUTPUT_DIR / '01_pos_distribution.csv', index=False, encoding='utf-8-sig')
    
    fig, ax = plt.subplots(figsize=(14, 6))
    x = np.arange(len(df))
    width = 0.35
    bars1 = ax.bar(x - width/2, df['dishu_pct'], width, label='《地书》图形', color='#e74c3c', alpha=0.8)
    bars2 = ax.bar(x + width/2, df['baihua_pct'], width, label='白话文本', color='#3498db', alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(df['label'], rotation=45, ha='right', fontsize=9)
    ax.set_ylabel('Percentage (%)', fontsize=11)
    ax.set_title('POS-like Category Distribution: 《地书》图形 vs 白话文本', fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '01_pos_distribution.png', dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  已保存图表 (n1={len(pos1)}, n2={len(pos2)})")
    return df

# ==================== 分析2: 语义基元 ====================

def analyze_semantic_primitives(records1_word, records2_word):
    print("\n[分析2] Semantic Primitives 分布对比")
    
    sp1 = extract_flat_values(records1_word, 'semantic_primitives')
    sp2 = extract_flat_values(records2_word, 'semantic_primitives')
    
    c1 = collections.Counter(sp1)
    c2 = collections.Counter(sp2)
    
    all_labels = sorted(set(c1.keys()) | set(c2.keys()))
    df = pd.DataFrame({
        'primitive': all_labels,
        'dishu_count': [c1.get(l, 0) for l in all_labels],
        'baihua_count': [c2.get(l, 0) for l in all_labels],
    })
    
    df.to_csv(OUTPUT_DIR / '02_semantic_primitives.csv', index=False, encoding='utf-8-sig')
    
    fig, ax = plt.subplots(figsize=(14, 6))
    x = np.arange(len(df))
    width = 0.35
    ax.bar(x - width/2, df['dishu_count'], width, label='《地书》图形', color='#e67e22', alpha=0.8)
    ax.bar(x + width/2, df['baihua_count'], width, label='白话文本', color='#2ecc71', alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(df['primitive'], rotation=45, ha='right', fontsize=9)
    ax.set_ylabel('Count', fontsize=11)
    ax.set_title('Semantic Primitives Distribution', fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '02_semantic_primitives.png', dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  已保存图表 (n1={len(sp1)}, n2={len(sp2)})")
    return df

# ==================== 分析3: 形态特征 ====================

def analyze_morphological_features(records1_word, records1_sent, records2_word):
    print("\n[分析3] Morphological-like Features 分布对比")
    
    # 合并词标注和句标注中的形态特征
    mf1 = extract_flat_values(records1_word, 'morphological_features')
    mf1 += extract_flat_values(records1_sent, 'morphological_features')
    mf2 = extract_flat_values(records2_word, 'morphological_features')
    
    c1 = collections.Counter(mf1)
    c2 = collections.Counter(mf2)
    
    all_labels = sorted(set(c1.keys()) | set(c2.keys()))
    df = pd.DataFrame({
        'feature': all_labels,
        'dishu_count': [c1.get(l, 0) for l in all_labels],
        'baihua_count': [c2.get(l, 0) for l in all_labels],
    })
    
    df.to_csv(OUTPUT_DIR / '03_morphological_features.csv', index=False, encoding='utf-8-sig')
    
    fig, ax = plt.subplots(figsize=(14, 6))
    x = np.arange(len(df))
    width = 0.35
    ax.bar(x - width/2, df['dishu_count'], width, label='《地书》图形', color='#9b59b6', alpha=0.8)
    ax.bar(x + width/2, df['baihua_count'], width, label='白话文本', color='#1abc9c', alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(df['feature'], rotation=45, ha='right', fontsize=9)
    ax.set_ylabel('Count', fontsize=11)
    ax.set_title('Morphological-like Features Distribution', fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '03_morphological_features.png', dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  已保存图表 (n1={len(mf1)}, n2={len(mf2)})")
    return df

# ==================== 分析4: 篇章关系 ====================

def analyze_discourse(records1_sent):
    print("\n[分析4] Discourse Relation 分布（句标注）")
    
    dr = extract_flat_values(records1_sent, 'discourse_relation')
    c = collections.Counter(dr)
    
    df = pd.DataFrame(c.most_common(), columns=['relation', 'count'])
    df['percentage'] = df['count'] / df['count'].sum() * 100
    df.to_csv(OUTPUT_DIR / '04_discourse_relation.csv', index=False, encoding='utf-8-sig')
    
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = plt.cm.Spectral(np.linspace(0.1, 0.9, len(df)))
    bars = ax.barh(df['relation'], df['count'], color=colors)
    ax.set_xlabel('Count', fontsize=11)
    ax.set_title('Discourse Relation Distribution in 《地书》Sentence Annotation', fontsize=13)
    ax.invert_yaxis()
    for bar, pct in zip(bars, df['percentage']):
        ax.text(bar.get_width() + 10, bar.get_y() + bar.get_height()/2, 
                f'{pct:.1f}%', va='center', fontsize=9)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '04_discourse_relation.png', dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  已保存图表 (n={len(dr)})")
    return df

# ==================== 分析5: 语义角色 ====================

def analyze_semantic_role(records1_word, records1_sent):
    print("\n[分析5] Semantic Role 分布")
    
    sr = extract_flat_values(records1_word, 'semantic_role_core')
    sr += extract_flat_values(records1_sent, 'semantic_role_core')
    c = collections.Counter(sr)
    
    df = pd.DataFrame(c.most_common(), columns=['role', 'count'])
    df['percentage'] = df['count'] / df['count'].sum() * 100
    df.to_csv(OUTPUT_DIR / '05_semantic_role.csv', index=False, encoding='utf-8-sig')
    
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.cm.Set3(np.linspace(0, 1, len(df)))
    ax.pie(df['count'], labels=df['role'], autopct='%1.1f%%', colors=colors, startangle=90)
    ax.set_title('Core Semantic Role Distribution in 《地书》', fontsize=13)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '05_semantic_role.png', dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  已保存图表 (n={len(sr)})")
    return df

# ==================== 分析6: 字面Gloss词频与TF-IDF ====================

def analyze_gloss_tfidf(records1_word, records2_word):
    print("\n[分析6] Literal Gloss 词频与TF-IDF分析")
    
    gloss1 = extract_flat_values(records1_word, 'literal_gloss')
    gloss2 = extract_flat_values(records2_word, 'literal_gloss')
    
    # 简单分词（提取中文字符串）
    def tokenize(texts):
        docs = []
        for t in texts:
            words = re.findall(r'[\u4e00-\u9fff]{2,}', t)
            docs.append(' '.join(words))
        return docs
    
    docs1 = tokenize(gloss1)
    docs2 = tokenize(gloss2)
    
    # 词频统计
    all_words1 = [w for d in docs1 for w in d.split()]
    all_words2 = [w for d in docs2 for w in d.split()]
    
    freq1 = collections.Counter(all_words1)
    freq2 = collections.Counter(all_words2)
    
    pd.DataFrame(freq1.most_common(100), columns=['word', 'count']).to_csv(
        OUTPUT_DIR / '06_gloss_freq_dishu.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(freq2.most_common(100), columns=['word', 'count']).to_csv(
        OUTPUT_DIR / '06_gloss_freq_baihua.csv', index=False, encoding='utf-8-sig')
    
    # TF-IDF 对比（如果有足够数据）
    if len(docs1) > 10 and len(docs2) > 10:
        corpus = docs1 + docs2
        labels = ['dishu'] * len(docs1) + ['baihua'] * len(docs2)
        
        vectorizer = TfidfVectorizer(max_features=200, min_df=2)
        tfidf_matrix = vectorizer.fit_transform(corpus)
        feature_names = vectorizer.get_feature_names_out()
        
        # 计算每个类别的平均TF-IDF
        dishu_idx = [i for i, l in enumerate(labels) if l == 'dishu']
        baihua_idx = [i for i, l in enumerate(labels) if l == 'baihua']
        
        dishu_mean = np.array(tfidf_matrix[dishu_idx].mean(axis=0)).flatten()
        baihua_mean = np.array(tfidf_matrix[baihua_idx].mean(axis=0)).flatten()
        
        diff = dishu_mean - baihua_mean
        top_dishu = np.argsort(diff)[-20:][::-1]
        top_baihua = np.argsort(diff)[:20]
        
        df_tfidf = pd.DataFrame({
            'dishu_distinctive': [feature_names[i] for i in top_dishu],
            'dishu_score': [diff[i] for i in top_dishu],
            'baihua_distinctive': [feature_names[i] for i in top_baihua],
            'baihua_score': [diff[i] for i in top_baihua],
        })
        df_tfidf.to_csv(OUTPUT_DIR / '06_gloss_tfidf_distinctive.csv', index=False, encoding='utf-8-sig')
        print(f"  TF-IDF distinctive words saved")
    
    print(f"  已保存词频 (dishu n={len(gloss1)}, baihua n={len(gloss2)})")
    return freq1, freq2

# ==================== 分析7: 依存关系 ====================

def analyze_dependency(records1_word, records1_sent):
    print("\n[分析7] Dependency Head Relation 分布")
    
    dep = extract_flat_values(records1_word, 'dependency_head_relation')
    dep += extract_flat_values(records1_sent, 'dependency_head_relation')
    c = collections.Counter(dep)
    
    df = pd.DataFrame(c.most_common(), columns=['relation', 'count'])
    df['percentage'] = df['count'] / df['count'].sum() * 100
    df.to_csv(OUTPUT_DIR / '07_dependency_relation.csv', index=False, encoding='utf-8-sig')
    
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = plt.cm.Paired(np.linspace(0, 1, len(df)))
    ax.bar(df['relation'], df['count'], color=colors, alpha=0.8)
    ax.set_xticklabels(df['relation'], rotation=45, ha='right')
    ax.set_ylabel('Count')
    ax.set_title('Dependency to Head Relation Distribution')
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '07_dependency_relation.png', dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  已保存图表 (n={len(dep)})")
    return df

# ==================== 分析8: 分组结构统计 ====================

def analyze_group_structure(records1_word, records1_sent):
    print("\n[分析8] Group Structure 分析")
    
    level_counter = collections.Counter()
    group_sizes = []
    children_counts = []
    
    for _, data in records1_word + records1_sent:
        for g in data.get('groups', []):
            level_counter[g.get('level', 0)] += 1
            size = g.get('leaf_end', 0) - g.get('leaf_start', 0) + 1
            group_sizes.append(size)
            children = g.get('children', [])
            children_counts.append(len(children))
    
    df = pd.DataFrame({
        'metric': ['Total Groups', 'Level 1', 'Level 2+', 'Mean Size', 'Median Size', 
                   'Mean Children', 'Median Children'],
        'value': [
            sum(level_counter.values()),
            level_counter.get(1, 0),
            sum(v for k, v in level_counter.items() if k >= 2),
            np.mean(group_sizes) if group_sizes else 0,
            np.median(group_sizes) if group_sizes else 0,
            np.mean(children_counts) if children_counts else 0,
            np.median(children_counts) if children_counts else 0,
        ]
    })
    df.to_csv(OUTPUT_DIR / '08_group_structure.csv', index=False, encoding='utf-8-sig')
    
    # 分组大小分布
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    ax1 = axes[0]
    size_counts = collections.Counter(group_sizes)
    sizes = sorted(size_counts.keys())
    counts = [size_counts[s] for s in sizes]
    ax1.bar(sizes, counts, color='#3498db', alpha=0.7)
    ax1.set_xlabel('Group Size (number of atoms)')
    ax1.set_ylabel('Frequency')
    ax1.set_title('Distribution of Group Sizes')
    ax1.grid(axis='y', alpha=0.3)
    
    ax2 = axes[1]
    level_data = [(k, level_counter[k]) for k in sorted(level_counter.keys())]
    ax2.bar([x[0] for x in level_data], [x[1] for x in level_data], color='#e74c3c', alpha=0.7)
    ax2.set_xlabel('Group Level')
    ax2.set_ylabel('Count')
    ax2.set_title('Distribution of Group Levels')
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '08_group_structure.png', dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  已保存图表 (groups={sum(level_counter.values())})")
    return df

# ==================== 分析9: 指称类型 ====================

def analyze_reference_type(records1_word, records1_sent):
    print("\n[分析9] Reference Type 分布")
    
    rt = extract_flat_values(records1_word, 'reference_type')
    rt += extract_flat_values(records1_sent, 'reference_type')
    c = collections.Counter(rt)
    
    df = pd.DataFrame(c.most_common(), columns=['type', 'count'])
    df['percentage'] = df['count'] / df['count'].sum() * 100
    df.to_csv(OUTPUT_DIR / '09_reference_type.csv', index=False, encoding='utf-8-sig')
    
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.cm.Set2(np.linspace(0, 1, len(df)))
    ax.pie(df['count'], labels=df['type'], autopct='%1.1f%%', colors=colors, startangle=90)
    ax.set_title('Reference Type Distribution in 《地书》', fontsize=13)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '09_reference_type.png', dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  已保存图表 (n={len(rt)})")
    return df

# ==================== 分析10: 交际功能 ====================

def analyze_communication(records1_sent):
    print("\n[分析10] Communicative Functions 分布")
    
    cf = extract_flat_values(records1_sent, 'communication_functions')
    c = collections.Counter(cf)
    
    df = pd.DataFrame(c.most_common(), columns=['function', 'count'])
    df['percentage'] = df['count'] / df['count'].sum() * 100
    df.to_csv(OUTPUT_DIR / '10_communication_functions.csv', index=False, encoding='utf-8-sig')
    
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = plt.cm.RdYlBu(np.linspace(0.1, 0.9, len(df)))
    ax.barh(df['function'], df['count'], color=colors)
    ax.set_xlabel('Count')
    ax.set_title('Communicative Functions Distribution')
    ax.invert_yaxis()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '10_communication_functions.png', dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  已保存图表 (n={len(cf)})")
    return df

# ==================== 主流程 ====================

def main():
    print("=" * 60)
    print("《地书》vs 自然语言 —— 全面数据分析 v2")
    print("=" * 60)
    
    # 加载所有数据
    print("\n[数据加载]")
    r1w = load_json_files(str(MAT1_WORD_DIR / '*.txt'))
    r1s = load_json_files(str(MAT1_SENT_DIR / '*.txt'))
    r2w = load_json_files(str(MAT2_WORD_DIR / '*.txt'))
    
    print(f"  材料1-词标注: {len(r1w)} 有效文件")
    print(f"  材料1-句标注: {len(r1s)} 有效文件")
    print(f"  材料2-词标注: {len(r2w)} 有效文件")
    
    # 执行分析
    analyze_pos(r1w, r2w)
    analyze_semantic_primitives(r1w, r2w)
    analyze_morphological_features(r1w, r1s, r2w)
    analyze_discourse(r1s)
    analyze_semantic_role(r1w, r1s)
    analyze_gloss_tfidf(r1w, r2w)
    analyze_dependency(r1w, r1s)
    analyze_group_structure(r1w, r1s)
    analyze_reference_type(r1w, r1s)
    analyze_communication(r1s)
    
    # 生成数据汇总表
    print("\n[生成汇总表]")
    summary_data = {
        '维度': [
            '材料1-词标注文件数', '材料1-句标注文件数', '材料2-词标注文件数',
            'POS-like标注(材料1)', 'POS-like标注(材料2)',
            '语义基元(材料1)', '语义基元(材料2)',
            '形态特征(材料1)', '形态特征(材料2)',
            '篇章关系(句标注)', '语义角色', '依存关系',
            '字面Gloss(材料1)', '字面Gloss(材料2)',
            '总分组数', 'Level1分组', 'Level2+分组',
        ],
        '数值': [
            len(r1w), len(r1s), len(r2w),
            len(extract_flat_values(r1w, 'pos_like_category')),
            len(extract_flat_values(r2w, 'pos_like_category')),
            len(extract_flat_values(r1w, 'semantic_primitives')),
            len(extract_flat_values(r2w, 'semantic_primitives')),
            len(extract_flat_values(r1w, 'morphological_features')) + len(extract_flat_values(r1s, 'morphological_features')),
            len(extract_flat_values(r2w, 'morphological_features')),
            len(extract_flat_values(r1s, 'discourse_relation')),
            len(extract_flat_values(r1w, 'semantic_role_core')) + len(extract_flat_values(r1s, 'semantic_role_core')),
            len(extract_flat_values(r1w, 'dependency_head_relation')) + len(extract_flat_values(r1s, 'dependency_head_relation')),
            len(extract_flat_values(r1w, 'literal_gloss')),
            len(extract_flat_values(r2w, 'literal_gloss')),
            sum(1 for _, d in r1w+r1s for g in d.get('groups', [])),
            sum(1 for _, d in r1w+r1s for g in d.get('groups', []) if g.get('level') == 1),
            sum(1 for _, d in r1w+r1s for g in d.get('groups', []) if g.get('level', 0) >= 2),
        ]
    }
    pd.DataFrame(summary_data).to_csv(OUTPUT_DIR / '00_summary_statistics.csv', index=False, encoding='utf-8-sig')
    
    print("\n" + "=" * 60)
    print("全部分析完成！结果保存在 Document/")
    print("=" * 60)

if __name__ == '__main__':
    main()
