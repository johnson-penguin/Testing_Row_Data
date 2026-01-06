
import json
import os
import re
import glob
from collections import Counter

class CaseAnalyzer:
    def __init__(self):
        self.results = []

    def analyze_directories(self, option_name, directories):
        print(f"Analyzing {option_name}...")
        for d in directories:
            # Match logs.json pattern
            search_path = os.path.join(d, "*_logs.json")
            files = glob.glob(search_path)
            print(f"Found {len(files)} files in {d}")
            for f in files:
                self.process_file(option_name, f)

    def process_file(self, option_name, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            orig = data.get('original_json_data', {})
            logs = data.get('logs', {})
            # Main logs seem to be in du.stdout.log, but let's check others if empty? 
            # Based on sample, important stuff is in DU.
            du_log = logs.get('du.stdout.log', '')
            if du_log is None: du_log = ""
            
            modified_key = orig.get('modified_key', '')
            error_value = str(orig.get('error_value', ''))
            
            # 1. Error Precision
            # Check if modified_key appears in log
            # We split key by '.' to check if leaf node appears (e.g. pdsch_AntennaPorts_XP)
            key_parts = modified_key.split('.')
            leaf_key = key_parts[-1] if key_parts else modified_key
            
            has_leaf_key_in_log = leaf_key in du_log
            has_full_key_in_log = modified_key in du_log
            
            # Check if error value appears
            has_error_value_in_log = error_value in du_log if len(error_value) > 0 else False
            
            # Match expected error type to log
            expected_error_type = orig.get('error_type', '').lower()
            
            # 2. Log Correlation Depth
            # Assertion Failure
            has_assertion = "Assertion" in du_log and "failed" in du_log
            
            # Source Code Trace (file.c:line)
            source_trace_match = re.search(r'([\w\.]+\.c:\d+)', du_log)
            source_trace = source_trace_match.group(1) if source_trace_match else None
            
            # Config validation (specifically looking for config_userapi or similar)
            # Sample log had: "In RCconfig_nr_macrlc() ../../../openair2/GNB_APP/gnb_config.c:1502"
            # It also had: "[CONFIG] function config_libconfig_init returned 0"
            has_config_userapi = "config_userapi" in du_log or "config_check_val" in du_log
            
            # Out of range detection
            is_out_of_range_log = "out of range" in du_log.lower() or "cannot be larger than" in du_log.lower() or "cannot be smaller than" in du_log.lower()
            
            # 3. Impact Consistency
            impact_desc = orig.get('impact_description', '')
            
            res = {
                'option': option_name,
                'file': os.path.basename(filepath),
                'error_type': expected_error_type,
                'has_leaf_key_in_log': has_leaf_key_in_log,
                'has_full_key_in_log': has_full_key_in_log,
                'has_assertion': has_assertion,
                'source_trace': source_trace,
                'has_config_userapi': has_config_userapi,
                'is_out_of_range_log': is_out_of_range_log,
                'log_length': len(du_log)
            }
            self.results.append(res)
            
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

    def generate_report(self):
        # Aggregate per option
        summary = {}
        for r in self.results:
            opt = r['option']
            if opt not in summary:
                summary[opt] = {
                    'count': 0,
                    'key_in_log': 0,
                    'assertion_failures': 0,
                    'source_trace_found': 0,
                    'config_level_detection': 0, # Approximation
                    'out_of_range_msg': 0
                }
            
            s = summary[opt]
            s['count'] += 1
            if r['has_leaf_key_in_log'] or r['has_full_key_in_log']:
                s['key_in_log'] += 1
            if r['has_assertion']:
                s['assertion_failures'] += 1
            if r['source_trace']:
                s['source_trace_found'] += 1
            if r['has_config_userapi']:
                s['config_level_detection'] += 1
            if r['is_out_of_range_log']:
                s['out_of_range_msg'] += 1

        print("\n" + "="*50)
        print("COMPARISON REPORT")
        print("="*50)
        
        for opt, s in summary.items():
            count = s['count'] if s['count'] > 0 else 1
            print(f"\nScheme: {opt}")
            print(f"Total Cases: {s['count']}")
            print(f"Error Precision (Key in Log): {s['key_in_log']} ({s['key_in_log']/count*100:.1f}%)")
            print(f"Log Correlation (Assertion Failed): {s['assertion_failures']} ({s['assertion_failures']/count*100:.1f}%)")
            print(f"Log Correlation (Source Trace Found): {s['source_trace_found']} ({s['source_trace_found']/count*100:.1f}%)")
            print(f"Log Correlation (Out of Range Msg): {s['out_of_range_msg']} ({s['out_of_range_msg']/count*100:.1f}%)")
            # print(f"Config UserAPI Hits: {s['config_level_detection']}")

        # Deep Dive: Source Trace Patterns
        print("\n[Deep Dive: Top 5 Source Traces]")
        for opt in summary.keys():
            traces = [r['source_trace'] for r in self.results if r['option'] == opt and r['source_trace']]
            print(f"\n{opt} Top Traces:")
            for trace, cnt in Counter(traces).most_common(5):
                print(f"  {trace}: {cnt}")

def main():
    analyzer = CaseAnalyzer()
    
    op1_dirs = [
        r"C:\Users\wasd0\Desktop\Testing_Row_Data\option_1\merge\op1_100_case_1",
        r"C:\Users\wasd0\Desktop\Testing_Row_Data\option_1\merge\op1_100_case_2"
    ]
    
    op2_dirs = [
        r"C:\Users\wasd0\Desktop\Testing_Row_Data\option_2\merge\op2_100_case_1",
        r"C:\Users\wasd0\Desktop\Testing_Row_Data\option_2\merge\op2_100_case_2"
    ]
    
    analyzer.analyze_directories("Option 1", op1_dirs)
    analyzer.analyze_directories("Option 2", op2_dirs)
    
    analyzer.generate_report()

if __name__ == "__main__":
    main()
