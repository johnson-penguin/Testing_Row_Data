#!/usr/bin/env python
"""
Parameter Change Features & Op1 vs Op2 Comparison
-------------------------------------------------

這支工具直接讀取四個 JSON（op1/op2 case_1/case_2），
針對「參數值變化前後」產生更豐富的特徵，用來比較 Op1 與 Op2 的行為差異。

Per-case 會計算：
  - param_name                : 參數名稱（去掉索引、取最後一段）
  - orig_type / err_type      : 原始值 / 錯誤值型別
  - type_changed              : 型別是否改變
  - numeric_orig / numeric_err: 若可轉 float 則給值，否則 NaN
  - numeric_delta / abs_delta : 數值差與其絕對值
  - direction                 : increase / decrease / same / non_numeric
  - zero_to_nonzero           : 0 -> 非 0
  - nonzero_to_zero           : 非 0 -> 0
  - sign_change               : 正負號改變（含 0->正/負 也可視為變號）
  - large_jump                : abs_delta > LARGE_JUMP_THRESHOLD

Per (option, param_name) 會聚合：
  - num_cases
  - num_numeric_pairs
  - mean_abs_delta
  - type_change_rate
  - sign_change_rate
  - zero_to_nonzero_rate
  - nonzero_to_zero_rate
  - large_jump_rate

最後會建立 Op1 vs Op2 的對照表（只保留兩邊都有出現的 param_name）：
  - experment/result/parameter_change_features_cases.csv
  - experment/result/parameter_change_features_summary.csv
  - experment/result/parameter_change_compare_op1_vs_op2.csv
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


DEFAULT_FILES = {
    "op1_case1": Path("option_1/json/processed/op1_100_case_1.json"),
    "op1_case2": Path("option_1/json/processed/op1_100_case_2.json"),
    "op2_case1": Path("option_2/json/processed/op2_100_case_1.json"),
    "op2_case2": Path("option_2/json/processed/op2_100_case_2.json"),
}

LARGE_JUMP_THRESHOLD = 10.0  # 可視需要調整


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
    # script 在 experment/tool，JSON 在 testing_row_data 根目錄，結果在 experment/result
    script_dir = Path(__file__).parent.resolve()   # .../experment/tool
    experment_dir = script_dir.parent              # .../experment
    base_path = experment_dir.parent               # .../testing_row_data
    out_dir = experment_dir / "result"
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_all_cases(base_path)
    if df.empty:
        print("[ERROR] No data loaded. Check JSON paths.")
        return

    df["modified_key"] = df["modified_key"].fillna("")
    df["param_name"] = df["modified_key"].apply(extract_param_name)

    df["orig_type"] = df["original_value"].apply(classify_type)
    df["err_type"] = df["error_value"].apply(classify_type)
    df["type_changed"] = df["orig_type"] != df["err_type"]

    # 數值特徵
    df["numeric_orig"] = df["original_value"].apply(to_numeric)
    df["numeric_err"] = df["error_value"].apply(to_numeric)

    deltas = df.apply(
        lambda row: numeric_delta(row["original_value"], row["error_value"]), axis=1
    )
    df["numeric_delta"] = [d[0] for d in deltas]
    df["abs_delta"] = [d[1] for d in deltas]
    df["direction"] = [d[2] for d in deltas]

    # 0/非0 / 符號變化 / 大跳動
    def zero_to_nonzero(row: pd.Series) -> bool:
        o = row["numeric_orig"]
        e = row["numeric_err"]
        if o is None or e is None:
            return False
        return o == 0.0 and e != 0.0

    def nonzero_to_zero(row: pd.Series) -> bool:
        o = row["numeric_orig"]
        e = row["numeric_err"]
        if o is None or e is None:
            return False
        return o != 0.0 and e == 0.0

    def sign_change(row: pd.Series) -> bool:
        o = row["numeric_orig"]
        e = row["numeric_err"]
        if o is None or e is None:
            return False
        # 包含 0->正/負 或 正/負->0 也視為符號相關變化
        return (o * e) < 0.0 or o == 0.0 or e == 0.0

    def large_jump(row: pd.Series) -> bool:
        a = row["abs_delta"]
        return a is not None and a is not pd.NA and a > LARGE_JUMP_THRESHOLD

    df["zero_to_nonzero"] = df.apply(zero_to_nonzero, axis=1)
    df["nonzero_to_zero"] = df.apply(nonzero_to_zero, axis=1)
    df["sign_change"] = df.apply(sign_change, axis=1)
    df["large_jump"] = df.apply(large_jump, axis=1)

    # per-case 特徵輸出
    cases_csv = out_dir / "parameter_change_features_cases.csv"
    df.to_csv(cases_csv, index=False)
    print(f"[INFO] Saved per-case parameter change features to {cases_csv}")

    # per (option, param_name) 聚合
    rows: List[Dict[str, Any]] = []
    for (opt, pname), g in df.groupby(["option", "param_name"]):
        num_cases = len(g)
        numeric_mask = g["abs_delta"].notna()
        num_numeric = int(numeric_mask.sum())
        mean_abs_delta = float(g.loc[numeric_mask, "abs_delta"].mean()) if num_numeric > 0 else None

        def rate(col: str) -> float:
            return float(g[col].mean()) if num_cases > 0 else 0.0

        rows.append(
            {
                "option": opt,
                "param_name": pname,
                "num_cases": num_cases,
                "num_numeric_pairs": num_numeric,
                "mean_abs_delta": mean_abs_delta,
                "type_change_rate": rate("type_changed"),
                "sign_change_rate": rate("sign_change"),
                "zero_to_nonzero_rate": rate("zero_to_nonzero"),
                "nonzero_to_zero_rate": rate("nonzero_to_zero"),
                "large_jump_rate": rate("large_jump"),
            }
        )

    summary_df = pd.DataFrame(rows)
    summary_csv = out_dir / "parameter_change_features_summary.csv"
    summary_df.to_csv(summary_csv, index=False)
    print(f"[INFO] Saved parameter change feature summary to {summary_csv}")

    # Op1 vs Op2 比較（只保留兩邊皆存在的 param_name）
    op1 = summary_df[summary_df["option"] == "op1"].set_index("param_name")
    op2 = summary_df[summary_df["option"] == "op2"].set_index("param_name")
    common_params = sorted(set(op1.index) & set(op2.index))

    compare_df = (
        op1.loc[common_params]
        .add_suffix("_op1")
        .join(op2.loc[common_params].add_suffix("_op2"), how="inner")
        .reset_index()
        .rename(columns={"param_name": "param_name"})
    )

    compare_csv = out_dir / "parameter_change_compare_op1_vs_op2.csv"
    compare_df.to_csv(compare_csv, index=False)
    print(f"[INFO] Saved Op1 vs Op2 parameter comparison to {compare_csv}")

    print("\n[SUMMARY] Top parameters where Op2 has larger mean_abs_delta than Op1:")
    bigger = compare_df.dropna(subset=["mean_abs_delta_op1", "mean_abs_delta_op2"])
    bigger = bigger[bigger["mean_abs_delta_op2"] > bigger["mean_abs_delta_op1"]]
    bigger["delta_mean_abs_delta"] = (
        bigger["mean_abs_delta_op2"] - bigger["mean_abs_delta_op1"]
    )
    with pd.option_context("display.max_rows", 20, "display.max_columns", None):
        print(
            bigger.sort_values("delta_mean_abs_delta", ascending=False)
            .head(20)
            .to_string(index=False)
        )


if __name__ == "__main__":
    main()


