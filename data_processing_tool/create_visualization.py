import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import csv

# Read the CSV file
csv_file = r"C:\Users\wasd0\Desktop\Testing_Row_Data\test_case_analysis_results.csv"

# Skip the summary lines and read detailed results
valid_errors = []
with open(csv_file, 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()
    # Find the start of detailed results (after the second header)
    for i, line in enumerate(lines):
        if line.startswith('case_id,filename'):
            data_start = i + 1
            break
    
    reader = csv.DictReader(lines[data_start:], 
                           fieldnames=['case_id', 'filename', 'modified_key', 'error_type', 
                                      'affected_module', 'impact_description', 'is_valid_error', 
                                      'has_pdu_success', 'triggering_score', 'diagnostic_score', 
                                      'consistency_score', 'source_file', 'line_number', 'error_message'])
    
    for row in reader:
        if row['case_id'].strip():  # Skip empty rows
            valid_errors.append(row)

# Extract statistics
total_cases = len(valid_errors)
successful_errors = sum(1 for r in valid_errors if r['is_valid_error'].strip() == 'Yes')
invalid_modifications = sum(1 for r in valid_errors if r['has_pdu_success'].strip() == 'Yes')
other_failed = total_cases - successful_errors - invalid_modifications

# Create figure with multiple subplots
fig = plt.figure(figsize=(16, 10))
fig.suptitle('5G gNB Test Case Analysis - Comprehensive Results', fontsize=16, fontweight='bold')

# 1. Overall Distribution (Pie Chart)
ax1 = plt.subplot(2, 3, 1)
labels = ['Successful Errors\n(Valid)', 'Invalid Modifications\n(PDU Success)', 'Other Failed\nCases']
sizes = [successful_errors, invalid_modifications, other_failed]
colors = ['#2ecc71', '#e74c3c', '#95a5a6']
explode = (0.1, 0, 0)

ax1.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
        shadow=True, startangle=90)
ax1.set_title('Test Case Distribution\n(Total: 100 Cases)', fontweight='bold')

# 2. Module Distribution for Valid Errors (Bar Chart)
ax2 = plt.subplot(2, 3, 2)
valid_error_cases = [r for r in valid_errors if r['is_valid_error'].strip() == 'Yes']
module_counts = {}
for case in valid_error_cases:
    module = case['affected_module'].strip()
    module_counts[module] = module_counts.get(module, 0) + 1

modules = list(module_counts.keys())
counts = list(module_counts.values())
bars = ax2.bar(modules, counts, color=['#3498db', '#9b59b6', '#e67e22', '#1abc9c'])
ax2.set_xlabel('Module', fontweight='bold')
ax2.set_ylabel('Number of Cases', fontweight='bold')
ax2.set_title('Valid Errors by Module\n(14 Total Cases)', fontweight='bold')
ax2.grid(axis='y', alpha=0.3)

# Add value labels on bars
for bar in bars:
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
             f'{int(height)}',
             ha='center', va='bottom', fontweight='bold')

# 3. Error Type Distribution (Bar Chart)
ax3 = plt.subplot(2, 3, 3)
error_type_counts = {}
for case in valid_error_cases:
    error_type = case['error_type'].strip()
    error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1

error_types = list(error_type_counts.keys())
type_counts = list(error_type_counts.values())
bars = ax3.bar(error_types, type_counts, color=['#e74c3c', '#3498db', '#f39c12'])
ax3.set_xlabel('Error Type', fontweight='bold')
ax3.set_ylabel('Number of Cases', fontweight='bold')
ax3.set_title('Valid Errors by Error Type\n(14 Total Cases)', fontweight='bold')
ax3.grid(axis='y', alpha=0.3)
plt.setp(ax3.xaxis.get_majorticklabels(), rotation=15, ha='right')

# Add value labels on bars
for bar in bars:
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2., height,
             f'{int(height)}',
             ha='center', va='bottom', fontweight='bold')

# 4. Average Scores (Horizontal Bar Chart)
ax4 = plt.subplot(2, 3, 4)
triggering_scores = [int(r['triggering_score']) for r in valid_error_cases]
diagnostic_scores = [int(r['diagnostic_score']) for r in valid_error_cases]
consistency_scores = [int(r['consistency_score']) for r in valid_error_cases]

avg_triggering = sum(triggering_scores) / len(triggering_scores)
avg_diagnostic = sum(diagnostic_scores) / len(diagnostic_scores)
avg_consistency = sum(consistency_scores) / len(consistency_scores)

categories = ['Triggering\nPrecision', 'Diagnostic\nTransparency', 'Causal\nConsistency']
scores = [avg_triggering, avg_diagnostic, avg_consistency]
colors_score = ['#3498db', '#e67e22', '#2ecc71']

bars = ax4.barh(categories, scores, color=colors_score)
ax4.set_xlabel('Average Score (out of 5)', fontweight='bold')
ax4.set_xlim(0, 5)
ax4.set_title('Average Scoring Metrics\n(Valid Errors Only)', fontweight='bold')
ax4.grid(axis='x', alpha=0.3)

# Add value labels on bars
for i, (bar, score) in enumerate(zip(bars, scores)):
    ax4.text(score + 0.1, bar.get_y() + bar.get_height()/2.,
             f'{score:.2f}/5.00',
             ha='left', va='center', fontweight='bold')

# 5. Score Distribution Histogram
ax5 = plt.subplot(2, 3, 5)
all_scores = triggering_scores + diagnostic_scores + consistency_scores
ax5.hist([triggering_scores, diagnostic_scores, consistency_scores], 
         bins=range(1, 7), label=categories, alpha=0.7, 
         color=colors_score, edgecolor='black')
ax5.set_xlabel('Score', fontweight='bold')
ax5.set_ylabel('Frequency', fontweight='bold')
ax5.set_title('Score Distribution Across Metrics', fontweight='bold')
ax5.legend()
ax5.grid(axis='y', alpha=0.3)
ax5.set_xticks(range(1, 6))

# 6. Statistics Summary (Text Box)
ax6 = plt.subplot(2, 3, 6)
ax6.axis('off')

summary_text = f"""
ANALYSIS SUMMARY
{'='*40}

Total Test Cases:              {total_cases:>3}
  ✓ Successful Errors:         {successful_errors:>3} ({successful_errors/total_cases*100:.1f}%)
  ✗ Invalid Modifications:     {invalid_modifications:>3} ({invalid_modifications/total_cases*100:.1f}%)
  ⚠ Other Failed Cases:        {other_failed:>3} ({other_failed/total_cases*100:.1f}%)

{'='*40}
VALID ERROR SCORE AVERAGES
{'='*40}

Triggering Precision:      {avg_triggering:.2f} / 5.00
Diagnostic Transparency:   {avg_diagnostic:.2f} / 5.00
Causal Consistency:        {avg_consistency:.2f} / 5.00

{'='*40}
TOP PERFORMING MODULES
{'='*40}
"""

for module, count in sorted(module_counts.items(), key=lambda x: x[1], reverse=True):
    summary_text += f"\n{module:>10}: {count:>2} cases ({count/successful_errors*100:.1f}%)"

ax6.text(0.05, 0.95, summary_text, transform=ax6.transAxes,
         fontsize=10, verticalalignment='top', fontfamily='monospace',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

plt.tight_layout()
plt.savefig(r'C:\Users\wasd0\Desktop\Testing_Row_Data\test_analysis_visualization.png', 
            dpi=300, bbox_inches='tight')
print("Visualization saved to: test_analysis_visualization.png")
print("Image size: 16x10 inches at 300 DPI")
