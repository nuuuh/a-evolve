#!/usr/bin/env python3
"""
Per-batch comparison between H1 baseline and Structured Evolution on FutureX benchmark.
"""

import json
from collections import defaultdict
from datetime import datetime

# Load results
with open('/home/ec2-user/A-EVOLVE-V2/a-evolve/results/futurex_smoke_structured_evo/results.json', 'r') as f:
    evo_results = json.load(f)

with open('/home/ec2-user/A-EVOLVE-V2/a-evolve/results/futurex_smoke_full_evo_v2baseline/results.json', 'r') as f:
    h1_results = json.load(f)

# Load H1 history
with open('/home/ec2-user/A-EVOLVE-V2/a-evolve/results/futurex_smoke_full_evo_v2baseline/history.jsonl', 'r') as f:
    h1_history = [json.loads(line) for line in f if line.strip()]

# Build lookup dictionaries
evo_by_id = {task['instance_id']: task for task in evo_results}
h1_by_id = {task['instance_id']: task for task in h1_results}

# Verify same task set
evo_ids = set(evo_by_id.keys())
h1_ids = set(h1_by_id.keys())
assert evo_ids == h1_ids, f"Task sets differ: {len(evo_ids)} vs {len(h1_ids)}"

print(f"Total tasks: {len(evo_ids)}\n")

# Group by batch
batches = defaultdict(list)
for task_id, task in evo_by_id.items():
    batch_num = task['batch_num']
    batches[batch_num].append(task_id)

# Sort batches
batch_nums = sorted(batches.keys())

print("=" * 120)
print("PER-BATCH COMPARISON: H1 vs Structured Evolution")
print("=" * 120)
print()

# Per-batch analysis
cumulative_h1_correct = 0
cumulative_evo_correct = 0
cumulative_total = 0

all_batch_data = []

for batch_num in batch_nums:
    task_ids = sorted(batches[batch_num])  # Sort by instance_id

    # Get date range (extract from instance_id format: futurex_past_XXXX_YYYYMMDD)
    dates = []
    for tid in task_ids:
        try:
            # Extract date from instance_id like "futurex_past_0023_20260110"
            parts = tid.split('_')
            if len(parts) >= 4:
                date_str = parts[-1]  # Last part should be YYYYMMDD
                if len(date_str) == 8 and date_str.isdigit():
                    year = int(date_str[0:4])
                    month = int(date_str[4:6])
                    day = int(date_str[6:8])
                    dates.append(datetime(year, month, day))
        except:
            pass

    date_range = ""
    if dates:
        dates.sort()
        date_range = f"{dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}"

    # Score calculation
    h1_correct = sum(1 for tid in task_ids if h1_by_id[tid].get('success', False))
    evo_correct = sum(1 for tid in task_ids if evo_by_id[tid].get('success', False))

    h1_score = h1_correct / len(task_ids) if task_ids else 0
    evo_score = evo_correct / len(task_ids) if task_ids else 0

    cumulative_h1_correct += h1_correct
    cumulative_evo_correct += evo_correct
    cumulative_total += len(task_ids)

    cumulative_h1_acc = cumulative_h1_correct / cumulative_total
    cumulative_evo_acc = cumulative_evo_correct / cumulative_total

    # Find gained/lost tasks
    h1_passed = {tid for tid in task_ids if h1_by_id[tid].get('success', False)}
    evo_passed = {tid for tid in task_ids if evo_by_id[tid].get('success', False)}

    gained = evo_passed - h1_passed  # Tasks that Evo solved but H1 didn't
    lost = h1_passed - evo_passed    # Tasks that H1 solved but Evo didn't
    both = h1_passed & evo_passed     # Tasks both solved

    all_batch_data.append({
        'batch_num': batch_num,
        'date_range': date_range,
        'n_tasks': len(task_ids),
        'h1_score': h1_score,
        'evo_score': evo_score,
        'h1_correct': h1_correct,
        'evo_correct': evo_correct,
        'gained': gained,
        'lost': lost,
        'both': both,
        'cumulative_h1_acc': cumulative_h1_acc,
        'cumulative_evo_acc': cumulative_evo_acc,
    })

    print(f"BATCH {batch_num} ({len(task_ids)} tasks)")
    print(f"  Date range: {date_range}")
    print(f"  H1 score:  {h1_score:.2%} ({h1_correct}/{len(task_ids)})")
    print(f"  Evo score: {evo_score:.2%} ({evo_correct}/{len(task_ids)})")
    print(f"  Delta:     {(evo_score - h1_score):+.2%}")
    print(f"  Both correct: {len(both)}")
    print(f"  Gained (Evo only): {len(gained)}")
    if gained:
        for tid in sorted(gained):
            print(f"    + {tid}")
    print(f"  Lost (H1 only): {len(lost)}")
    if lost:
        for tid in sorted(lost):
            print(f"    - {tid}")
    print()

