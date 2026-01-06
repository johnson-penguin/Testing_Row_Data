
import os
import json
import re
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
from typing import List, Dict, Set

# --- Configuration ---
BASE_DIR = r"C:\Users\wasd0\Desktop\Testing_Row_Data"
OPTION_1_JSON = os.path.join(BASE_DIR, "option_1", "json", "processed")
OPTION_1_LOG = os.path.join(BASE_DIR, "option_1", "log")
OPTION_2_JSON = os.path.join(BASE_DIR, "option_2", "json", "processed")
OPTION_2_LOG = os.path.join(BASE_DIR, "option_2", "log")

OUTPUT_DIR = r"C:\Users\wasd0\Desktop\Testing_Row_Data\experment\result"

OAI_KEYWORDS = {'RRC', 'S1AP', 'NGAP', 'gNB', 'PDCP', 'RLC', 'MAC', 'L1', 'F1AP', 'DU', 'CU', 'PHY'}

# --- Metrics Functions ---

def calculate_ttr(text_list: List[str]) -> float:
    """Calculates Type-Token Ratio for a list of strings."""
    if not text_list:
        return 0.0
    tokens = []
    for text in text_list:
        tokens.extend(str(text).lower().split()) # Basic splitting
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)

def count_domain_keywords(text_list: List[str]) -> float:
    """Calculates density of OAI keywords."""
    if not text_list:
        return 0.0
    text_blob = " ".join([str(t) for t in text_list]).upper()
    count = 0
    for kw in OAI_KEYWORDS:
        count += len(re.findall(r'\b' + re.escape(kw) + r'\b', text_blob))
    
    # Normalize by total words (approximate density)
    words = text_blob.split()
    return count / len(words) if words else 0.0

def jaccard_similarity(set1: Set, set2: Set) -> float:
    """Calculates Jaccard Index."""
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union > 0 else 0.0

def analyze_json_structure(json_files: List[str]) -> Dict:
    """Analyzes structure repetition among a group of JSON files."""
    keys_sets = []
    values_sets = []
    
    for f in json_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                # Handle list of dicts or single dict
                if isinstance(data, list):
                    # Flatten keys for the list
                    keys = set()
                    vals = set()
                    for item in data:
                        if isinstance(item, dict):
                           keys.update(item.keys())
                           vals.update([str(v) for v in item.values()])
                    keys_sets.append(keys)
                    values_sets.append(vals)
                elif isinstance(data, dict):
                    keys_sets.append(set(data.keys()))
                    values_sets.append(set([str(v) for v in data.values()]))
        except Exception as e:
            print(f"Error reading {f}: {e}")

    # Pairwise Jaccard
    jaccard_scores = []
    for i in range(len(keys_sets)):
        for j in range(i + 1, len(keys_sets)):
            jaccard_scores.append(jaccard_similarity(keys_sets[i], keys_sets[j]))
            
    return {
        "avg_structure_jaccard": np.mean(jaccard_scores) if jaccard_scores else 0.0,
        "raw_keys_list": keys_sets
    }

def analyze_log_depth(log_dir: str, case_id: str) -> Dict:
    """
    Analyzes log files for a specific case to determine error propagation depth.
    Look for specific log file patterns associated with the case.
    """
    candidate_dirs = []
    # Recursively find the folder matching the case_id
    for root, dirs, files in os.walk(log_dir):
        for d in dirs:
            if case_id in d:
               candidate_dirs.append(os.path.join(root, d))

    
    unique_modules = set()
    unique_errors = set()
    total_error_lines = 0
    
    if not candidate_dirs:
        return {"modules_count": 0, "unique_errors": 0, "error_lines": 0}
        
    target_dir = candidate_dirs[0] # Assume best match
    
    # Read common log files
    log_files = glob.glob(os.path.join(target_dir, "*.log"))
    
    module_pattern = re.compile(r'\[([a-zA-Z0-9_]+)\]') # Extract [RRC], [MAC] etc
    error_pattern = re.compile(r'(error|fail|crit|fault|assert)', re.IGNORECASE)
    
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if error_pattern.search(line):
                        total_error_lines += 1
                        # Signature: remove numbers and timestamps to find unique patterns
                        clean_line = re.sub(r'\d+', 'N', line).strip()
                        unique_errors.add(clean_line)
                        
                        # Find modules
                        mods = module_pattern.findall(line)
                        unique_modules.update(mods)
        except Exception as e:
            pass
            
    return {
        "modules_count": len(unique_modules),
        "unique_errors": len(unique_errors),
        "error_lines": total_error_lines
    }

# --- Main Analysis Loop ---

