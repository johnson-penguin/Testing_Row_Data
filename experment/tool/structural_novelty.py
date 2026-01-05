#!/usr/bin/env python
"""
Compute Structural Novelty via Jaccard similarity per option.
Outputs:
  - experment/structural_novelty_cases.csv  (token sets as strings)
  - experment/structural_novelty_summary.csv
"""

import json
import re
from itertools import combinations
from pathlib import Path
from typing import List, Dict, Any, Set

import pandas as pd


DEFAULT_FILES = {
    "op1_case1": Path("option_1/json/processed/op1_100_case_1.json"),
    "op1_case2": Path("option_1/json/processed/op1_100_case_2.json"),
    "op2_case1": Path("option_2/json/processed/op2_100_case_1.json"),
    "op2_case2": Path("option_2/json/processed/op2_100_case_2.json"),
}


def tokenize(text: str) -> List[str]:
    if text is None:
        return []
    return re.findall(r"[A-Za-z0-9_]+", str(text).lower())


def case_token_set(row: pd.Series) -> Set[str]:
    text = f"{row.get('impact_description', '')} {row.get('error_type', '')} {row.get('affected_module', '')}"
    return set(tokenize(text))


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def avg_jaccard_for_option(df_opt: pd.DataFrame) -> float:
    sets = df_opt["token_set"].tolist()
    if len(sets) < 2:
        return 0.0
    sims = [jaccard(a, b) for a, b in combinations(sets, 2)]
    return float(sum(sims) / len(sims))


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


def main():
    script_dir = Path(__file__).parent.resolve()   # .../experment/tool
    experment_dir = script_dir.parent              # .../experment
    base_path = experment_dir.parent               # .../testing_row_data
    out_dir = experment_dir / "result"             # .../experment/result
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_all_cases(base_path)
    if df.empty:
        print("[ERROR] No data loaded. Check JSON paths.")
        return

    df["impact_description"] = df["impact_description"].fillna("")
    df["error_type"] = df["error_type"].fillna("unknown")
    df["affected_module"] = df["affected_module"].fillna("unknown")

    df["token_set"] = df.apply(case_token_set, axis=1)

    # Save per-case token sets (as joined strings for inspection)
    df_out = df.copy()
    df_out["token_set_str"] = df_out["token_set"].apply(lambda s: " ".join(sorted(s)))
    df_out.drop(columns=["token_set"], inplace=True)
    cases_csv = out_dir / "structural_novelty_cases.csv"
    df_out.to_csv(cases_csv, index=False)
    print(f"[INFO] Saved per-case tokens to {cases_csv}")

    rows = []
    for opt, g in df.groupby("option"):
        avg_j = avg_jaccard_for_option(g)
        novelty = 1.0 - avg_j
        rows.append(
            {
                "option": opt,
                "avg_jaccard_similarity": avg_j,
                "structural_novelty": novelty,
                "num_cases": len(g),
            }
        )
    summary = pd.DataFrame(rows)
    summary_csv = out_dir / "structural_novelty_summary.csv"
    summary.to_csv(summary_csv, index=False)
    print(f"[INFO] Saved structural novelty summary to {summary_csv}")

    print("\n[SUMMARY]")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()


