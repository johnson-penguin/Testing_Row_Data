#!/usr/bin/env python
"""
分析 LLM 生成案例的多樣性：
1. error_type 熵值 (錯誤類型多樣性)
2. modified_key 熵值 (參數覆蓋多樣性)
"""

import json
import math
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any, Set
import pandas as pd

# 配置路徑 (保持不變)
DEFAULT_FILES = {
    "op1_case1": Path("option_1/json/processed/op1_100_case_1.json"),
    "op1_case2": Path("option_1/json/processed/op1_100_case_2.json"),
    "op2_case1": Path("option_2/json/processed/op2_100_case_1.json"),
    "op2_case2": Path("option_2/json/processed/op2_100_case_2.json"),
}

def load_cases_from_file(path: Path, option_label: str) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    for rec in data:
        rec["option"] = option_label
        rec["source_file"] = str(path)
    return data

def load_all_cases(base_path: Path) -> pd.DataFrame:
    records: List[Dict[str, Any]] = []
    for name, rel in DEFAULT_FILES.items():
        path = base_path / rel
        if not path.is_file():
            print(f"[WARN] Missing JSON file: {path}")
            continue
        opt = "op1" if "op1" in name else "op2" if "op2" in name else "unknown"
        records.extend(load_cases_from_file(path, opt))
    return pd.DataFrame.from_records(records)

def entropy_from_counts(counts: Counter) -> float:
    total = sum(counts.values())
    if total == 0: return 0.0
    H = 0.0
    for c in counts.values():
        p = c / total
        H -= p * math.log2(p)
    return H

def main():
    # --- 路徑設定 ---
    script_dir = Path(__file__).parent.resolve()
    experment_dir = script_dir.parent
    base_path = experment_dir.parent
    out_dir = experment_dir / "result"
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- 載入數據 ---
    df = load_all_cases(base_path)
    if df.empty:
        print("[ERROR] No data loaded.")
        return

    # 填充缺失值
    df["error_type"] = df["error_type"].fillna("unknown")
    df["modified_key"] = df["modified_key"].fillna("unknown")

    # --- 分析邏輯 ---
    summary_rows = []
    detail_counts = []

    for opt, g in df.groupby("option"):
        # 1. 分析 Error Type
        et_counts = Counter(g["error_type"])
        et_entropy = entropy_from_counts(et_counts)
        # 歸一化熵 (H / log2(K))
        et_k = len(set(df["error_type"]))
        et_norm = et_entropy / math.log2(et_k) if et_k > 1 else 0.0

        # 2. 分析 Modified Key (參數名稱)
        # 有些 key 包含索引如 [0]，我們將其簡化以統一統計
        keys_simplified = g["modified_key"].str.replace(r"\[\d+\]", "", regex=True)
        mk_counts = Counter(keys_simplified)
        mk_entropy = entropy_from_counts(mk_counts)
        mk_k = len(set(df["modified_key"].str.replace(r"\[\d+\]", "", regex=True)))
        mk_norm = mk_entropy / math.log2(mk_k) if mk_k > 1 else 0.0

        # 儲存摘要
        summary_rows.append({
            "option": opt,
            "num_cases": len(g),
            "error_type_entropy": round(et_entropy, 4),
            "error_type_norm_entropy": round(et_norm, 4),
            "param_coverage_entropy": round(mk_entropy, 4),
            "param_coverage_norm_entropy": round(mk_norm, 4),
            "unique_params_tested": len(mk_counts)
        })

        # 儲存詳細計數供後續觀察
        for k, count in mk_counts.items():
            detail_counts.append({
                "option": opt,
                "type": "parameter",
                "name": k,
                "count": count
            })

    # --- 輸出結果 ---
    summary_df = pd.DataFrame(summary_rows)
    counts_df = pd.DataFrame(detail_counts)

    summary_df.to_csv(out_dir / "diversity_analysis_summary.csv", index=False)
    counts_df.to_csv(out_dir / "param_usage_counts.csv", index=False)

    print("\n[分析摘要報告]")
    print(summary_df.to_string(index=False))
    print(f"\n[INFO] 詳細結果已儲存至: {out_dir}")

if __name__ == "__main__":
    main()