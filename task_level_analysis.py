#!/usr/bin/env python3
"""
Task-level detailed analysis of where H1 and Structured Evolution differ.
"""

import json
from collections import defaultdict
from datetime import datetime

# Load results
with open('/home/ec2-user/A-EVOLVE-V2/a-evolve/results/futurex_smoke_structured_evo/results.json', 'r') as f:
    evo_results = json.load(f)

with open('/home/ec2-user/A-EVOLVE-V2/a-evolve/results/futurex_smoke_full_evo_v2baseline/results.json', 'r') as f:
    h1_results = json.load(f)

# Build lookup dictionaries
evo_by_id = {task['instance_id']: task for task in evo_results}
h1_by_id = {task['instance_id']: task for task in h1_results}

# Group by batch
batches = defaultdict(list)
for task_id, task in evo_by_id.items():
    batch_num = task['batch_num']
    batches[batch_num].append(task_id)

batch_nums = sorted(batches.keys())

print("=" * 160)
print("TASK-LEVEL DETAILED COMPARISON: WHERE DO H1 AND STRUCTURED EVOLUTION DIFFER?")
print("=" * 160)
print()

# Collect all differing tasks
all_gained = []
all_lost = []
all_both = []

for batch_num in batch_nums:
    task_ids = sorted(batches[batch_num])

    h1_passed = {tid for tid in task_ids if h1_by_id[tid].get('success', False)}
    evo_passed = {tid for tid in task_ids if evo_by_id[tid].get('success', False)}

    gained = evo_passed - h1_passed  # Evo solved, H1 didn't
    lost = h1_passed - evo_passed    # H1 solved, Evo didn't
    both = h1_passed & evo_passed     # Both solved

    for tid in gained:
        all_gained.append({
            'task_id': tid,
            'batch_num': batch_num,
            'evo_score': evo_by_id[tid].get('score', 0),
            'h1_score': h1_by_id[tid].get('score', 0),
            'evo_turns': evo_by_id[tid].get('turns', 0),
            'h1_turns': h1_by_id[tid].get('turns', 0),
            'evo_elapsed': evo_by_id[tid].get('elapsed', 0),
            'h1_elapsed': h1_by_id[tid].get('elapsed', 0),
        })

    for tid in lost:
        all_lost.append({
            'task_id': tid,
            'batch_num': batch_num,
            'evo_score': evo_by_id[tid].get('score', 0),
            'h1_score': h1_by_id[tid].get('score', 0),
            'evo_turns': evo_by_id[tid].get('turns', 0),
            'h1_turns': h1_by_id[tid].get('turns', 0),
            'evo_elapsed': evo_by_id[tid].get('elapsed', 0),
            'h1_elapsed': h1_by_id[tid].get('elapsed', 0),
        })

    for tid in both:
        all_both.append({
            'task_id': tid,
            'batch_num': batch_num,
        })

print(f"Total tasks: {len(evo_by_id)}")
print(f"Both systems solved: {len(all_both)}")
print(f"Only Structured Evo solved: {len(all_gained)}")
print(f"Only H1 solved: {len(all_lost)}")
print(f"Neither solved: {len(evo_by_id) - len(all_both) - len(all_gained) - len(all_lost)}")
print()

