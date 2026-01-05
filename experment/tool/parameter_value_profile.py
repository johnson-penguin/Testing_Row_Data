#!/usr/bin/env python
"""
Parameter & Value Profiling Tool
--------------------------------

延伸 error_type_entropy.py 的觀點，從「參數名稱 + 參數值」的角度分析：

1. 對每個 case：
   - 萃取參數名稱 param_name（例如 gNBs[0].servingCellConfigCommon[0].prach_ConfigurationIndex -> prach_ConfigurationIndex）
   - 判斷 original_value / error_value 的型別（int/float/str/bool/null/list/dict）
   - 若為可比較的數值，計算差值 delta = error_value - original_value 與絕對值 abs_delta
   - 標記變化方向：increase / decrease / same / non_numeric

2. 對每個 (option, param_name)：
   - 統計案例數 num_cases
   - 數值對的數量 num_numeric_pairs
   - 平均 |delta| mean_abs_delta
   - 方向分佈 (increase/decrease/same/non_numeric) 的比例

輸出：
  - experment/result/parameter_value_cases.csv
  - experment/result/parameter_value_summary.csv
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


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
        if "op1" in name:
            opt = "op1"
        elif "op2" in name:
            opt = "op2"
        else:
            opt = "unknown"
        records.extend(load_cases_from_file(path, opt))
    return pd.DataFrame.from_records(records)


def extract_param_name(modified_key: Any) -> str:
    import re

    if modified_key is None:
        return ""
    s = str(modified_key)
    # 去掉索引，例如 gNBs[0].x[1] -> gNBs.x
    no_idx = re.sub(r"\[[0-9]+\]", "", s)
    return no_idx.split(".")[-1]


def classify_type(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "str"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "dict"
    return "other"


def to_numeric(v: Any) -> Optional[float]:
    """嘗試將值轉成 float，若失敗則回傳 None。"""
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return None
    return None


def numeric_delta(orig: Any, err: Any) -> Tuple[Optional[float], Optional[float], str]:
    """
    回傳 (delta, abs_delta, direction)
    direction ∈ {increase, decrease, same, non_numeric}
    """
    o = to_numeric(orig)
    e = to_numeric(err)
    if o is None or e is None:
        return None, None, "non_numeric"
    d = e - o
    if d > 0:
        direction = "increase"
    elif d < 0:
        direction = "decrease"
    else:
        direction = "same"
    return d, abs(d), direction


def main() -> None:
    # 路徑：script 在 experment/tool，JSON 在 testing_row_data 根目錄，結果在 experment/result
    script_dir = Path(__file__).parent.resolve()   # .../experment/tool
    experment_dir = script_dir.parent              # .../experment
    base_path = experment_dir.parent               # .../testing_row_data
    out_dir = experment_dir / "result"
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_all_cases(base_path)
    if df.empty:
        print("[ERROR] No data loaded. Check JSON paths.")
        return

    # 填補欄位
    df["modified_key"] = df["modified_key"].fillna("")
    df["original_value"] = df["original_value"]
    df["error_value"] = df["error_value"]

    # 參數名稱與型別
    df["param_name"] = df["modified_key"].apply(extract_param_name)
    df["orig_type"] = df["original_value"].apply(classify_type)
    df["err_type"] = df["error_value"].apply(classify_type)

    # 數值差異
    deltas = df.apply(
        lambda row: numeric_delta(row["original_value"], row["error_value"]), axis=1
    )
    df["numeric_delta"] = [d[0] for d in deltas]
    df["abs_delta"] = [d[1] for d in deltas]
    df["delta_direction"] = [d[2] for d in deltas]

    # 將 per-case 結果輸出
    cases_csv = out_dir / "parameter_value_cases.csv"
    df.to_csv(cases_csv, index=False)
    print(f"[INFO] Saved per-case parameter/value profile to {cases_csv}")

    # 建立 per (option, param_name) summary
    rows: List[Dict[str, Any]] = []
    for (opt, pname), g in df.groupby(["option", "param_name"]):
        num_cases = len(g)
        # 只統計有數值 delta 的行
        numeric_mask = g["abs_delta"].notna()
        num_numeric = int(numeric_mask.sum())
        mean_abs_delta = float(g.loc[numeric_mask, "abs_delta"].mean()) if num_numeric > 0 else None

        # 方向分佈
        dir_counts = Counter(g["delta_direction"])
        total_dir = sum(dir_counts.values()) or 1
        p_increase = dir_counts.get("increase", 0) / total_dir
        p_decrease = dir_counts.get("decrease", 0) / total_dir
        p_same = dir_counts.get("same", 0) / total_dir
        p_non_numeric = dir_counts.get("non_numeric", 0) / total_dir

        rows.append(
            {
                "option": opt,
                "param_name": pname,
                "num_cases": num_cases,
                "num_numeric_pairs": num_numeric,
                "mean_abs_delta": mean_abs_delta,
                "p_increase": p_increase,
                "p_decrease": p_decrease,
                "p_same": p_same,
                "p_non_numeric": p_non_numeric,
            }
        )

    summary_df = pd.DataFrame(rows)
    summary_csv = out_dir / "parameter_value_summary.csv"
    summary_df.to_csv(summary_csv, index=False)
    print(f"[INFO] Saved parameter/value summary to {summary_csv}")

    print("\n[SUMMARY]")
    # 顯示每個 option 中，案例數最多的前幾個參數
    with pd.option_context("display.max_rows", 20, "display.max_columns", None):
        print(summary_df.sort_values(["option", "num_cases"], ascending=[True, False]).head(20).to_string(index=False))


if __name__ == "__main__":
    main()