print("=" * 120)
print("CUMULATIVE ACCURACY CURVES")
print("=" * 120)
print()
print(f"{'After Batch':<15} {'H1 Accuracy':<15} {'Evo Accuracy':<15} {'Delta':<15} {'H1 Correct':<15} {'Evo Correct':<15} {'Total':<10}")
print("-" * 120)

for data in all_batch_data:
    print(f"{data['batch_num']:<15} {data['cumulative_h1_acc']:<15.2%} {data['cumulative_evo_acc']:<15.2%} {(data['cumulative_evo_acc'] - data['cumulative_h1_acc']):+<15.2%} {cumulative_h1_correct if data['batch_num'] == all_batch_data[-1]['batch_num'] else sum(all_batch_data[i]['h1_correct'] for i in range(data['batch_num'])):<15} {cumulative_evo_correct if data['batch_num'] == all_batch_data[-1]['batch_num'] else sum(all_batch_data[i]['evo_correct'] for i in range(data['batch_num'])):<15} {sum(all_batch_data[i]['n_tasks'] for i in range(data['batch_num'])):<10}")

# Recalculate cumulative correctly
cumulative_h1 = 0
cumulative_evo = 0
cumulative_tot = 0
print()
print("(Recalculated cumulative table)")
print(f"{'After Batch':<15} {'H1 Accuracy':<15} {'Evo Accuracy':<15} {'Delta':<15} {'H1 Correct':<15} {'Evo Correct':<15} {'Total':<10}")
print("-" * 120)
for data in all_batch_data:
    cumulative_h1 += data['h1_correct']
    cumulative_evo += data['evo_correct']
    cumulative_tot += data['n_tasks']
    h1_acc = cumulative_h1 / cumulative_tot
    evo_acc = cumulative_evo / cumulative_tot
    print(f"{data['batch_num']:<15} {h1_acc:<15.2%} {evo_acc:<15.2%} {(evo_acc - h1_acc):+<15.2%} {cumulative_h1:<15} {cumulative_evo:<15} {cumulative_tot:<10}")

print()
print("=" * 120)
print("H1 EVOLUTION TRAJECTORY")
print("=" * 120)
print()
print(f"{'Cycle':<8} {'Batch':<8} {'Batch Score':<15} {'Batch Passed':<15} {'Cumulative Acc':<20} {'Mutated':<10} {'Evolution Time (s)':<20}")
print("-" * 120)

for entry in h1_history:
    if entry:
        cum_acc = entry['cumulative_passed'] / entry['cumulative_total'] if entry['cumulative_total'] > 0 else 0
        print(f"{entry['cycle']:<8} {entry['batch_num']:<8} {entry['batch_score']:<15.2%} {entry['batch_passed']}/{entry['batch_total']:<10} {cum_acc:<20.2%} {str(entry['mutated']):<10} {entry['evo_elapsed']:<20.1f}")

print()
print("=" * 120)
print("SUMMARY STATISTICS")
print("=" * 120)
print()
print(f"Overall H1 accuracy:  {cumulative_h1_correct / cumulative_total:.2%} ({cumulative_h1_correct}/{cumulative_total})")
print(f"Overall Evo accuracy: {cumulative_evo_correct / cumulative_total:.2%} ({cumulative_evo_correct}/{cumulative_total})")
print(f"Overall delta:        {(cumulative_evo_correct - cumulative_h1_correct) / cumulative_total:+.2%} ({cumulative_evo_correct - cumulative_h1_correct:+d} tasks)")
print()

# Date-based analysis
print("=" * 120)
print("DATE RANGE ANALYSIS")
print("=" * 120)
print()

# Group batches into time periods
early_batches = [1, 2, 3]  # First third
mid_batches = [4, 5, 6]     # Middle third
late_batches = [7, 8, 9]    # Last third

