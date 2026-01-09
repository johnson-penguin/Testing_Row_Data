import json
import re
from collections import Counter

INPUT_FILE = r"C:\Users\bmwlab\Desktop\Testing_Row_Data\Training_Data\all_row_data.jsonl"

def analyze_patterns():
    # Store unique error lines to find sub-clusters
    crash_details = Counter()
    sctp_details = Counter()
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line)
                logs = ""
                if "logs" in entry:
                    for part in entry["logs"].values():
                        if isinstance(part, list): logs += "\n".join(part) + "\n"
                        elif isinstance(part, str): logs += part + "\n"
                
                # Analyze Crashes
                if "Assertion" in logs:
                    match = re.search(r"Assertion \((.*?)\) failed", logs)
                    if match:
                        crash_details[f"Assertion: {match.group(1)}"] += 1
                    else:
                        crash_details["Assertion (Other)"] += 1
                elif "Segmentation fault" in logs:
                    crash_details["Segmentation Fault"] += 1
                elif "Exiting execution" in logs:
                    # Try to find context before exit
                    match = re.search(r"In (.*?) \.\.", logs)
                    if match:
                         crash_details[f"Exit in: {match.group(1)}"] += 1
                    else:
                         crash_details["Generic Exit"] += 1

                # Analyze SCTP
                if "Connection refused" in logs:
                    sctp_details["Connection Refused"] += 1
                elif "SCTP.*failed" in logs:
                    sctp_details["SCTP Failed (Generic)"] += 1
                elif "getaddrinfo error" in logs: # This was lumped in Config but might be network
                    sctp_details["DNS/Addr Error"] += 1
                    
            except Exception:
                pass

    print("--- CRASH BREAKDOWN ---")
    for k, v in crash_details.most_common(10):
        print(f"{k}: {v}")
        
    print("\n--- SCTP BREAKDOWN ---")
    for k, v in sctp_details.most_common(10):
        print(f"{k}: {v}")

if __name__ == "__main__":
    analyze_patterns()
