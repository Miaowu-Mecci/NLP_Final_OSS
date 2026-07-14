#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《地书》vs 自然语言 —— Transformer/BERT 语义分析
"""

import json, glob, re, torch
import numpy as np
import pandas as pd
from pathlib import Path
from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Noto Sans CJK SC', 'WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False

BASE_DIR = Path('/home/zhb/NLP')
DATA_DIR = BASE_DIR / 'Data'
OUTPUT_DIR = BASE_DIR / 'Document'
OUTPUT_DIR.mkdir(exist_ok=True)

def load_json_files(path_pattern):
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

def extract_literal_gloss_pairs(records1_word, records2_word):
    """提取地书图形和白话文本的字面Gloss对"""
    gloss1 = []
    for f, data in records1_word:
        for ann in data.get('annotations', []):
            if ann.get('task_id') == 'literal_gloss':
                v = ann.get('value')
                if v and str(v).strip():
                    gloss1.append(str(v).strip())
    
    gloss2 = []
    for f, data in records2_word:
        for ann in data.get('annotations', []):
            if ann.get('task_id') == 'literal_gloss':
                v = ann.get('value')
                if v and str(v).strip():
                    gloss2.append(str(v).strip())
    
    return gloss1, gloss2

def get_bert_embeddings(texts, tokenizer, model, batch_size=32, max_length=64):
    """使用BERT获取文本embedding"""
    embeddings = []
    model.eval()
    device = next(model.parameters()).device
    
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            inputs = tokenizer(batch, return_tensors='pt', padding=True, truncation=True, max_length=max_length)
            inputs = {k: v.to(device) for k, v in inputs.items()}
            outputs = model(**inputs)
            # 使用[CLS] token的embedding
            batch_emb = outputs.last_hidden_state[:, 0, :].cpu().numpy()
            embeddings.append(batch_emb)
    
    return np.vstack(embeddings)

def analyze_semantic_similarity(gloss1, gloss2, tokenizer, model):
    """分析地书Gloss与白话Gloss的语义相似度"""
    print("\n[BERT语义相似度分析]")
    
    # 采样避免OOM
    sample1 = gloss1[:500] if len(gloss1) > 500 else gloss1
    sample2 = gloss2[:500] if len(gloss2) > 500 else gloss2
    
    print(f"  采样分析: dishu={len(sample1)}, baihua={len(sample2)}")
    
    emb1 = get_bert_embeddings(sample1, tokenizer, model)
    emb2 = get_bert_embeddings(sample2, tokenizer, model)
    
    # 组内相似度
    sim1 = cosine_similarity(emb1)
    sim2 = cosine_similarity(emb2)
    
    # 取上三角（排除对角线）
    triu1 = sim1[np.triu_indices_from(sim1, k=1)]
    triu2 = sim2[np.triu_indices_from(sim2, k=1)]
    
    print(f"  地书Gloss组内平均相似度: {np.mean(triu1):.4f} ± {np.std(triu1):.4f}")
    print(f"  白话Gloss组内平均相似度: {np.mean(triu2):.4f} ± {np.std(triu2):.4f}")
    
    # 跨组相似度
    cross_sim = cosine_similarity(emb1, emb2)
    print(f"  跨组平均相似度: {np.mean(cross_sim):.4f} ± {np.std(cross_sim):.4f}")
    
    # 保存结果
    results = pd.DataFrame({
        'metric': ['Dishu Intra-sim', 'Baihua Intra-sim', 'Cross-sim'],
        'mean': [np.mean(triu1), np.mean(triu2), np.mean(cross_sim)],
        'std': [np.std(triu1), np.std(triu2), np.std(cross_sim)],
        'median': [np.median(triu1), np.median(triu2), np.median(cross_sim)],
    })
    results.to_csv(OUTPUT_DIR / 'bert_semantic_similarity.csv', index=False, encoding='utf-8-sig')
    
    # 可视化
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    axes[0].hist(triu1, bins=50, alpha=0.7, color='#e74c3c', edgecolor='black')
    axes[0].set_title(f'Dishu Gloss Intra-sim\nmean={np.mean(triu1):.3f}')
    axes[0].set_xlabel('Cosine Similarity')
    
    axes[1].hist(triu2, bins=50, alpha=0.7, color='#3498db', edgecolor='black')
    axes[1].set_title(f'Baihua Gloss Intra-sim\nmean={np.mean(triu2):.3f}')
    axes[1].set_xlabel('Cosine Similarity')
    
    axes[2].hist(cross_sim.flatten(), bins=50, alpha=0.7, color='#2ecc71', edgecolor='black')
    axes[2].set_title(f'Cross-group Similarity\nmean={np.mean(cross_sim):.3f}')
    axes[2].set_xlabel('Cosine Similarity')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'bert_similarity_distribution.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  图表已保存: bert_similarity_distribution.png")
    
    return results

def analyze_pos_semantic_clusters(records1_word, records2_word, tokenizer, model):
    """分析不同POS类别的语义聚类"""
    print("\n[POS语义聚类分析]")
    
    # 提取带POS标签的Gloss
    pos_gloss = {}
    for f, data in records1_word:
        # 建立target_id -> pos映射
        pos_map = {}
        gloss_map = {}
        for ann in data.get('annotations', []):
            tid = ann.get('target_id')
            if ann.get('task_id') == 'pos_like_category':
                v = ann.get('value')
                if isinstance(v, list):
                    pos_map[tid] = v[0] if v else ''
                else:
                    pos_map[tid] = str(v)
            elif ann.get('task_id') == 'literal_gloss':
                gloss_map[tid] = str(ann.get('value', '')).strip()
        
        for tid, gloss in gloss_map.items():
            pos = pos_map.get(tid, 'Unknown')
            if pos and gloss:
                if pos not in pos_gloss:
                    pos_gloss[pos] = []
                pos_gloss[pos].append(gloss)
    
    # 选择样本量足够的POS类别
    selected_pos = {k: v[:100] for k, v in pos_gloss.items() if len(v) >= 30}
    
    print(f"  分析POS类别: {list(selected_pos.keys())}")
    
    all_texts = []
    all_labels = []
    for pos, texts in selected_pos.items():
        all_texts.extend(texts)
        all_labels.extend([pos] * len(texts))
    
    if len(all_texts) < 50:
        print("  样本不足，跳过")
        return None
    
    embeddings = get_bert_embeddings(all_texts, tokenizer, model, batch_size=16)
    
    # PCA降维到2D
    pca = PCA(n_components=2)
    emb_2d = pca.fit_transform(embeddings)
    
    # 可视化
    fig, ax = plt.subplots(figsize=(12, 8))
    unique_labels = sorted(set(all_labels))
    colors = plt.cm.tab10(np.linspace(0, 1, len(unique_labels)))
    
    for label, color in zip(unique_labels, colors):
        mask = [l == label for l in all_labels]
        x = emb_2d[mask, 0]
        y = emb_2d[mask, 1]
        ax.scatter(x, y, c=[color], label=label, alpha=0.6, s=30)
    
    ax.set_title('BERT Embedding PCA: POS-like Categories in 《地书》', fontsize=13)
    ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)')
    ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)')
    ax.legend(fontsize=9, loc='best')
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'bert_pos_pca.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  图表已保存: bert_pos_pca.png")
    
    return selected_pos

def analyze_natural_language_corpus():
    """分析自然语言语料库的关键特征"""
    print("\n[自然语言语料库特征分析]")
    
    # 读取THUcNews样本
    news_file = DATA_DIR / 'THUcNews' / 'cnews.test900wan.txt'
    corpus_samples = []
    if news_file.exists():
        with open(news_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= 1000:
                    break
                corpus_samples.append(line.strip())
    
    # 读取小说样本
    novel_dir = DATA_DIR / '小说'
    novel_files = list(novel_dir.glob('*.txt'))[:5]
    for nf in novel_files:
        with open(nf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            # 提取前2000字
            corpus_samples.append(content[:2000])
    
    # 简单统计：句子长度、标点密度
    sentence_lengths = []
    punct_ratios = []
    for text in corpus_samples:
        sentences = re.split(r'[。！？；]', text)
        for s in sentences:
            if len(s.strip()) > 0:
                sentence_lengths.append(len(s.strip()))
        punct_count = len(re.findall(r'[，。！？、；：""''（）]', text))
        char_count = len(re.findall(r'[\u4e00-\u9fff]', text))
        if char_count > 0:
            punct_ratios.append(punct_count / char_count)
    
    stats = {
        'avg_sentence_length': np.mean(sentence_lengths) if sentence_lengths else 0,
        'std_sentence_length': np.std(sentence_lengths) if sentence_lengths else 0,
        'avg_punct_ratio': np.mean(punct_ratios) if punct_ratios else 0,
        'std_punct_ratio': np.std(punct_ratios) if punct_ratios else 0,
    }
    
    pd.DataFrame([stats]).to_csv(OUTPUT_DIR / 'corpus_statistics.csv', index=False, encoding='utf-8-sig')
    print(f"  语料统计: 平均句长={stats['avg_sentence_length']:.1f}, 标点占比={stats['avg_punct_ratio']:.3f}")
    
    return stats

def main():
    print("=" * 60)
    print("Transformer/BERT 语义分析")
    print("=" * 60)
    
    # 加载数据
    r1w = load_json_files(str(DATA_DIR / '标注数据/《地书》标注数据/《地书》标注任务1-词标注/*.txt'))
    r2w = load_json_files(str(DATA_DIR / '白话版标注数据/《地书》白话版标注数据/《地书》白话版标注任务1-词标注/*.txt'))
    
    print(f"[数据加载] 材料1={len(r1w)}, 材料2={len(r2w)}")
    
    # 加载BERT
    print("\n[加载BERT模型] bert-base-chinese")
    tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')
    model = BertModel.from_pretrained('bert-base-chinese')
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    print(f"  使用设备: {device}")
    
    # 提取Gloss
    gloss1, gloss2 = extract_literal_gloss_pairs(r1w, r2w)
    print(f"\n[Gloss提取] dishu={len(gloss1)}, baihua={len(gloss2)}")
    
    # 语义相似度分析
    sim_results = analyze_semantic_similarity(gloss1, gloss2, tokenizer, model)
    
    # POS语义聚类
    pos_clusters = analyze_pos_semantic_clusters(r1w, r2w, tokenizer, model)
    
    # 自然语言语料库分析
    corpus_stats = analyze_natural_language_corpus()
    
    print("\n" + "=" * 60)
    print("BERT分析完成！")
    print("=" * 60)

if __name__ == '__main__':
    main()
