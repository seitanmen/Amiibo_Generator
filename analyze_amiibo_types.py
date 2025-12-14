#!/usr/bin/env python3
"""
Amiibo Template Analyzer
AmiiboAPIデータを分析してタイプ別テンプレートシステムを構築する
"""

import json
import os
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

def analyze_amiibo_data(data_file: str = "amiibo_api_data.json") -> Dict:
    """AmiiboAPIデータを分析する"""
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    analysis = {
        'total_count': len(data['amiibo']),
        'types': Counter(),
        'series': Counter(),
        'type_series_mapping': defaultdict(Counter),
        'head_patterns': defaultdict(list),
        'tail_patterns': defaultdict(list),
        'samples_by_type': defaultdict(list)
    }
    
    for amiibo in data['amiibo']:
        amiibo_type = amiibo.get('type', 'Unknown')
        series = amiibo.get('amiiboSeries', 'Unknown')
        head = amiibo.get('head', '')
        tail = amiibo.get('tail', '')
        
        analysis['types'][amiibo_type] += 1
        analysis['series'][series] += 1
        analysis['type_series_mapping'][amiibo_type][series] += 1
        analysis['head_patterns'][amiibo_type].append(head)
        analysis['tail_patterns'][amiibo_type].append(tail)
        
        # 各タイプのサンプルを保存（最大3個）
        if len(analysis['samples_by_type'][amiibo_type]) < 3:
            analysis['samples_by_type'][amiibo_type].append(amiibo)
    
    return analysis

def analyze_head_patterns(heads: List[str]) -> Dict:
    """headパターンを分析"""
    patterns = {
        'prefixes': Counter(),
        'suffixes': Counter(),
        'lengths': Counter(),
        'common_prefixes': []
    }
    
    for head in heads:
        if len(head) >= 4:
            patterns['prefixes'][head[:4]] += 1
        if len(head) >= 4:
            patterns['suffixes'][head[-4:]] += 1
        patterns['lengths'][len(head)] += 1
    
    # 一般的なプレフィックスを抽出
    for prefix, count in patterns['prefixes'].most_common(5):
        patterns['common_prefixes'].append(f"{prefix}: {count}")
    
    return patterns

def print_analysis(analysis: Dict):
    """分析結果を出力"""
    print("=== AmiiboAPIデータ分析結果 ===\n")
    
    print(f"総Amiibo数: {analysis['total_count']}\n")
    
    print("=== タイプ別分布 ===")
    for amiibo_type, count in analysis['types'].most_common():
        print(f"{amiibo_type:10}: {count:3}個")
    print()
    
    print("=== 上位5シリーズ ===")
    for series, count in analysis['series'].most_common(5):
        print(f"{series:25}: {count:3}個")
    print()
    
    print("=== タイプ×シリーズマトリクス ===")
    for amiibo_type in analysis['types']:
        print(f"\n{amiibo_type}:")
        for series, count in analysis['type_series_mapping'][amiibo_type].most_common(3):
            print(f"  {series:25}: {count:3}個")
    print()
    
    print("=== headパターン分析 ===")
    for amiibo_type in analysis['types']:
        heads = analysis['head_patterns'][amiibo_type]
        patterns = analyze_head_patterns(heads)
        print(f"\n{amiibo_type} (計{len(heads)}個):")
        print(f"  一般的なプレフィックス: {', '.join(patterns['common_prefixes'])}")
        print(f"  一般的なサフィックス: {', '.join([f'{suf}:{cnt}' for suf, cnt in patterns['suffixes'].most_common(3)])}")
    
    print("\n=== サンプルAmiibo（各タイプ） ===")
    for amiibo_type, samples in analysis['samples_by_type'].items():
        print(f"\n{amiibo_type}:")
        for i, sample in enumerate(samples, 1):
            print(f"  {i}. {sample['name']} ({sample['head']}-{sample['tail']})")

def generate_template_recommendations(analysis: Dict) -> Dict:
    """テンプレートシステムの推奨事項を生成"""
    recommendations = {
        'template_strategy': {},
        'priority_types': [],
        'complexity_levels': {}
    }
    
    # 優先度の高いタイプを特定
    for amiibo_type, count in analysis['types'].most_common():
        recommendations['priority_types'].append(amiibo_type)
        
        # 複雑度レベルを評価
        series_diversity = len(analysis['type_series_mapping'][amiibo_type])
        head_diversity = len(set(analysis['head_patterns'][amiibo_type]))
        
        if series_diversity <= 2 and head_diversity <= 5:
            complexity = 'Low'
        elif series_diversity <= 5 and head_diversity <= 10:
            complexity = 'Medium'
        else:
            complexity = 'High'
        
        recommendations['complexity_levels'][amiibo_type] = complexity
        
        # テンプレート戦略を提案
        if amiibo_type == 'Card':
            recommendations['template_strategy'][amiibo_type] = {
                'base_template': 'Animal_Card.bin',
                'variations': ['Animal_Crossing', 'Mario_Sports'],
                'special_handling': 'card_specific_data'
            }
        elif amiibo_type == 'Figure':
            recommendations['template_strategy'][amiibo_type] = {
                'base_template': 'Smash_Figure.bin',
                'variations': ['Smash_Bros', 'Zelda', 'Splatoon'],
                'special_handling': 'figure_specific_data'
            }
        else:
            recommendations['template_strategy'][amiibo_type] = {
                'base_template': f'{amiibo_type}_Template.bin',
                'variations': list(analysis['type_series_mapping'][amiibo_type].keys())[:3],
                'special_handling': 'type_specific_data'
            }
    
    return recommendations

def main():
    """メイン実行関数"""
    print("AmiiboAPIデータ分析を開始します...")
    
    if not os.path.exists("amiibo_api_data.json"):
        print("Error: amiibo_api_data.jsonが見つかりません")
        return
    
    analysis = analyze_amiibo_data()
    print_analysis(analysis)
    
    recommendations = generate_template_recommendations(analysis)
    
    print("\n=== テンプレートシステム推奨事項 ===")
    print("\n優先度（実装順）:")
    for i, amiibo_type in enumerate(recommendations['priority_types'], 1):
        complexity = recommendations['complexity_levels'][amiibo_type]
        strategy = recommendations['template_strategy'][amiibo_type]
        print(f"{i}. {amiibo_type:10} (複雑度: {complexity:5})")
        print(f"   ベーステンプレート: {strategy['base_template']}")
        print(f"   バリエーション: {', '.join(strategy['variations'])}")
    
    print(f"\n分析完了！")

if __name__ == "__main__":
    main()