def process_option(name, json_dir, log_dir):
    results = []
    
    # We need to map JSON files to Case IDs
    # Option 1 format: op1_100_case_1.json contains a LIST of cases typically? 
    # Wait, looking at file listing: 
    #  Files: op1_100_case_1.json, op1_100_case_2.json
    #  Log Dirs: 2025..._Option_1_DU_case_001
    
    # Let's inspect the JSON structure again. 
    # Based on `type` output: It's a LIST of objects, each has "filename": "DU_case_xxx.json".
    # So one compiled JSON file contains meta-data for MANY cases.
    
    json_files = glob.glob(os.path.join(json_dir, "*.json"))
    
    for jf in json_files:
        try:
            with open(jf, 'r') as f:
                data = json.load(f)
                
            if isinstance(data, list):
                # Analyze entire file batch (lexical stats)
                descriptions = [item.get('impact_description', '') for item in data]
                ttr = calculate_ttr(descriptions)
                domain_density = count_domain_keywords(descriptions)
                
                # Analyze per-case mapping
                structure_jaccard_scores = []
                
                # Calculate internal structural similarity of this batch
                keys_list = [set(item.keys()) for item in data]
                for i in range(len(keys_list)):
                    for j in range(i+1, len(keys_list)):
                        structure_jaccard_scores.append(jaccard_similarity(keys_list[i], keys_list[j]))
                avg_jaccard = np.mean(structure_jaccard_scores) if structure_jaccard_scores else 0
                
                # Link to Logs
                for item in data:
                    # Extract Case ID from "filename" field: "DU_case_073.json" or "du_gnb_case_081.json"
                    fname = item.get('filename', '')
                    match = re.search(r'((?:DU|du_gnb)_case_\d+)', fname, re.IGNORECASE)
                    if match:
                        case_id = match.group(1)
                        log_stats = analyze_log_depth(log_dir, case_id)
                        
                        row = {
                            "Option": name,
                            "BatchFile": os.path.basename(jf),
                            "CaseID": case_id,
                            "TTR": ttr, # Shared for batch
                            "DomainDensity": domain_density, # Shared
                            "AvgJaccard": avg_jaccard, # Shared
                            "NumModules": log_stats['modules_count'],
                            "UniqueErrors": log_stats['unique_errors'],
                            "ErrorLines": log_stats['error_lines'],
                            "ErrorType": item.get('error_type', 'unknown')
                        }
                        results.append(row)
                        
        except Exception as e:
            print(f"Failed to process {jf}: {e}")
            
    return pd.DataFrame(results)

def main():
    print("Starting Analysis...")
    
    df1 = process_option("Option 1 (Baseline)", OPTION_1_JSON, OPTION_1_LOG)
    df2 = process_option("Option 2 (Context)", OPTION_2_JSON, OPTION_2_LOG)
    
    if df1.empty and df2.empty:
        print("No data found!")
        return

    full_df = pd.concat([df1, df2], ignore_index=True)
    
    # Save Raw Data
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    full_df.to_csv(os.path.join(OUTPUT_DIR, "detailed_metrics.csv"), index=False)
    
    # --- Aggregation & Visualization ---
    
    # 1. Summary Table
    summary = full_df.groupby("Option")[["TTR", "DomainDensity", "AvgJaccard", "NumModules", "UniqueErrors"]].mean()
    print("\n--- Summary Metrics (Mean) ---")
    print(summary)
    summary.to_csv(os.path.join(OUTPUT_DIR, "summary_metrics.csv"))
    
    # 2. Radar Chart
    # Normalize columns for chart
    categories = ["TTR", "DomainDensity", "AvgJaccard", "NumModules", "UniqueErrors"]
    
    # Min-Max Normalization just for plotting
    plot_data = summary.copy()
    for col in categories:
        min_val = plot_data[col].min()
        max_val = plot_data[col].max()
        if max_val - min_val > 0:
            plot_data[col] = (plot_data[col] - min_val) / (max_val - min_val)
        else:
            plot_data[col] = 0.5 # Default if equal
            
    # Add first point to end to close the loop
    # (Implementation of radar chart in matplotlib)
    
    num_vars = len(categories)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    
    for idx, row in plot_data.iterrows():
        values = row[categories].tolist()
        values += values[:1]
        ax.plot(angles, values, linewidth=1, linestyle='solid', label=idx)
        ax.fill(angles, values, alpha=0.25)
        
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
    plt.title("Option 1 vs Option 2 Performance (Normalized)")
    plt.savefig(os.path.join(OUTPUT_DIR, "radar_chart.png"))
    plt.close()
    
    # 3. Heatmap: Error Type vs Error Code (or just Error Lines as proxy)
    # Aggregating ErrorLines by Option and ErrorType
    pivot = full_df.groupby(['ErrorType', 'Option'])['NumModules'].mean().unstack()
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(pivot, annot=True, cmap="YlGnBu", fmt=".1f")
    plt.title("Avg Impact Depth (Modules Affected) by Error Type")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "heatmap_impact.png"))
    plt.close()
    
    print(f"\nAnalysis complete. Results saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
