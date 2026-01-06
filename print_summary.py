import json
from pathlib import Path

# Load results
results_file = Path("classification_results.json")
with open(results_file, 'r', encoding='utf-8') as f:
    results = json.load(f)

# Calculate statistics
total = len(results)
severity_counts = {}
for result in results:
    sev = result['severity_stage']
    severity_counts[sev] = severity_counts.get(sev, 0) + 1

# Labels
severity_labels = {
    0: "No Error (正常)",
    1: "Component Crash (崩潰)",
    2: "Component Abnormal (異常運行)",
    3: "UE Connection Failed (UE 連線失敗)",
}

# Print summary
print("=" * 70)
print("5G gNB/OAI Log Analysis Summary")
print("=" * 70)
print(f"Total files analyzed: {total}")
print()
print("Severity Distribution:")
print("-" * 70)

for sev in sorted(severity_counts.keys()):
    label = severity_labels.get(sev, f"Unknown ({sev})")
    count = severity_counts[sev]
    percentage = (count / total) * 100
    print(f"  Severity {sev} - {label}: {count} ({percentage:.1f}%)")

print()
print("=" * 70)

# High/low confidence breakdown
high_conf = [r for r in results if r['confidence'] >= 0.85]
low_conf = [r for r in results if r['confidence'] < 0.60]

print(f"High Confidence (>= 0.85): {len(high_conf)} cases ({len(high_conf)/total*100:.1f}%)")
print(f"Low Confidence (< 0.60): {len(low_conf)} cases ({len(low_conf)/total*100:.1f}%)")
print()

# Show low confidence cases
if low_conf:
    print("Low Confidence Cases (may need manual review):")
    print("-" * 70)
    for r in low_conf[:10]:
        print(f"  {r['case_id']}")
        print(f"    Severity: {r['severity_stage']}, Confidence: {r['confidence']}")
        print(f"    Reason: {r['root_cause_summary'][:80]}...")
        print()

# Save detailed summary
summary_file = Path("classification_summary.txt")
with open(summary_file, 'w', encoding='utf-8') as f:
    f.write("=" * 70 + "\n")
    f.write("5G gNB/OAI Log Analysis - Detailed Summary\n")
    f.write("=" * 70 + "\n\n")
    f.write(f"Total files analyzed: {total}\n\n")
    
    f.write("Severity Distribution:\n")
    f.write("-" * 70 + "\n")
    for sev in sorted(severity_counts.keys()):
        label = severity_labels.get(sev, f"Unknown ({sev})")
        count = severity_counts[sev]
        percentage = (count / total) * 100
        f.write(f"  Severity {sev} - {label}: {count} ({percentage:.1f}%)\n")
    
    f.write("\n" + "=" * 70 + "\n\n")
    f.write(f"High Confidence (>= 0.85): {len(high_conf)} cases\n")
    f.write(f"Low Confidence (< 0.60): {len(low_conf)} cases\n\n")
    
    if low_conf:
        f.write("Cases requiring manual review (low confidence):\n")
        f.write("-" * 70 + "\n")
        for r in low_conf:
            f.write(f"\n{r['case_id']}\n")
            f.write(f"  Severity: {r['severity_stage']}, Confidence: {r['confidence']}\n")
            f.write(f"  Component: {r['component']}\n")
            f.write(f"  Summary: {r['root_cause_summary']}\n")
            f.write(f"  Evidence: {', '.join(r['evidence_keywords'][:3])}\n")

print(f"Detailed summary saved to: {summary_file}")
