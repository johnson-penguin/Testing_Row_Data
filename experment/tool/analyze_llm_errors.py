#!/usr/bin/env python
import json
import math
import re
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import List, Dict, Any, Set, Optional

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import subprocess
import argparse


# -------------------------------
# Config
# -------------------------------

DOMAIN_TERMS = {
    "gnb", "rrc", "s1ap", "pdcp", "amf",
    "mac", "phy", "rlc", "ngap", "f1ap", "sctp",
    "ssb", "bwp", "pucch", "pusch", "prach", "dmrs",
    "mimo", "tdd", "sib1", "ngsetuprequest",
}

# Paths relative to workspace root
DEFAULT_FILES = {
    "op1_case1": Path("option_1/json/processed/op1_100_case_1.json"),
    "op1_case2": Path("option_1/json/processed/op1_100_case_2.json"),
    "op2_case1": Path("option_2/json/processed/op2_100_case_1.json"),
    "op2_case2": Path("option_2/json/processed/op2_100_case_2.json"),
}


# -------------------------------
# Text utilities
# -------------------------------

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


def structural_novelty_from_avg_jaccard(avg_j: float) -> float:
    return 1.0 - avg_j


def entropy(values: List[str]) -> float:
    cnt = Counter(values)
    total = sum(cnt.values())
    if total == 0:
        return 0.0
    H = 0.0
    for c in cnt.values():
        p = c / total
        H -= p * math.log2(p)
    return H


def normalized_entropy(values: List[str], all_types: Set[str]) -> float:
    H = entropy(values)
    K = len(all_types) or 1
    return H / math.log2(K)


# -------------------------------
# Code mapping utilities
# -------------------------------

def extract_param_name(modified_key: str) -> str:
    if modified_key is None:
        return ""
    no_idx = re.sub(r"\[[0-9]+\]", "", str(modified_key))
    return no_idx.split(".")[-1]


def param_exists_in_repo(param: str, repo_root: Optional[Path]) -> Optional[bool]:
    if repo_root is None:
        return None
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
        # rg not available
        return None


# -------------------------------
# Data loading
# -------------------------------

def load_cases_from_file(path: Path, option_label: str) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    for rec in data:
        rec["option"] = option_label  # "op1" or "op2"
        rec["source_file"] = str(path)
    return data


def load_all_cases(files: Dict[str, Path]) -> pd.DataFrame:
    records: List[Dict[str, Any]] = []

    for name, path in files.items():
        if not path.is_file():
            print(f"[WARN] Missing JSON file: {path}")
            continue
        if "op1" in name:
            option = "op1"
        elif "op2" in name:
            option = "op2"
        else:
            option = "unknown"
        recs = load_cases_from_file(path, option)
        records.extend(recs)

    df = pd.DataFrame.from_records(records)
    return df


# -------------------------------
# Main analysis pipeline
# -------------------------------

def compute_metrics(df: pd.DataFrame, oai_repo_root: Optional[Path]) -> (pd.DataFrame, pd.DataFrame):
    # Derived columns
    df = df.copy()
    df["impact_description"] = df["impact_description"].fillna("")
    df["error_type"] = df["error_type"].fillna("unknown")
    df["affected_module"] = df["affected_module"].fillna("unknown")

    df["domain_density"] = df["impact_description"].apply(
        lambda t: domain_term_density(t, DOMAIN_TERMS)
    )
    df["token_set"] = df.apply(case_token_set, axis=1)
    df["param_name"] = df["modified_key"].apply(extract_param_name)

    if oai_repo_root is not None:
        df["param_in_repo"] = df["param_name"].apply(
            lambda p: bool(param_exists_in_repo(p, oai_repo_root))
        )
    else:
        df["param_in_repo"] = None

    # Global set of error types for entropy normalization
    all_error_types = set(df["error_type"].unique())

    rows = []

    for opt, g in df.groupby("option"):
        # Domain term density
        avg_domain = g["domain_density"].mean()

        # Structural novelty
        avg_j = avg_jaccard_for_option(g)
        novelty = structural_novelty_from_avg_jaccard(avg_j)

        # Code-mapping precision (only if we have repo_root and boolean values)
        if g["param_in_repo"].notna().any():
            mapped = g["param_in_repo"].sum()
            total = g["param_in_repo"].count()
            code_prec = mapped / total if total else 0.0
        else:
            code_prec = float("nan")

        # Entropy of error types
        H_norm = normalized_entropy(list(g["error_type"]), all_error_types)

        rows.append(
            {
                "option": opt,
                "avg_domain_term_density": avg_domain,
                "avg_jaccard_similarity": avg_j,
                "structural_novelty": novelty,
                "code_mapping_precision": code_prec,
                "normalized_error_type_entropy": H_norm,
                "num_cases": len(g),
            }
        )

    metrics_df = pd.DataFrame(rows)
    return metrics_df, df


