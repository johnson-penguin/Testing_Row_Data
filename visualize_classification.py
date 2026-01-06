#!/usr/bin/env python3
"""
視覺化分類報告比較
比較 option_1 和 option_2 的錯誤分類情況
"""

import json
import matplotlib.pyplot as plt
import matplotlib
from pathlib import Path
from collections import Counter

# 設置中文字體支持
matplotlib.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False


def load_classification_report(filepath):
    """載入分類報告"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_report(report, option_name):
    """分析分類報告"""
    # 統計嚴重度分布
    severity_counts = Counter()
    confidence_by_severity = {0: [], 1: [], 2: [], 3: []}
    
    for item in report:
        severity = item['severity_stage']
        confidence = item['confidence']
        
        severity_counts[severity] += 1
        confidence_by_severity[severity].append(confidence)
    
    # 計算平均信心度
    avg_confidence = {}
    for sev in range(4):
        if confidence_by_severity[sev]:
            avg_confidence[sev] = sum(confidence_by_severity[sev]) / len(confidence_by_severity[sev])
        else:
            avg_confidence[sev] = 0
    
    return severity_counts, avg_confidence


def create_visualizations(option1_data, option2_data):
    """創建視覺化圖表"""
    
    severity_labels = {
        0: '無錯誤\n(No Error)',
        1: '組件崩潰\n(Crash)',
        2: '組件異常\n(Abnormal)',
        3: 'UE連線失敗\n(UE Failure)'
    }
    
    # 創建圖表
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('5G gNB/OAI 錯誤分類比較：Option 1 vs Option 2', fontsize=16, fontweight='bold')
    
    # === 圖表 1: 嚴重度分布比較（柱狀圖）===
    ax1 = axes[0, 0]
    x_pos = range(4)
    width = 0.35
    
    opt1_counts = [option1_data['counts'][i] for i in range(4)]
    opt2_counts = [option2_data['counts'][i] for i in range(4)]
    
    bars1 = ax1.bar([x - width/2 for x in x_pos], opt1_counts, width, 
                    label='Option 1', alpha=0.8, color='#2E86AB')
    bars2 = ax1.bar([x + width/2 for x in x_pos], opt2_counts, width,
                    label='Option 2', alpha=0.8, color='#A23B72')
    
    ax1.set_xlabel('嚴重度等級', fontsize=12)
    ax1.set_ylabel('案例數量', fontsize=12)
    ax1.set_title('嚴重度分布比較', fontsize=14, fontweight='bold')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels([severity_labels[i] for i in range(4)])
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)
    
    # 在柱狀圖上顯示數值
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}',
                        ha='center', va='bottom', fontsize=10)
    
    # === 圖表 2: 百分比圓餅圖（Option 1）===
    ax2 = axes[0, 1]
    opt1_total = sum(opt1_counts)
    opt1_percentages = [count/opt1_total*100 if opt1_total > 0 else 0 for count in opt1_counts]
    
    # 只顯示非零的分類
    non_zero_indices = [i for i in range(4) if opt1_counts[i] > 0]
    pie_labels = [f"{severity_labels[i]}\n{opt1_counts[i]} ({opt1_percentages[i]:.1f}%)" 
                  for i in non_zero_indices]
    pie_sizes = [opt1_counts[i] for i in non_zero_indices]
    colors = ['#06D6A0', '#EF476F', '#FFD166', '#118AB2']
    pie_colors = [colors[i] for i in non_zero_indices]
    
    wedges, texts, autotexts = ax2.pie(pie_sizes, labels=pie_labels, autopct='',
                                        colors=pie_colors, startangle=90)
    ax2.set_title(f'Option 1 分類分布\n(總計: {opt1_total} 個案例)', 
                  fontsize=14, fontweight='bold')
    
    # === 圖表 3: 百分比圓餅圖（Option 2）===
    ax3 = axes[1, 0]
    opt2_total = sum(opt2_counts)
    opt2_percentages = [count/opt2_total*100 if opt2_total > 0 else 0 for count in opt2_counts]
    
    # 只顯示非零的分類
    non_zero_indices_2 = [i for i in range(4) if opt2_counts[i] > 0]
    pie_labels_2 = [f"{severity_labels[i]}\n{opt2_counts[i]} ({opt2_percentages[i]:.1f}%)" 
                    for i in non_zero_indices_2]
    pie_sizes_2 = [opt2_counts[i] for i in non_zero_indices_2]
    pie_colors_2 = [colors[i] for i in non_zero_indices_2]
    
    wedges2, texts2, autotexts2 = ax3.pie(pie_sizes_2, labels=pie_labels_2, autopct='',
                                           colors=pie_colors_2, startangle=90)
    ax3.set_title(f'Option 2 分類分布\n(總計: {opt2_total} 個案例)', 
                  fontsize=14, fontweight='bold')
    
    # === 圖表 4: 平均信心度比較===
    ax4 = axes[1, 1]
    
    opt1_confidence = [option1_data['avg_confidence'][i] for i in range(4)]
    opt2_confidence = [option2_data['avg_confidence'][i] for i in range(4)]
    
    bars1_conf = ax4.bar([x - width/2 for x in x_pos], opt1_confidence, width,
                         label='Option 1', alpha=0.8, color='#2E86AB')
    bars2_conf = ax4.bar([x + width/2 for x in x_pos], opt2_confidence, width,
                         label='Option 2', alpha=0.8, color='#A23B72')
    
    ax4.set_xlabel('嚴重度等級', fontsize=12)
    ax4.set_ylabel('平均信心度', fontsize=12)
    ax4.set_title('分類信心度比較', fontsize=14, fontweight='bold')
    ax4.set_xticks(x_pos)
    ax4.set_xticklabels([f'Severity {i}' for i in range(4)])
    ax4.set_ylim(0, 1.0)
    ax4.legend()
    ax4.grid(axis='y', alpha=0.3)
    
    # 在柱狀圖上顯示數值
    for bars in [bars1_conf, bars2_conf]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax4.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.2f}',
                        ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    
    # 保存圖表
    output_path = Path(r"C:\Users\wasd0\Desktop\Testing_Row_Data\classification_comparison.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n圖表已保存至: {output_path}")
    
    # 顯示圖表
    plt.show()


def print_summary(option1_data, option2_data):
    """列印統計摘要"""
    severity_names = ['無錯誤', '組件崩潰', '組件異常', 'UE連線失敗']
    
    print("=" * 80)
    print("分類統計摘要")
    print("=" * 80)
    print()
    
    opt1_total = sum(option1_data['counts'].values())
    opt2_total = sum(option2_data['counts'].values())
    
    print(f"{'嚴重度':<15} {'Option 1':<20} {'Option 2':<20} {'差異':<15}")
    print("-" * 80)
    
    for sev in range(4):
        name = severity_names[sev]
        opt1_count = option1_data['counts'][sev]
        opt2_count = option2_data['counts'][sev]
        opt1_pct = (opt1_count / opt1_total * 100) if opt1_total > 0 else 0
        opt2_pct = (opt2_count / opt2_total * 100) if opt2_total > 0 else 0
        diff = opt2_count - opt1_count
        diff_sign = '+' if diff > 0 else ''
        
        print(f"{name:<15} {opt1_count:>3} ({opt1_pct:>5.1f}%){'':>8} "
              f"{opt2_count:>3} ({opt2_pct:>5.1f}%){'':>8} "
              f"{diff_sign}{diff:>3}")
    
    print("-" * 80)
    print(f"{'總計':<15} {opt1_total:>3} (100.0%){'':>8} {opt2_total:>3} (100.0%){'':>8}")
    print()
    
    # 平均信心度
    print("平均分類信心度:")
    print("-" * 80)
    for sev in range(4):
        if option1_data['counts'][sev] > 0 or option2_data['counts'][sev] > 0:
            name = severity_names[sev]
            opt1_conf = option1_data['avg_confidence'][sev]
            opt2_conf = option2_data['avg_confidence'][sev]
            print(f"{name:<15} Option 1: {opt1_conf:.3f}    Option 2: {opt2_conf:.3f}")
    
    print()
    print("=" * 80)


def main():
    """主程式"""
    # 檔案路徑
    option1_path = Path(r"C:\Users\wasd0\Desktop\Testing_Row_Data\option_1\merge_only_error_class\option_1_classification_report.json")
    option2_path = Path(r"C:\Users\wasd0\Desktop\Testing_Row_Data\option_2\merge_only_error_class\option_2_classification_report.json")
    
    # 檢查檔案是否存在
    if not option1_path.exists():
        print(f"錯誤: 找不到檔案 {option1_path}")
        return
    
    if not option2_path.exists():
        print(f"錯誤: 找不到檔案 {option2_path}")
        return
    
    print("載入分類報告...")
    
    # 載入報告
    option1_report = load_classification_report(option1_path)
    option2_report = load_classification_report(option2_path)
    
    print(f"Option 1: 載入 {len(option1_report)} 個案例")
    print(f"Option 2: 載入 {len(option2_report)} 個案例")
    print()
    
    # 分析報告
    opt1_counts, opt1_confidence = analyze_report(option1_report, "Option 1")
    opt2_counts, opt2_confidence = analyze_report(option2_report, "Option 2")
    
    option1_data = {
        'counts': opt1_counts,
        'avg_confidence': opt1_confidence
    }
    
    option2_data = {
        'counts': opt2_counts,
        'avg_confidence': opt2_confidence
    }
    
    # 列印統計摘要
    print_summary(option1_data, option2_data)
    
    # 創建視覺化
    print("生成視覺化圖表...")
    create_visualizations(option1_data, option2_data)


if __name__ == "__main__":
    main()