def analyze_period(name, batch_list):
    h1_cor = sum(all_batch_data[b-1]['h1_correct'] for b in batch_list if b <= len(all_batch_data))
    evo_cor = sum(all_batch_data[b-1]['evo_correct'] for b in batch_list if b <= len(all_batch_data))
    total = sum(all_batch_data[b-1]['n_tasks'] for b in batch_list if b <= len(all_batch_data))

    if total > 0:
        print(f"{name}:")
        print(f"  H1:  {h1_cor / total:.2%} ({h1_cor}/{total})")
        print(f"  Evo: {evo_cor / total:.2%} ({evo_cor}/{total})")
        print(f"  Delta: {(evo_cor - h1_cor) / total:+.2%}")
        print()

analyze_period("Early period (batches 1-3)", early_batches)
analyze_period("Mid period (batches 4-6)", mid_batches)
analyze_period("Late period (batches 7-9)", late_batches)

# Divergence analysis
print("=" * 120)
print("DIVERGENCE ANALYSIS")
print("=" * 120)
print()

best_h1_batch = max(all_batch_data, key=lambda x: x['h1_score'])
best_evo_batch = max(all_batch_data, key=lambda x: x['evo_score'])
largest_gap_batch = max(all_batch_data, key=lambda x: abs(x['evo_score'] - x['h1_score']))

print(f"H1 best batch: Batch {best_h1_batch['batch_num']} with {best_h1_batch['h1_score']:.2%}")
print(f"Evo best batch: Batch {best_evo_batch['batch_num']} with {best_evo_batch['evo_score']:.2%}")
print(f"Largest gap: Batch {largest_gap_batch['batch_num']} with {abs(largest_gap_batch['evo_score'] - largest_gap_batch['h1_score']):.2%} difference")
print()

# Find where cumulative curves diverge most
max_divergence = 0
max_divergence_batch = 0
for data in all_batch_data:
    div = abs(data['cumulative_evo_acc'] - data['cumulative_h1_acc'])
    if div > max_divergence:
        max_divergence = div
        max_divergence_batch = data['batch_num']

print(f"Maximum cumulative divergence: {max_divergence:.2%} after batch {max_divergence_batch}")
print()

# Check if structured evolution is consistently better or worse
evo_better_count = sum(1 for data in all_batch_data if data['evo_score'] > data['h1_score'])
h1_better_count = sum(1 for data in all_batch_data if data['h1_score'] > data['evo_score'])
tied_count = sum(1 for data in all_batch_data if data['h1_score'] == data['evo_score'])

print(f"Batches where Evo > H1: {evo_better_count}/{len(all_batch_data)}")
print(f"Batches where H1 > Evo: {h1_better_count}/{len(all_batch_data)}")
print(f"Tied batches: {tied_count}/{len(all_batch_data)}")
print()

print("=" * 120)
print("KEY FINDINGS")
print("=" * 120)
print()

# Key finding 1: Overall comparison
if cumulative_evo_correct > cumulative_h1_correct:
    print(f"1. Structured Evolution outperforms H1 baseline overall by {(cumulative_evo_correct - cumulative_h1_correct) / cumulative_total:.2%}")
elif cumulative_evo_correct < cumulative_h1_correct:
    print(f"1. H1 baseline outperforms Structured Evolution overall by {(cumulative_h1_correct - cumulative_evo_correct) / cumulative_total:.2%}")
else:
    print("1. Structured Evolution and H1 baseline achieve identical overall accuracy")

# Key finding 2: Evolution trajectory
h1_batch_scores = [entry['batch_score'] for entry in h1_history]
if len(h1_batch_scores) >= 3:
    early_avg = sum(h1_batch_scores[:3]) / 3
    late_avg = sum(h1_batch_scores[-3:]) / 3
    if late_avg > early_avg:
        print(f"2. H1's evolution shows improvement over time: early {early_avg:.2%} -> late {late_avg:.2%}")
    else:
        print(f"2. H1's evolution does not show clear improvement: early {early_avg:.2%} -> late {late_avg:.2%}")

# Key finding 3: Where divergence happens
print(f"3. Maximum batch-level divergence occurs at batch {largest_gap_batch['batch_num']}")
print(f"4. Maximum cumulative divergence occurs after batch {max_divergence_batch}")

# Key finding 5: Consistency
if evo_better_count > h1_better_count:
    print(f"5. Structured Evolution is more consistently strong, winning {evo_better_count}/{len(all_batch_data)} batches")
elif h1_better_count > evo_better_count:
    print(f"5. H1 is more consistently strong, winning {h1_better_count}/{len(all_batch_data)} batches")
else:
    print(f"5. Both systems show similar consistency")

print()