def plot_metrics(metrics_df: pd.DataFrame, out_file: Path):
    # Melt to long form for plotting
    value_cols = [
        "avg_domain_term_density",
        "structural_novelty",
        "code_mapping_precision",
        "normalized_error_type_entropy",
    ]
    plot_df = metrics_df.melt(
        id_vars=["option"],
        value_vars=value_cols,
        var_name="metric",
        value_name="value",
    )

    plt.figure(figsize=(10, 5))
    sns.barplot(data=plot_df, x="metric", y="value", hue="option")
    plt.xticks(rotation=30, ha="right")
    plt.ylabel("Score")
    plt.title("Option 1 vs Option 2 – Error Generation Metrics")
    plt.tight_layout()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_file)
    plt.close()
    print(f"[INFO] Saved plot to {out_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Quantitative analysis of LLM-generated OAI error cases (Op1 vs Op2)."
    )
    parser.add_argument(
        "--oai-repo-root",
        type=str,
        default=None,
        help="Path to openairinterface5g repo root for code-mapping precision (optional).",
    )
    parser.add_argument(
        "--out-metrics-csv",
        type=str,
        default=None,
        help="Where to save the metrics CSV (default: experment/metrics_summary.csv).",
    )
    parser.add_argument(
        "--out-plot",
        type=str,
        default=None,
        help="Where to save the bar plot image (default: experment/metrics_barplot.png).",
    )
    args = parser.parse_args()

    # Paths: script in experment/tool, JSON in repo root, results in experment/result
    script_dir = Path(__file__).parent.resolve()          # .../experment/tool
    experment_dir = script_dir.parent                     # .../experment
    base_path = experment_dir.parent                      # .../testing_row_data

    files = {k: base_path / v for k, v in DEFAULT_FILES.items()}
    df = load_all_cases(files)
    if df.empty:
        print("[ERROR] No data loaded. Check JSON paths.")
        return

    repo_root = Path(args.oai_repo_root) if args.oai_repo_root else None

    metrics_df, detailed_df = compute_metrics(df, repo_root)

    # Output directory: experment/result
    output_dir = experment_dir / "result"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save metrics and (optionally) detailed per-case data
    metrics_csv = Path(args.out_metrics_csv) if args.out_metrics_csv else output_dir / "metrics_summary.csv"
    metrics_csv.parent.mkdir(parents=True, exist_ok=True)
    metrics_df.to_csv(metrics_csv, index=False)
    print(f"[INFO] Saved metrics to {metrics_csv}")

    # Example: also dump a per-case CSV if you want
    detailed_csv = metrics_csv.with_name("cases_with_features.csv")
    detailed_df.to_csv(detailed_csv, index=False)
    print(f"[INFO] Saved per-case data to {detailed_csv}")

    # Plot
    plot_path = Path(args.out_plot) if args.out_plot else output_dir / "metrics_barplot.png"
    plot_metrics(metrics_df, plot_path)

    print("\n[SUMMARY]")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    main()


