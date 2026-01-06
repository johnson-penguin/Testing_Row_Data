import os
import json
import shutil

def check_log_for_success(log_file_path):
    """
    Check if log file contains 'Received PDU Session Establishment Accept'
    Returns True if found (success case), False otherwise (error case)
    """
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return 'Received PDU Session Establishment Accept' in content
    except Exception as e:
        print(f"Error reading {log_file_path}: {e}")
        return None

def isolate_error_cases(source_dir, dest_dir):
    """
    Find all log files without 'Received PDU Session Establishment Accept'
    and copy them to destination directory
    """
    # Create destination directory if it doesn't exist
    os.makedirs(dest_dir, exist_ok=True)
    
    error_count = 0
    success_count = 0
    
    # Process all JSON files in source directory
    for filename in os.listdir(source_dir):
        if filename.endswith('.json'):
            source_path = os.path.join(source_dir, filename)
            
            # Check if this is an error case
            has_success = check_log_for_success(source_path)
            
            if has_success is None:
                continue
            elif not has_success:
                # This is an error case - copy it
                dest_path = os.path.join(dest_dir, filename)
                shutil.copy2(source_path, dest_path)
                print(f"[ERROR] Copied error case: {filename}")
                error_count += 1
            else:
                print(f"[SUCCESS] Success case (skipped): {filename}")
                success_count += 1
    
    return error_count, success_count

def main():
    # Define source and destination directories for option_1
    cases = [
        {
            'source': r'C:\Users\wasd0\Desktop\Testing_Row_Data\option_1\merge\op1_100_case_1',
            'dest': r'C:\Users\wasd0\Desktop\Testing_Row_Data\option_1\merge_only_error\op1_100_case_1'
        },
        {
            'source': r'C:\Users\wasd0\Desktop\Testing_Row_Data\option_1\merge\op1_100_case_2',
            'dest': r'C:\Users\wasd0\Desktop\Testing_Row_Data\option_1\merge_only_error\op1_100_case_2'
        }
    ]
    
    print("=" * 70)
    print("Isolating Error Cases for Option 1")
    print("(without PDU Session Establishment Accept)")
    print("=" * 70)
    
    total_errors = 0
    total_success = 0
    
    for i, case in enumerate(cases, 1):
        print(f"\n[Processing Case {i}: {os.path.basename(case['source'])}")
        print("-" * 70)
        
        error_count, success_count = isolate_error_cases(case['source'], case['dest'])
        total_errors += error_count
        total_success += success_count
        
        print(f"\nSummary for Case {i}:")
        print(f"   - Error cases copied: {error_count}")
        print(f"   - Success cases (not copied): {success_count}")
        print(f"   - Total files processed: {error_count + success_count}")
    
    print("\n" + "=" * 70)
    print("OVERALL SUMMARY")
    print("=" * 70)
    print(f"Total error cases isolated: {total_errors}")
    print(f"Total success cases: {total_success}")
    print(f"Total files processed: {total_errors + total_success}")
    print(f"\nError cases have been copied to merge_only_error directories")

if __name__ == "__main__":
    main()
