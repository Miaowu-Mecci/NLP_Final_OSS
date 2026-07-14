#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《地书》图形语言 vs 自然语言 —— 数据分析主脚本
视角：象似性（Iconicity）与组合性（Compositionality）
"""

import json
import glob
import os
import sys
import collections
import re
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Noto Sans CJK SC']
plt.rcParams['axes.unicode_minus'] = False

# ==================== 路径配置 ====================
BASE_DIR = Path('/home/zhb/NLP')
DATA_DIR = BASE_DIR / 'Data'
OUTPUT_DIR = BASE_DIR / 'Document'
OUTPUT_DIR.mkdir(exist_ok=True)

MAT1_WORD_DIR = DATA_DIR / '标注数据/《地书》标注数据/《地书》标注任务1-词标注'
MAT1_SENT_DIR = DATA_DIR / '标注数据/《地书》标注数据/《地书》标注任务2-句标注'
MAT2_WORD_DIR = DATA_DIR / '白话版标注数据/《地书》白话版标注数据/《地书》白话版标注任务1-词标注'
MAT2_SENT_DIR = DATA_DIR / '白话版标注数据/《地书》白话版标注数据/《地书》白话版标注任务2-句标注'

# ==================== 材料1解析 ====================

def parse_material1_word():
    """解析材料1词标注数据"""
    files = list(MAT1_WORD_DIR.glob('*.txt'))
    print(f"[材料1-词标注] 发现 {len(files)} 个文件")
    
    records = []
    task_counter = collections.Counter()
    group_counter = 0
    atoms_grouped = set()
    scale_records = []
    
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                raw = fp.read().strip()
                if not raw:
                    continue
                data = json.loads(raw)
        except Exception as e:
            continue
        
        groups = data.get('groups', [])
        annotations = data.get('annotations', [])
        session = data.get('session', {})
        
        group_counter += len(groups)
        for g in groups:
            for i in range(g.get('leaf_start', 0), g.get('leaf_end', 0) + 1):
                atoms_grouped.add(i)
        
        for ann in annotations:
            tid = ann.get('task_id')
            val = ann.get('value')
            task_counter[tid] += 1
            
            rec = {
                'file': f.name,
                'target_id': ann.get('target_id'),
                'task_id': tid,
                'value': val,
                'updated_at': ann.get('updated_at'),
                'pageStartKey': session.get('pageStartKey'),
                'pageEndKey': session.get('pageEndKey'),
            }
            records.append(rec)
            
            # 提取量表数据
            if tid in ['cognitive_linguistic_metrics', 'syntactic_semantic_fitness', 'annotation_confidence']:
                if isinstance(val, dict):
                    for item_id, score in val.items():
                        scale_records.append({
                            'file': f.name,
                            'task_id': tid,
                            'item_id': item_id,
                            'score': float(score) if score is not None else np.nan,
                            'target_id': ann.get('target_id'),
                        })
    
    df = pd.DataFrame(records)
    df_scale = pd.DataFrame(scale_records)
    
    print(f"  有效标注记录: {len(df)}")
    print(f"  总分组数: {group_counter}")
    print(f"  被分组Atom数(唯一): {len(atoms_grouped)}")
    print(f"  量表记录: {len(df_scale)}")
    
    return df, df_scale, task_counter, group_counter, atoms_grouped


# ==================== 材料2解析 ====================

def parse_material2_word():
    """解析材料2白话版词标注数据"""
    files = list(MAT2_WORD_DIR.glob('*.txt'))
    print(f"\n[材料2-词标注] 发现 {len(files)} 个文件")
    
    records = []
    task_counter = collections.Counter()
    units_total = 0
    
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                raw = fp.read().strip()
                if not raw:
                    continue
                data = json.loads(raw)
        except Exception as e:
            continue
        
        # 只处理 dict 格式的传统格式
        if not isinstance(data, dict):
            continue
        if not isinstance(data.get('annotations'), list):
            continue
        if 'units' not in data:
            continue
        
        units = data.get('units', [])
        annotations = data.get('annotations', [])
        units_total += len(units)
        
        # 建立 unit_id -> token 映射
        unit_map = {u.get('id', f'u{i}'): u.get('token', '') for i, u in enumerate(units)}
        
        for ann in annotations:
            uid = ann.get('unit_id')
            for key, val in ann.items():
                if key == 'unit_id':
                    continue
                task_counter[key] += 1
                records.append({
                    'file': f.name,
                    'unit_id': uid,
                    'token': unit_map.get(uid, ''),
                    'task_id': key,
                    'value': val,
                })
    
    df = pd.DataFrame(records)
    print(f"  有效标注记录: {len(df)}")
    print(f"  总标注单元数: {units_total}")
    
    return df, task_counter, units_total


# ==================== 统计与可视化 ====================

def analyze_scale_data(df_scale):
    """分析量表数据"""
    if df_scale.empty:
        print("[量表分析] 无量表数据")
        return None
    
    print("\n[量表分析] 开始...")
    
    # 按 item_id 分组统计
    scale_summary = df_scale.groupby('item_id').agg(
        count=('score', 'count'),
        mean=('score', 'mean'),
        std=('score', 'std'),
        median=('score', 'median'),
        min=('score', 'min'),
        max=('score', 'max')
    ).round(3)
    
    print("\n量表指标统计:")
    print(scale_summary)
    
    # 保存到CSV
    scale_summary.to_csv(OUTPUT_DIR / 'scale_summary.csv', encoding='utf-8-sig')
    df_scale.to_csv(OUTPUT_DIR / 'scale_raw_data.csv', index=False, encoding='utf-8-sig')
    
    # 可视化
    items = df_scale['item_id'].unique()
    if len(items) > 0:
        fig, axes = plt.subplots(2, 1, figsize=(12, 10))
        
        # 箱线图
        ax1 = axes[0]
        sns.boxplot(data=df_scale, x='item_id', y='score', ax=ax1)
        ax1.set_title('Cognitive-Linguistic Metrics Distribution (《地书》图形标注)')
        ax1.set_xlabel('Metric Item')
        ax1.set_ylabel('Score (1-7)')
        ax1.tick_params(axis='x', rotation=45)
        
        # 均值条形图
        ax2 = axes[1]
        mean_scores = df_scale.groupby('item_id')['score'].mean().sort_values(ascending=False)
        colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(mean_scores)))
        mean_scores.plot(kind='bar', ax=ax2, color=colors)
        ax2.set_title('Mean Scores by Metric')
        ax2.set_ylabel('Mean Score')
        ax2.tick_params(axis='x', rotation=45)
        ax2.axhline(y=4, color='r', linestyle='--', alpha=0.5, label='Midpoint (4)')
        ax2.legend()
        
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'scale_analysis.png', dpi=200, bbox_inches='tight')
        plt.close()
        print("  图表已保存: scale_analysis.png")
    
    return scale_summary


def analyze_pos_distribution(df1, df2):
    """对比材料1和材料2的POS-like分布"""
    print("\n[POS-like 分布分析] 开始...")
    
    # 材料1: pos_like_category (multi)
    pos1 = df1[df1['task_id'] == 'pos_like_category']['value'].tolist()
    pos1_flat = []
    for val in pos1:
        if isinstance(val, list):
            pos1_flat.extend(val)
        elif isinstance(val, str):
            pos1_flat.append(val)
    pos1_counter = collections.Counter(pos1_flat)
    
    # 材料2: pos_like_category
    pos2 = df2[df2['task_id'] == 'pos_like_category']['value'].tolist()
    pos2_flat = []
    for val in pos2:
        if isinstance(val, list):
            pos2_flat.extend(val)
        elif isinstance(val, str):
            pos2_flat.append(val)
    pos2_counter = collections.Counter(pos2_flat)
    
    print(f"  材料1 POS标签数: {len(pos1_flat)} (唯一类别: {len(pos1_counter)})")
    print(f"  材料2 POS标签数: {len(pos2_flat)} (唯一类别: {len(pos2_counter)})")
    
    # 合并为DataFrame
    all_labels = sorted(set(pos1_counter.keys()) | set(pos2_counter.keys()))
    df_pos = pd.DataFrame({
        'label': all_labels,
        'material1_count': [pos1_counter.get(l, 0) for l in all_labels],
        'material2_count': [pos2_counter.get(l, 0) for l in all_labels],
    })
    df_pos['material1_pct'] = df_pos['material1_count'] / sum(pos1_counter.values()) * 100
    df_pos['material2_pct'] = df_pos['material2_count'] / sum(pos2_counter.values()) * 100
    
    df_pos.to_csv(OUTPUT_DIR / 'pos_distribution.csv', index=False, encoding='utf-8-sig')
    print("  POS分布对比已保存: pos_distribution.csv")
    
    # 可视化
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(df_pos))
    width = 0.35
    ax.bar(x - width/2, df_pos['material1_pct'], width, label='《地书》图形 (材料1)', alpha=0.8)
    ax.bar(x + width/2, df_pos['material2_pct'], width, label='白话文本 (材料2)', alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(df_pos['label'], rotation=45, ha='right')
    ax.set_ylabel('Percentage (%)')
    ax.set_title('POS-like Category Distribution: 《地书》图形 vs 白话文本')
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'pos_distribution.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  图表已保存: pos_distribution.png")
    
    return df_pos


def analyze_semantic_primitives(df1, df2):
    """分析语义基元分布"""
    print("\n[语义基元分析] 开始...")
    
    # 材料1
    sp1 = df1[df1['task_id'] == 'semantic_primitives']['value'].tolist()
    sp1_flat = []
    for val in sp1:
        if isinstance(val, list):
            sp1_flat.extend(val)
        elif isinstance(val, str):
            sp1_flat.append(val)
    sp1_counter = collections.Counter(sp1_flat)
    
    # 材料2
    sp2 = df2[df2['task_id'] == 'semantic_primitives']['value'].tolist()
    sp2_flat = []
    for val in sp2:
        if isinstance(val, list):
            sp2_flat.extend(val)
        elif isinstance(val, str):
            sp2_flat.append(val)
    sp2_counter = collections.Counter(sp2_flat)
    
    print(f"  材料1 语义基元数: {len(sp1_flat)} (唯一: {len(sp1_counter)})")
    print(f"  材料2 语义基元数: {len(sp2_flat)} (唯一: {len(sp2_counter)})")
    
    all_labels = sorted(set(sp1_counter.keys()) | set(sp2_counter.keys()))
    df_sp = pd.DataFrame({
        'primitive': all_labels,
        'material1_count': [sp1_counter.get(l, 0) for l in all_labels],
        'material2_count': [sp2_counter.get(l, 0) for l in all_labels],
    })
    
    df_sp.to_csv(OUTPUT_DIR / 'semantic_primitives.csv', index=False, encoding='utf-8-sig')
    
    # 可视化
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(df_sp))
    width = 0.35
    ax.bar(x - width/2, df_sp['material1_count'], width, label='《地书》图形', alpha=0.8)
    ax.bar(x + width/2, df_sp['material2_count'], width, label='白话文本', alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(df_sp['primitive'], rotation=45, ha='right')
    ax.set_ylabel('Count')
    ax.set_title('Semantic Primitives Distribution')
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'semantic_primitives.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  图表已保存: semantic_primitives.png")
    
    return df_sp


def analyze_literal_gloss(df1, df2):
    """分析字面对应词的词频"""
    print("\n[字面对应词分析] 开始...")
    
    gloss1 = df1[df1['task_id'] == 'literal_gloss']['value'].tolist()
    gloss1_texts = [str(v).strip() for v in gloss1 if v]
    
    gloss2 = df2[df2['task_id'] == 'literal_gloss']['value'].tolist()
    gloss2_texts = [str(v).strip() for v in gloss2 if v]
    
    print(f"  材料1 literal_gloss: {len(gloss1_texts)}")
    print(f"  材料2 literal_gloss: {len(gloss2_texts)}")
    
    # 词频统计（简单分词）
    words1 = []
    for text in gloss1_texts:
        words1.extend(re.findall(r'[\u4e00-\u9fff]+', text))
    
    words2 = []
    for text in gloss2_texts:
        words2.extend(re.findall(r'[\u4e00-\u9fff]+', text))
    
    freq1 = collections.Counter(words1)
    freq2 = collections.Counter(words2)
    
    print(f"  材料1 高频词 Top10: {freq1.most_common(10)}")
    print(f"  材料2 高频词 Top10: {freq2.most_common(10)}")
    
    # 保存
    pd.DataFrame(freq1.most_common(50), columns=['word', 'count']).to_csv(
        OUTPUT_DIR / 'gloss_freq_material1.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(freq2.most_common(50), columns=['word', 'count']).to_csv(
        OUTPUT_DIR / 'gloss_freq_material2.csv', index=False, encoding='utf-8-sig')
    
    return freq1, freq2


def analyze_groups_structure(df1_scale):
    """分析分组结构（层级分布）"""
    # 需要从材料1原始文件中读取groups
    files = list(MAT1_WORD_DIR.glob('*.txt'))
    level_counter = collections.Counter()
    group_sizes = []
    
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                raw = fp.read().strip()
                if not raw:
                    continue
                data = json.loads(raw)
        except:
            continue
        
        for g in data.get('groups', []):
            level = g.get('level', 0)
            level_counter[level] += 1
            size = g.get('leaf_end', 0) - g.get('leaf_start', 0) + 1
            group_sizes.append(size)
    
    print(f"\n[分组结构分析]")
    print(f"  层级分布: {dict(level_counter)}")
    print(f"  平均组大小: {np.mean(group_sizes):.2f} ± {np.std(group_sizes):.2f}")
    print(f"  中位组大小: {np.median(group_sizes):.0f}")
    
    return level_counter, group_sizes


# ==================== 主流程 ====================

def main():
    print("=" * 60)
    print("《地书》图形语言 vs 自然语言 —— 数据分析")
    print("=" * 60)
    
    # 解析材料1
    df1, df1_scale, task1_counter, group_count, atoms_grouped = parse_material1_word()
    
    # 解析材料2
    df2, task2_counter, units_total = parse_material2_word()
    
    # 量表分析
    scale_summary = analyze_scale_data(df1_scale)
    
    # POS分布对比
    df_pos = analyze_pos_distribution(df1, df2)
    
    # 语义基元分析
    df_sp = analyze_semantic_primitives(df1, df2)
    
    # 字面对应词分析
    freq1, freq2 = analyze_literal_gloss(df1, df2)
    
    # 分组结构
    level_counter, group_sizes = analyze_groups_structure(df1_scale)
    
    # 保存综合汇总
    summary = {
        '材料1-词标注文件数': 365,
        '材料1-总分组数': group_count,
        '材料1-被分组Atom数': len(atoms_grouped),
        '材料1-总标注记录': len(df1),
        '材料2-词标注文件数': 202,
        '材料2-总标注单元数': units_total,
        '材料2-总标注记录': len(df2),
    }
    pd.Series(summary).to_csv(OUTPUT_DIR / 'data_summary.csv', encoding='utf-8-sig', header=['value'])
    
    # 任务分布
    task_dist = pd.DataFrame({
        'task_id': list(task1_counter.keys()),
        'material1_count': list(task1_counter.values()),
    })
    task_dist.to_csv(OUTPUT_DIR / 'task_distribution.csv', index=False, encoding='utf-8-sig')
    
    print("\n" + "=" * 60)
    print("数据分析完成，所有结果已保存到 Document/")
    print("=" * 60)

if __name__ == '__main__':
    main()
