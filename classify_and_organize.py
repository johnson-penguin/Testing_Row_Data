#!/usr/bin/env python3
"""
Classify and organize error logs by severity level
Reads logs from merge_only_error and organizes them into severity-based subdirectories
"""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
import re


class LogClassifier:
    """Classifies 5G gNB/OAI logs by severity and organizes them"""
    
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
                assertion_match = re.search(r'Assertion \(([^)]+)\) failed', all_logs)
                if assertion_match:
                    evidence.append(f"Assertion: {assertion_match.group(1)}")
            return 1, root_cause, evidence, 0.95
        
        # Check for success patterns
        has_success, success_evidence = self.check_patterns(all_logs, self.success_patterns)
        
        if has_success:
            pdu_session_accept = "PDU Session Establishment Accept" in all_logs
            rrc_connected = "RRC_CONNECTED reached" in all_logs
            cbra_succeeded = "CBRA procedure succeeded" in all_logs
            ipv4_configured = re.search(r'IPv4\s+[\d\.]+', all_logs)
            
            success_count = sum([pdu_session_accept, rrc_connected, cbra_succeeded, bool(ipv4_configured)])
            
            if success_count >= 2:
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
            if not has_success:
                connect_failures = len(re.findall(r'connect\(\).*failed', ue_log))
                if connect_failures > 10:
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
    
    def classify_and_organize(self, source_dir: Path, dest_dir: Path):
        """Classify logs and organize them into severity-based folders"""
        
        # Create destination directory structure
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        severity_labels = {
            0: "severity_0_no_error",
            1: "severity_1_crash",
            2: "severity_2_abnormal",
            3: "severity_3_ue_failure"
        }
        
        # Create subdirectories for each severity level
        severity_dirs = {}
        for sev, label in severity_labels.items():
            sev_dir = dest_dir / label
            sev_dir.mkdir(exist_ok=True)
            severity_dirs[sev] = sev_dir
        
        # Find all JSON files recursively
        json_files = list(source_dir.rglob("*.json"))
        
        print(f"Found {len(json_files)} log files to classify")
        print(f"Source: {source_dir}")
        print(f"Destination: {dest_dir}")
        print()
        
        # Classification results
        results = []
        file_counts = {0: 0, 1: 0, 2: 0, 3: 0}
        
        for i, filepath in enumerate(json_files, 1):
            try:
                # Load log file
                with open(filepath, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                
                # Classify
                severity, root_cause, evidence, confidence = self.classify_severity(log_data)
                
                # Get relative path from source directory
                rel_path = filepath.relative_to(source_dir)
                
                # Determine destination path
                dest_path = severity_dirs[severity] / rel_path
                
                # Create parent directories if needed
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file to destination
                shutil.copy2(filepath, dest_path)
                
                # Update counters
                file_counts[severity] += 1
                
                # Store result
                result = {
                    "source_file": str(rel_path),
                    "severity_stage": severity,
                    "destination_folder": severity_labels[severity],
                    "root_cause_summary": root_cause,
                    "confidence": confidence,
                    "evidence_keywords": evidence[:3]  # Only first 3 for brevity
                }
                results.append(result)
                
                # Progress indicator
                if i % 10 == 0 or i == len(json_files):
                    print(f"  Progress: {i}/{len(json_files)}")
                
            except Exception as e:
                print(f"  Error processing {filepath}: {str(e)}")
                continue
        
        # Save classification report
        report_file = dest_dir / "classification_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Print summary
        print()
        print("=" * 70)
        print("Classification Summary")
        print("=" * 70)
        for sev in sorted(file_counts.keys()):
            count = file_counts[sev]
            label = severity_labels[sev]
            percentage = (count / len(json_files)) * 100 if json_files else 0
            print(f"  {label}: {count} files ({percentage:.1f}%)")
        
        print()
        print(f"Files organized into: {dest_dir}")
        print(f"Classification report: {report_file}")
        print()
        print("=" * 70)
        
        return results, file_counts


def main():
    """Main entry point"""
    
    # Define paths
    source_dir = Path(r"C:\Users\wasd0\Desktop\Testing_Row_Data\option_2\merge_only_error")
    dest_dir = Path(r"C:\Users\wasd0\Desktop\Testing_Row_Data\option_2\merge_only_error_class")
    
    if not source_dir.exists():
        print(f"Error: Source directory not found: {source_dir}")
        return
    
    print("5G gNB/OAI Error Log Classification and Organization")
    print("=" * 70)
    print()
    
    classifier = LogClassifier()
    results, file_counts = classifier.classify_and_organize(source_dir, dest_dir)
    
    print("Classification complete!")


if __name__ == "__main__":
    main()
