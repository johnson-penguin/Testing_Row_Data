#!/usr/bin/env python3
"""
5G gNB/OAI Log Error Classification Tool
Classifies log errors into severity levels 0-3
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple


class LogAnalyzer:
    """Analyzes 5G gNB/OAI logs and classifies errors by severity"""
    
    def __init__(self):
        # Severity 1: Component crash patterns
        self.crash_patterns = [
            r'Assertion.*failed',
            r'Assert_Exit_',
            r'Exiting execution',
            r'exit_fun',
            r'Segmentation fault',
            r'config_execcheck.*failed',
            r'fatal',
            r'abort\(\)',
            r'core dump',
        ]
        
        # Severity 2: Component abnormal but running
        self.abnormal_patterns = [
            r'ERROR',
            r'CRITICAL',
            r'failed.*initialization',
            r'failed.*init',
            r'Connection.*failed',
            r'timeout.*exceeded',
            r'retry.*limit',
        ]
        
        # Severity 3: UE connection failure patterns
        self.ue_failure_patterns = [
            r'RA procedure.*failed',
            r'RRC.*reject',
            r'Registration.*reject',
            r'PDU.*session.*failed',
            r'attach.*failed',
            r'connection.*reject',
            r'UE.*connection.*failed',
        ]
        
        # Success patterns
        self.success_patterns = [
            r'PDU Session Establishment Accept',
            r'RA procedure succeeded',
            r'RRC_CONNECTED reached',
            r'CBRA procedure succeeded',
            r'successfully configured.*IPv4',
            r'Received PDU Session Establishment Accept',
        ]
        
    def extract_component_from_filename(self, filename: str) -> str:
        """Extract affected component from filename"""
        filename_upper = filename.upper()
        if 'DU' in filename_upper:
            return 'DU'
        elif 'CU' in filename_upper:
            return 'CU'
        elif 'UE' in filename_upper:
            return 'UE'
        else:
            return 'Unknown'
    
    def check_patterns(self, text: str, patterns: List[str]) -> Tuple[bool, List[str]]:
        """Check if any pattern matches in text"""
        matches = []
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                matches.append(pattern)
        return len(matches) > 0, matches
    
    def classify_severity(self, log_data: Dict) -> Tuple[int, str, List[str], float]:
        """
        Classify log severity
        Returns: (severity_stage, root_cause_summary, evidence_keywords, confidence)
        """
        # Combine all logs
        all_logs = ""
        if "logs" in log_data:
            for log_key, log_content in log_data["logs"].items():
                all_logs += log_content + "\n"
        
        metadata = log_data.get("original_json_data", {})
        filename = metadata.get("filename", "unknown")
        affected_module = metadata.get("affected_module", "Unknown")
        error_type = metadata.get("error_type", "")
        impact_desc = metadata.get("impact_description", "")
        
        evidence = []
        
        # Priority 1: Check for crashes (Severity 1)
        has_crash, crash_evidence = self.check_patterns(all_logs, self.crash_patterns)
        if has_crash:
            evidence.extend(crash_evidence)
            root_cause = f"組件崩潰：在 {filename} 中偵測到 assertion 失敗或 exit，錯誤類型：{error_type}"
            if "Assertion" in all_logs and "failed" in all_logs:
                # Extract the specific assertion
                assertion_match = re.search(r'Assertion \(([^)]+)\) failed', all_logs)
                if assertion_match:
                    evidence.append(f"Assertion: {assertion_match.group(1)}")
            return 1, root_cause, evidence, 0.95
        
        # Check for success patterns
        has_success, success_evidence = self.check_patterns(all_logs, self.success_patterns)
        
        if has_success:
            # Check if there are multiple successful connection indicators
            pdu_session_accept = "PDU Session Establishment Accept" in all_logs
            rrc_connected = "RRC_CONNECTED reached" in all_logs
            cbra_succeeded = "CBRA procedure succeeded" in all_logs
            ipv4_configured = re.search(r'IPv4\s+[\d\.]+', all_logs)
            
            success_count = sum([pdu_session_accept, rrc_connected, cbra_succeeded, bool(ipv4_configured)])
            
            if success_count >= 2:
                # Likely successful
                root_cause = f"無錯誤：在 {filename} 中 UE 成功建立連線並獲取 IP，所有主要流程正常完成"
                evidence.extend(success_evidence)
                if ipv4_configured:
                    evidence.append(f"IPv4配置成功: {ipv4_configured.group(0)}")
                return 0, root_cause, evidence, 0.90
        
        # Priority 2: Check for UE connection failures (Severity 3)
        has_ue_failure, ue_failure_evidence = self.check_patterns(all_logs, self.ue_failure_patterns)
        if has_ue_failure:
            evidence.extend(ue_failure_evidence)
            root_cause = f"UE 連線失敗：組件啟動正常但 UE 無法完成連線，在 {affected_module} 模組偵測到失敗"
            return 3, root_cause, evidence, 0.85
        
        # Priority 3: Check for abnormal but no crash (Severity 2)
        has_abnormal, abnormal_evidence = self.check_patterns(all_logs, self.abnormal_patterns)
        if has_abnormal:
            evidence.extend(abnormal_evidence)
            root_cause = f"組件異常運行：在 {filename} 中 {affected_module} 模組出現錯誤但未崩潰，{impact_desc}"
            return 2, root_cause, evidence, 0.70
        
        # Check for connection attempts in UE log
        ue_log = log_data.get("logs", {}).get("ue.stdout.log", "")
        if "connect() to" in ue_log and "failed, errno" in ue_log:
            # UE repeatedly trying to connect but no success indication
            if not has_success:
                connect_failures = len(re.findall(r'connect\(\).*failed', ue_log))
                if connect_failures > 10:  # Many connection failures
                    root_cause = f"UE 連線失敗：UE 無法連接到 DU (重試 {connect_failures} 次)"
                    evidence.append(f"{connect_failures} connection attempts failed")
                    return 3, root_cause, evidence, 0.80
        
        # Default: If we have error_type in metadata but no clear classification
        if error_type and error_type != "":
            root_cause = f"可能異常：配置錯誤 ({error_type}) 在 {filename}，但 log 中無明確崩潰或失敗訊息"
            evidence.append(f"Config error: {error_type}")
            evidence.append(f"Impact: {impact_desc}")
            return 2, root_cause, evidence, 0.50
        
        # If reached here with success patterns, mark as success
        if has_success:
            root_cause = f"無錯誤：在 {filename} 中未發現明顯錯誤，有成功連線的跡象"
            evidence.extend(success_evidence)
            return 0, root_cause, evidence, 0.70
        
        # Uncertain case
        root_cause = f"無法判斷：log 資訊不足以明確分類，檔案 {filename}"
        evidence.append("Insufficient log information")
        return 0, root_cause, evidence, 0.30
    
    def analyze_file(self, filepath: Path) -> Dict:
        """Analyze a single log file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            case_id = log_data.get("case_id", filepath.stem)
            metadata = log_data.get("original_json_data", {})
            filename = metadata.get("filename", "unknown")
            
            # Classify severity
            severity, root_cause, evidence, confidence = self.classify_severity(log_data)
            
            # Determine component
            component = self.extract_component_from_filename(filename)
            
            result = {
                "case_id": f"{filepath.parent.name}/{filepath.name}",
                "severity_stage": severity,
                "root_cause_summary": root_cause,
                "evidence_keywords": evidence,
                "component": component,
                "confidence": confidence
            }
            
            return result
            
        except Exception as e:
            return {
                "case_id": str(filepath),
                "severity_stage": -1,
                "root_cause_summary": f"Error processing file: {str(e)}",
                "evidence_keywords": [str(e)],
                "component": "Error",
                "confidence": 0.0
            }
    
    def analyze_directory(self, directory: Path) -> List[Dict]:
        """Analyze all JSON files in a directory"""
        results = []
        json_files = sorted(directory.glob("*.json"))
        
        print(f"Analyzing {len(json_files)} files in {directory}...")
        
        for i, filepath in enumerate(json_files, 1):
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(json_files)}")
            
            result = self.analyze_file(filepath)
            results.append(result)
        
        return results


