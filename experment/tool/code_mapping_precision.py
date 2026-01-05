#!/usr/bin/env python
"""
Compute Code-Mapping Precision using ripgrep over an OAI repo.
Requires:
  - --oai-repo-root pointing to openairinterface5g root
  - ripgrep (rg) installed and available on PATH

Outputs:
  - experment/code_mapping_cases.csv
  - experment/code_mapping_precision_summary.csv
"""

import json
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

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


def extract_param_name(modified_key: str) -> str:
    if modified_key is None:
        return ""
    no_idx = re.sub(r"\[[0-9]+\]", "", str(modified_key))
    return no_idx.split(".")[-1]


def param_exists_in_repo(param: str, repo_root: Path) -> Optional[bool]:
    param = param.strip()
    if not param:
        return False
    try:
        result = subprocess.run(
            ["rg", "-n", param, str(repo_root)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except FileNotFoundError:
        print("[ERROR] ripgrep (rg) not found on PATH.")
        return None


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Compute code-mapping precision for generated error parameters."
    )
    parser.add_argument(
        "--oai-repo-root",
        type=str,
        required=True,
        help="Path to openairinterface5g repo root.",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent.resolve()   # .../experment/tool
    experment_dir = script_dir.parent              # .../experment
    base_path = experment_dir.parent               # .../testing_row_data
    out_dir = experment_dir / "result"             # .../experment/result
    out_dir.mkdir(parents=True, exist_ok=True)

    repo_root = Path(args.oai_repo_root).resolve()
    if not repo_root.is_dir():
        print(f"[ERROR] Repo root not found: {repo_root}")
        return

    df = load_all_cases(base_path)
    if df.empty:
        print("[ERROR] No data loaded. Check JSON paths.")
        return

    df["modified_key"] = df["modified_key"].fillna("")
    df["param_name"] = df["modified_key"].apply(extract_param_name)

    df["param_in_repo"] = df["param_name"].apply(
        lambda p: param_exists_in_repo(p, repo_root)
    )

    # Per-case output
    cases_csv = out_dir / "code_mapping_cases.csv"
    df.to_csv(cases_csv, index=False)
    print(f"[INFO] Saved per-case code mapping data to {cases_csv}")

    # Summary precision per option (ignoring None rows if rg is missing)
    rows = []
    for opt, g in df.groupby("option"):
        valid = g["param_in_repo"].dropna()
        total = len(valid)
        if total == 0:
            precision = float("nan")
        else:
            mapped = valid.sum()
            precision = mapped / total
        rows.append(
            {
                "option": opt,
                "code_mapping_precision": precision,
                "num_cases_with_check": total,
                "num_cases_total": len(g),
            }
        )
    summary = pd.DataFrame(rows)
    summary_csv = out_dir / "code_mapping_precision_summary.csv"
    summary.to_csv(summary_csv, index=False)
    print(f"[INFO] Saved code mapping precision summary to {summary_csv}")

    print("\n[SUMMARY]")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()


