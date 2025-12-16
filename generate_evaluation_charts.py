#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate evaluation charts for the report
"""

import matplotlib.pyplot as plt
import numpy as np
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica']
matplotlib.rcParams['axes.unicode_minus'] = False

# Evaluation data
tasks = ['Task 1\n(Keyword\nCombination)', 'Task 2\n(Price & Tag\nFiltering)', 'Task 3\n(Cross-Language\nSemantic)']
evaluators = ['Evaluator 1', 'Evaluator 2', 'Evaluator 3']

# Scores: [Task1, Task2, Task3] for each evaluator
scores = {
    'Evaluator 1': [4, 5, 4],
    'Evaluator 2': [5, 5, 4],
    'Evaluator 3': [4, 5, 4]
}

# Calculate averages
task_averages = [
    np.mean([scores[e][0] for e in evaluators]),  # Task 1 average
    np.mean([scores[e][1] for e in evaluators]),  # Task 2 average
    np.mean([scores[e][2] for e in evaluators])  # Task 3 average
]

overall_average = np.mean([score for evaluator_scores in scores.values() for score in evaluator_scores])

# Create figure with subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Chart 1: Bar chart showing scores by evaluator and task
x = np.arange(len(tasks))
width = 0.25
multiplier = 0

colors = ['#667eea', '#764ba2', '#ff6b6b']

for i, evaluator in enumerate(evaluators):
    offset = width * multiplier
    bars = ax1.bar(x + offset, scores[evaluator], width, label=evaluator, color=colors[i], alpha=0.8)
    ax1.bar_label(bars, padding=3)
    multiplier += 1

ax1.set_xlabel('Task', fontsize=12, fontweight='bold')
ax1.set_ylabel('Performance Score (1-5)', fontsize=12, fontweight='bold')
ax1.set_title('System Performance Scores by Task and Evaluator', fontsize=14, fontweight='bold')
ax1.set_xticks(x + width, tasks)
ax1.set_ylim(0, 5.5)
ax1.legend(loc='upper left', frameon=True)
ax1.grid(axis='y', alpha=0.3, linestyle='--')
ax1.axhline(y=5, color='green', linestyle='--', alpha=0.3, label='Perfect Score')
ax1.set_yticks(range(0, 6))

# Chart 2: Average scores per task and overall
categories = tasks + ['Overall\nSystem\nPerformance']
averages = task_averages + [overall_average]
colors_bar = ['#667eea', '#764ba2', '#ff6b6b', '#95e1d3']

bars2 = ax2.bar(categories, averages, color=colors_bar, alpha=0.8, edgecolor='black', linewidth=1.5)
ax2.bar_label(bars2, fmt='%.1f', padding=5, fontweight='bold')

ax2.set_ylabel('Average Performance Score (1-5)', fontsize=12, fontweight='bold')
ax2.set_title('Average System Performance by Task', fontsize=14, fontweight='bold')
ax2.set_ylim(0, 5.5)
ax2.grid(axis='y', alpha=0.3, linestyle='--')
ax2.axhline(y=5, color='green', linestyle='--', alpha=0.3)
ax2.set_yticks(range(0, 6))

plt.tight_layout()
plt.savefig('evaluation_charts.png', dpi=300, bbox_inches='tight')
plt.savefig('evaluation_charts.pdf', bbox_inches='tight')
print("Charts saved as evaluation_charts.png and evaluation_charts.pdf")

# Print summary statistics
print("\n=== Evaluation Summary ===")
print(f"Task 1 Average: {task_averages[0]:.1f}/5")
print(f"Task 2 Average: {task_averages[1]:.1f}/5")
print(f"Task 3 Average: {task_averages[2]:.1f}/5")
print(f"Overall System Performance: {overall_average:.1f}/5")