# Detailed breakdown of gained tasks
if all_gained:
    print("=" * 160)
    print(f"TASKS GAINED BY STRUCTURED EVOLUTION (n={len(all_gained)})")
    print("=" * 160)
    print()
    print("┌" + "─" * 158 + "┐")
    print("│" + " " * 60 + "Tasks where Structured Evolution succeeded but H1 failed" + " " * 41 + "│")
    print("├" + "─" * 7 + "┬" + "─" * 40 + "┬" + "─" * 12 + "┬" + "─" * 12 + "┬" + "─" * 18 + "┬" + "─" * 18 + "┬" + "─" * 18 + "┬" + "─" * 18 + "┬" + "─" * 10 + "┤")
    print(f"│ {'Batch':<6}│ {'Task ID':<39}│ {'Evo Score':<11}│ {'H1 Score':<11}│ {'Evo Turns':<17}│ {'H1 Turns':<17}│ {'Evo Time (s)':<17}│ {'H1 Time (s)':<17}│ {'Date':<9}│")
    print("├" + "─" * 7 + "┼" + "─" * 40 + "┼" + "─" * 12 + "┼" + "─" * 12 + "┼" + "─" * 18 + "┼" + "─" * 18 + "┼" + "─" * 18 + "┼" + "─" * 18 + "┼" + "─" * 10 + "┤")

    for task in sorted(all_gained, key=lambda x: (x['batch_num'], x['task_id'])):
        # Extract date
        parts = task['task_id'].split('_')
        date_str = ""
        if len(parts) >= 4:
            date_part = parts[-1]
            if len(date_part) == 8 and date_part.isdigit():
                date_str = f"{date_part[4:6]}/{date_part[6:8]}"

        print(f"│ {task['batch_num']:<6}│ {task['task_id']:<39}│ {task['evo_score']:<11.2f}│ {task['h1_score']:<11.2f}│ {task['evo_turns']:<17}│ {task['h1_turns']:<17}│ {task['evo_elapsed']:<17.1f}│ {task['h1_elapsed']:<17.1f}│ {date_str:<9}│")

    print("└" + "─" * 7 + "┴" + "─" * 40 + "┴" + "─" * 12 + "┴" + "─" * 12 + "┴" + "─" * 18 + "┴" + "─" * 18 + "┴" + "─" * 18 + "┴" + "─" * 18 + "┴" + "─" * 10 + "┘")
    print()

# Detailed breakdown of lost tasks
if all_lost:
    print("=" * 160)
    print(f"TASKS LOST BY STRUCTURED EVOLUTION (n={len(all_lost)})")
    print("=" * 160)
    print()
    print("┌" + "─" * 158 + "┐")
    print("│" + " " * 60 + "Tasks where H1 succeeded but Structured Evolution failed" + " " * 41 + "│")
    print("├" + "─" * 7 + "┬" + "─" * 40 + "┬" + "─" * 12 + "┬" + "─" * 12 + "┬" + "─" * 18 + "┬" + "─" * 18 + "┬" + "─" * 18 + "┬" + "─" * 18 + "┬" + "─" * 10 + "┤")
    print(f"│ {'Batch':<6}│ {'Task ID':<39}│ {'Evo Score':<11}│ {'H1 Score':<11}│ {'Evo Turns':<17}│ {'H1 Turns':<17}│ {'Evo Time (s)':<17}│ {'H1 Time (s)':<17}│ {'Date':<9}│")
    print("├" + "─" * 7 + "┼" + "─" * 40 + "┼" + "─" * 12 + "┼" + "─" * 12 + "┼" + "─" * 18 + "┼" + "─" * 18 + "┼" + "─" * 18 + "┼" + "─" * 18 + "┼" + "─" * 10 + "┤")

    for task in sorted(all_lost, key=lambda x: (x['batch_num'], x['task_id'])):
        # Extract date
        parts = task['task_id'].split('_')
        date_str = ""
        if len(parts) >= 4:
            date_part = parts[-1]
            if len(date_part) == 8 and date_part.isdigit():
                date_str = f"{date_part[4:6]}/{date_part[6:8]}"

        print(f"│ {task['batch_num']:<6}│ {task['task_id']:<39}│ {task['evo_score']:<11.2f}│ {task['h1_score']:<11.2f}│ {task['evo_turns']:<17}│ {task['h1_turns']:<17}│ {task['evo_elapsed']:<17.1f}│ {task['h1_elapsed']:<17.1f}│ {date_str:<9}│")

    print("└" + "─" * 7 + "┴" + "─" * 40 + "┴" + "─" * 12 + "┴" + "─" * 12 + "┴" + "─" * 18 + "┴" + "─" * 18 + "┴" + "─" * 18 + "┴" + "─" * 18 + "┴" + "─" * 10 + "┘")
    print()

