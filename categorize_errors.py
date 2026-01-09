import json
import re
import csv
from pathlib import Path
from collections import Counter, defaultdict

# Configuration
INPUT_FILE = r"C:\Users\bmwlab\Desktop\Testing_Row_Data\Training_Data\all_row_data.jsonl"
OUTPUT_CSV = r"C:\Users\bmwlab\Desktop\Testing_Row_Data\categorized_errors.csv"
OUTPUT_STATS = r"C:\Users\bmwlab\Desktop\Testing_Row_Data\categorization_stats.txt"

# Regex Patterns for Categories
PATTERNS = {
    "GTP/Interface Creation Failure": [
        r"Assertion.*gtpInst > 0",
        r"cannot create DU F1-U GTP module",
        r"sctp_handle_new_association_req", 
        r"Assertion.*status == 0" # Often associated with sctp_handle_new_association_req
    ],
    "Radio Frequency/ARFCN Issue": [
        r"Assertion.*freq.*3000000000",
        r"Assertion.*nrarfcn >= N_OFFs",
        r"Assertion.*delta_f_RA_PRACH < 6",
        r"Assertion.*subcarrier_offset"
    ],
    "Encoding/Buffer Overflow": [
        r"Assertion.*enc_rval.encoded > 0",
        r"Assertion.*bw_index"
    ],
    "SCTP Connection Refused": [
        r"Connection refused",
        r"connect.*failed",
        r"errno\(111\)"
    ],
    "DNS/Address Resolution Error": [
        r"getaddrinfo error", 
        r"Name or service not known"
    ],
    "General Component Crash": [
        r"Assertion.*failed",
        r"Segmentation fault",
        r"dumping core",
        r"exiting with status 1",
        r"AS_ASSERT",
        r"Exiting execution",
        r"Exiting OAI softmodem",
        r"_Assert_Exit_"
    ],
    "Configuration/Syntax Error": [
        r"syntax error",
        r"unknown option",
        r"invalid value",
        r"config_execcheck",
        r"Failed to parse",
        r"Error in configuration",
        r"mismatch in.*configuration"
    ],
    "Network/PLMN/Cell ID Mismatch": [
        r"PLMN.*mismatch",
        r"CellIdentity.*mismatch",
        r"TAC.*mismatch",
        r"Network.*configuration.*mismatch",
        r"Dropping.*due to.*mismatch"
    ],
    "RF/Hardware/Feature Missing": [
        r"rfsimulator.*failed",
        r"features not found",
        r"No radio device",
        r"Failed to load.*library",
        r"Device.*not found"
    ]
}

def classify_log(log_text):
    """
    Classifies a single log entry based on regex patterns.
    Returns the first matching category or 'Unknown'.
    """
    if not log_text:
        return "Empty Log"

    # Priority 1: Specific Technical Failures (GTP, RF, Encoding)
    for cat in ["GTP/Interface Creation Failure", "Radio Frequency/ARFCN Issue", "Encoding/Buffer Overflow", "DNS/Address Resolution Error"]:
        for pattern in PATTERNS[cat]:
            if re.search(pattern, log_text, re.IGNORECASE | re.MULTILINE):
                return cat

    # Priority 2: Config (often causes the above, but check explicit config errors first if unique)
    for pattern in PATTERNS["Configuration/Syntax Error"]:
        if re.search(pattern, log_text, re.IGNORECASE | re.MULTILINE):
            return "Configuration/Syntax Error"

    # Priority 3: Specific Connection Errors
    for pattern in PATTERNS["SCTP Connection Refused"]:
        if re.search(pattern, log_text, re.IGNORECASE | re.MULTILINE):
            return "SCTP Connection Refused"

    # Priority 4: General Crash (Catch-all for other assertions)
    for pattern in PATTERNS["General Component Crash"]:
        if re.search(pattern, log_text, re.IGNORECASE | re.MULTILINE):
            return "General Component Crash/Assertion"

    # Priority 5: Other Network/Misc
    for cat in ["Network/PLMN/Cell ID Mismatch", "RF/Hardware/Feature Missing"]:
        for pattern in PATTERNS[cat]:
            if re.search(pattern, log_text, re.IGNORECASE | re.MULTILINE):
                return cat
                
    return "Unknown/Other"

def main():
    input_path = Path(INPUT_FILE)
    if not input_path.exists():
        print(f"Error: Input file not found at {input_path}")
        return

    print(f"Processing {input_path}...")
    
    stats = Counter()
    category_lines = defaultdict(list)
    results = []

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line)
                    
                    # Combine all log parts (CU, DU, UE) for analysis
                    logs_combined = ""
                    if "logs" in entry:
                        for part in entry["logs"].values():
                            if isinstance(part, list):
                                logs_combined += "\n".join(part) + "\n"
                            elif isinstance(part, str):
                                logs_combined += part + "\n"
                    
                    category = classify_log(logs_combined)
                    stats[category] += 1
                    category_lines[category].append(line_num)
                    
                    # Store distinct hint for review
                    misconf = entry.get("misconfigured_param", "N/A")
                    
                    results.append({
                        "Line": line_num,
                        "Category": category,
                        "Misconfigured_Param": str(misconf),
                        "Snippet": logs_combined[:200].replace('\n', ' ')  # First 200 chars for preview
                    })
                    
                except json.JSONDecodeError:
                    print(f"Warning: Invalid JSON on line {line_num}")
                    stats["JSON Decode Error"] += 1
                    category_lines["JSON Decode Error"].append(line_num)

        # Write CSV results
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ["Line", "Category", "Misconfigured_Param", "Snippet"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow(r)
        
        # Write Stats
        with open(OUTPUT_STATS, 'w', encoding='utf-8') as f:
            f.write("Classification Statistics:\n")
            f.write("==========================\n")
            total = sum(stats.values())
            f.write(f"Total Entries: {total}\n\n")
            for cat, count in stats.most_common():
                pct = (count / total) * 100 if total > 0 else 0
                f.write(f"Category: {cat}\n")
                f.write(f"Count: {count} ({pct:.2f}%)\n")
                lines = category_lines[cat]
                # Write line numbers, wrapping text if it's too long could be nice but simple comma separated is fine for data checking
                f.write(f"Lines: {', '.join(map(str, lines))}\n")
                f.write("-" * 40 + "\n")
        
        print("\nAnalysis Complete.")
        print("Statistics:")
        for cat, count in stats.most_common():
             print(f"{cat}: {count}")
             
        print(f"\nDetailed CSV written to: {OUTPUT_CSV}")
        print(f"Stats written to: {OUTPUT_STATS}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
