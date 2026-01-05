#!/usr/bin/env python
"""
Compute Domain Term Density per case and per option.
Outputs:
  - experment/domain_term_density_cases.csv
  - experment/domain_term_density_summary.csv
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Set

import pandas as pd


DOMAIN_TERMS: Set[str] = {
    "gnb", "rrc", "s1ap", "pdcp", "amf",
    "mac", "phy", "rlc", "ngap", "f1ap", "sctp",
    "ssb", "bwp", "pucch", "pusch", "prach", "dmrs",
    "mimo", "tdd", "sib1", "ngsetuprequest",
}

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


def domain_term_density(text: str, domain_terms: Set[str]) -> float:
    tokens = tokenize(text)
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in domain_terms)
    return hits / len(tokens)


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
    df["domain_density"] = df["impact_description"].apply(
        lambda t: domain_term_density(t, DOMAIN_TERMS)
    )

    # Per-case output
    cases_csv = out_dir / "domain_term_density_cases.csv"
    df.to_csv(cases_csv, index=False)
    print(f"[INFO] Saved per-case domain term density to {cases_csv}")

    # Summary per option
    summary = (
        df.groupby("option")["domain_density"]
        .agg(["mean", "std", "count"])
        .reset_index()
        .rename(
            columns={
                "mean": "avg_domain_term_density",
                "std": "std_domain_term_density",
                "count": "num_cases",
            }
        )
    )
    summary_csv = out_dir / "domain_term_density_summary.csv"
    summary.to_csv(summary_csv, index=False)
    print(f"[INFO] Saved domain term density summary to {summary_csv}")

    print("\n[SUMMARY]")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()