# Summary stats
print("=" * 160)
print("SUMMARY STATISTICS ON DIFFERENCES")
print("=" * 160)
print()

if all_gained:
    avg_evo_turns_gained = sum(t['evo_turns'] for t in all_gained) / len(all_gained)
    avg_h1_turns_gained = sum(t['h1_turns'] for t in all_gained) / len(all_gained)
    avg_evo_time_gained = sum(t['evo_elapsed'] for t in all_gained) / len(all_gained)
    avg_h1_time_gained = sum(t['h1_elapsed'] for t in all_gained) / len(all_gained)

    print(f"Tasks gained by Structured Evolution (n={len(all_gained)}):")
    print(f"  Average turns: Evo = {avg_evo_turns_gained:.1f}, H1 = {avg_h1_turns_gained:.1f}")
    print(f"  Average time: Evo = {avg_evo_time_gained:.1f}s, H1 = {avg_h1_time_gained:.1f}s")
    print()

if all_lost:
    avg_evo_turns_lost = sum(t['evo_turns'] for t in all_lost) / len(all_lost)
    avg_h1_turns_lost = sum(t['h1_turns'] for t in all_lost) / len(all_lost)
    avg_evo_time_lost = sum(t['evo_elapsed'] for t in all_lost) / len(all_lost)
    avg_h1_time_lost = sum(t['h1_elapsed'] for t in all_lost) / len(all_lost)

    print(f"Tasks lost by Structured Evolution (n={len(all_lost)}):")
    print(f"  Average turns: Evo = {avg_evo_turns_lost:.1f}, H1 = {avg_h1_turns_lost:.1f}")
    print(f"  Average time: Evo = {avg_evo_time_lost:.1f}s, H1 = {avg_h1_time_lost:.1f}s")
    print()

# Per-batch breakdown
print("=" * 160)
print("PER-BATCH GAIN/LOSS BREAKDOWN")
print("=" * 160)
print()

print("┌" + "─" * 158 + "┐")
print("│" + " " * 60 + "Task-level changes per batch" + " " * 68 + "│")
print("├" + "─" * 10 + "┬" + "─" * 20 + "┬" + "─" * 20 + "┬" + "─" * 20 + "┬" + "─" * 30 + "┬" + "─" * 30 + "┬" + "─" * 25 + "┤")
print(f"│ {'Batch':<9}│ {'Tasks in Batch':<19}│ {'Both Correct':<19}│ {'Gained by Evo':<19}│ {'Lost by Evo':<29}│ {'Net Change':<29}│ {'Interpretation':<24}│")
print("├" + "─" * 10 + "┼" + "─" * 20 + "┼" + "─" * 20 + "┼" + "─" * 20 + "┼" + "─" * 30 + "┼" + "─" * 30 + "┼" + "─" * 25 + "┤")

for batch_num in batch_nums:
    task_ids = sorted(batches[batch_num])

    h1_passed = {tid for tid in task_ids if h1_by_id[tid].get('success', False)}
    evo_passed = {tid for tid in task_ids if evo_by_id[tid].get('success', False)}

    gained = len(evo_passed - h1_passed)
    lost = len(h1_passed - evo_passed)
    both = len(h1_passed & evo_passed)
    net = gained - lost

    if net > 0:
        interp = "Evo advantage"
    elif net < 0:
        interp = "H1 advantage"
    else:
        interp = "Neutral"

    print(f"│ {batch_num:<9}│ {len(task_ids):<19}│ {both:<19}│ {gained:<19}│ {lost:<29}│ {net:+d} ({net/len(task_ids):+.1%}){'':>14}│ {interp:<24}│")

print("└" + "─" * 10 + "┴" + "─" * 20 + "┴" + "─" * 20 + "┴" + "─" * 20 + "┴" + "─" * 30 + "┴" + "─" * 30 + "┴" + "─" * 25 + "┘")

print()
print("=" * 160)