def main():
    """Main entry point"""
    # Define directories to analyze
    dir1 = Path(r"C:\Users\wasd0\Desktop\Testing_Row_Data\option_1\merge\op1_100_case_1")
    dir2 = Path(r"C:\Users\wasd0\Desktop\Testing_Row_Data\option_1\merge\op1_100_case_2")
    
    analyzer = LogAnalyzer()
    
    # Analyze both directories
    all_results = []
    
    for directory in [dir1, dir2]:
        if directory.exists():
            results = analyzer.analyze_directory(directory)
            all_results.extend(results)
        else:
            print(f"Directory not found: {directory}")
    
    # Save results to JSON file
    output_file = Path(r"C:\Users\wasd0\Desktop\Testing_Row_Data\classification_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Analysis complete!")
    print(f"  Total files analyzed: {len(all_results)}")
    print(f"  Results saved to: {output_file}")
    
    # Print summary statistics
    severity_counts = {}
    for result in all_results:
        sev = result["severity_stage"]
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    
    print("\n=== Severity Distribution ===")
    severity_labels = {
        0: "No Error (正常)",
        1: "Component Crash (崩潰)",
        2: "Component Abnormal (異常運行)",
        3: "UE Connection Failed (UE 連線失敗)",
        -1: "Processing Error"
    }
    
    for sev in sorted(severity_counts.keys()):
        label = severity_labels.get(sev, f"Unknown ({sev})")
        count = severity_counts[sev]
        percentage = (count / len(all_results)) * 100
        print(f"  Severity {sev} - {label}: {count} ({percentage:.1f}%)")
    
    # Save summary statistics
    summary_file = Path(r"C:\Users\wasd0\Desktop\Testing_Row_Data\classification_summary.txt")
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("=== 5G gNB/OAI Log Analysis Summary ===\n\n")
        f.write(f"Total files analyzed: {len(all_results)}\n")
        f.write(f"Analysis date: {Path(__file__).stat().st_mtime}\n\n")
        
        f.write("Severity Distribution:\n")
        for sev in sorted(severity_counts.keys()):
            label = severity_labels.get(sev, f"Unknown ({sev})")
            count = severity_counts[sev]
            percentage = (count / len(all_results)) * 100
            f.write(f"  Severity {sev} - {label}: {count} ({percentage:.1f}%)\n")
        
        # High confidence classifications
        f.write("\n=== High Confidence Classifications (>= 0.85) ===\n")
        high_conf = [r for r in all_results if r["confidence"] >= 0.85]
        f.write(f"Count: {len(high_conf)}\n\n")
        
        # Low confidence classifications
        f.write("=== Low Confidence Classifications (< 0.60) ===\n") 
        low_conf = [r for r in all_results if r["confidence"] < 0.60]
        f.write(f"Count: {len(low_conf)}\n")
        for r in low_conf[:10]:  # Show first 10
            f.write(f"  - {r['case_id']}: {r['root_cause_summary']}\n")
    
    print(f"  Summary saved to: {summary_file}")


if __name__ == "__main__":
    main()
