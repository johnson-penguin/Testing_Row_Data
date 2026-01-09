import json
from pathlib import Path

INPUT_FILE = Path(r"C:\Users\bmwlab\Desktop\Testing_Row_Data\Training_Data\all_row_data.jsonl")
OUTPUT_FILE = Path(r"C:\Users\bmwlab\Desktop\Testing_Row_Data\Training_Data\all_row_data_sorted.jsonl")

def sort_jsonl():
    print(f"Reading from {INPUT_FILE}...")
    data = []
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                try:
                    obj = json.loads(line)
                    data.append(obj)
                except json.JSONDecodeError:
                    print(f"Warning: Skipping invalid JSON at line {i}")

        print(f"Read {len(data)} entries. Sorting...")
        
        # Sort by misconfigured_param. Handle missing/None by converting to string.
        # We use a stable sort (Python's default) which preserves original order for same keys.
        data.sort(key=lambda x: str(x.get("misconfigured_param", "")))

        print(f"Writing sorted data to {OUTPUT_FILE}...")
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for obj in data:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        
        print("Done.")

    except FileNotFoundError:
        print(f"Error: File not found at {INPUT_FILE}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    sort_jsonl()
