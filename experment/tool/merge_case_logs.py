
import os
import json
import re
import glob

# --- Configuration ---
BASE_DIR = r"C:\Users\wasd0\Desktop\Testing_Row_Data"

# You can change this to "option_1" or "option_2"
OPTION = "option_1" 

# Derive op1/op2 short name. 
# option_1 -> op1, option_2 -> op2. 
# Logic: 'op' + last character of the option string.
SHORT_OPT = "op" + OPTION[-1] 

BATCHES = [
    {
        "name": f"{SHORT_OPT}_100_case_1",
        "json_path": os.path.join(BASE_DIR, OPTION, "json", "processed", f"{SHORT_OPT}_100_case_1.json"),
        "log_parent_dir": os.path.join(BASE_DIR, OPTION, "log", f"{SHORT_OPT}_100_case_1"),
        "output_dir": os.path.join(BASE_DIR, OPTION, "merge", f"{SHORT_OPT}_100_case_1")
    },
    {
        "name": f"{SHORT_OPT}_100_case_2",
        "json_path": os.path.join(BASE_DIR, OPTION, "json", "processed", f"{SHORT_OPT}_100_case_2.json"),
        "log_parent_dir": os.path.join(BASE_DIR, OPTION, "log", f"{SHORT_OPT}_100_case_2"),
        "output_dir": os.path.join(BASE_DIR, OPTION, "merge", f"{SHORT_OPT}_100_case_2")
    }
]

def process_batch(batch_config):
    name = batch_config["name"]
    json_path = batch_config["json_path"]
    log_parent_dir = batch_config["log_parent_dir"]
    output_dir = batch_config["output_dir"]

    print(f"--- Processing Batch: {name} ---")
    print(f"Reading JSON: {json_path}")
    
    if not os.path.exists(json_path):
        print(f"Error: JSON file not found at {json_path}")
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            cases_data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return

    if not isinstance(cases_data, list):
        print("Error: Expected JSON content to be a list of cases.")
        return

    if not os.path.exists(output_dir):
        print(f"Creating output directory: {output_dir}")
        os.makedirs(output_dir)

    print(f"Found {len(cases_data)} cases. Mapping to logs in {log_parent_dir}...")

    for case_item in cases_data:
        # Extract Case ID. Expected filename format: "DU_case_001.json" or "du_gnb_case_001.conf"
        filename = case_item.get('filename', '')
        
        # Regex to find the case number.
        match = re.search(r'case_(\d+)', filename, re.IGNORECASE)
        
        if not match:
            print(f"Skipping item, could not extract case ID from filename: {filename}")
            continue

        case_num_str = match.group(1) # e.g. "001"
        case_id = int(case_num_str)   # e.g. 1
        
        # Log Directory Search Pattern
        search_pattern = os.path.join(log_parent_dir, f"*case_{case_num_str}")
        matching_dirs = glob.glob(search_pattern)
        
        target_log_dir = None
        if matching_dirs:
            target_log_dir = matching_dirs[0] # Take the first match
        elif len(matching_dirs) > 1:
             print(f"Warning: Multiple log directories found for Case {case_id}, using first: {matching_dirs[0]}")
             target_log_dir = matching_dirs[0]
        else:
            print(f"Warning: No log directory found for Case {case_id} (Pattern: {search_pattern})")
        
        # Prepare content for the specific case output
        case_output = {
            "case_id": case_id,
            "original_json_data": case_item,
            "logs": {}
        }

        if target_log_dir:
            files_to_read = ["du.stdout.log", "cu.stdout.log", "ue.stdout.log"]
            
            for log_filename in files_to_read:
                log_path = os.path.join(target_log_dir, log_filename)
                content = ""
                if os.path.exists(log_path):
                    try:
                        with open(log_path, 'r', encoding='utf-8', errors='replace') as lf:
                            content = lf.read()
                    except Exception as e:
                        content = f"Error reading log: {e}"
                else:
                    content = "Log file not found."
                
                case_output["logs"][log_filename] = content

        # Save individual file using the config variable if desired, or standard naming
        # User requested: f"{option}_case_{case_id}_logs.json"
        
        output_filename = f"{OPTION}_case_{case_id}_logs.json"
        output_path = os.path.join(output_dir, output_filename)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as out_f:
                json.dump(case_output, out_f, indent=2)
        except Exception as e:
            print(f"Error writing output file {output_path}: {e}")

    print(f"Batch {name} complete.\n")

def main():
    print(f"Starting Multi-Batch Merge for {OPTION} ({SHORT_OPT})...")
    for batch in BATCHES:
        process_batch(batch)
    print("Multi-Batch Merge Cycle Complete.")

if __name__ == "__main__":
    main()
