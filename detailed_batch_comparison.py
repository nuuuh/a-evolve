#!/usr/bin/env python3
"""
Comprehensive per-batch comparison between H1 baseline and Structured Evolution on FutureX benchmark.
"""

import json
from collections import defaultdict
from datetime import datetime

# Load results
with open('/home/ec2-user/A-EVOLVE-V2/a-evolve/results/futurex_smoke_structured_evo/results.json', 'r') as f:
    evo_results = json.load(f)

with open('/home/ec2-user/A-EVOLVE-V2/a-evolve/results/futurex_smoke_full_evo_v2baseline/results.json', 'r') as f:
    h1_results = json.load(f)

# Load histories
with open('/home/ec2-user/A-EVOLVE-V2/a-evolve/results/futurex_smoke_full_evo_v2baseline/history.jsonl', 'r') as f:
    h1_history = [json.loads(line) for line in f if line.strip()]

with open('/home/ec2-user/A-EVOLVE-V2/a-evolve/results/futurex_smoke_structured_evo/history.jsonl', 'r') as f:
    evo_history = [json.loads(line) for line in f if line.strip()]

# Build lookup dictionaries
evo_by_id = {task['instance_id']: task for task in evo_results}
h1_by_id = {task['instance_id']: task for task in h1_results}

print("=" * 140)
print("DETAILED PER-BATCH COMPARISON: H1 BASELINE vs STRUCTURED EVOLUTION")
print("FutureX Benchmark - 84 Tasks (stride 6 from 503)")
print("=" * 140)
print()

# Group by batch
batches = defaultdict(list)
for task_id, task in evo_by_id.items():
    batch_num = task['batch_num']
    batches[batch_num].append(task_id)

batch_nums = sorted(batches.keys())

# Summary table
print("┌" + "─" * 138 + "┐")
print("│" + " " * 50 + "BATCH-BY-BATCH RESULTS SUMMARY" + " " * 57 + "│")
print("├" + "─" * 7 + "┬" + "─" * 22 + "┬" + "─" * 17 + "┬" + "─" * 17 + "┬" + "─" * 12 + "┬" + "─" * 12 + "┬" + "─" * 12 + "┬" + "─" * 12 + "┬" + "─" * 12 + "┬" + "─" * 12 + "┤")
print(f"│ {'Batch':<6}│ {'Date Range':<21}│ {'H1 Score':<16}│ {'Evo Score':<16}│ {'Delta':<11}│ {'Both OK':<11}│ {'Gained':<11}│ {'Lost':<11}│ {'H1 Evo (s)':<11}│ {'Evo Evo (s)':<11}│")
print("├" + "─" * 7 + "┼" + "─" * 22 + "┼" + "─" * 17 + "┼" + "─" * 17 + "┼" + "─" * 12 + "┼" + "─" * 12 + "┼" + "─" * 12 + "┼" + "─" * 12 + "┼" + "─" * 12 + "┼" + "─" * 12 + "┤")

all_batch_data = []
for i, batch_num in enumerate(batch_nums):
    task_ids = sorted(batches[batch_num])

    # Get date range
    dates = []
    for tid in task_ids:
        try:
            parts = tid.split('_')
            if len(parts) >= 4:
                date_str = parts[-1]
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
        date_range = f"{dates[0].strftime('%m/%d')}-{dates[-1].strftime('%m/%d')}"

    # Score calculation
    h1_correct = sum(1 for tid in task_ids if h1_by_id[tid].get('success', False))
    evo_correct = sum(1 for tid in task_ids if evo_by_id[tid].get('success', False))

    h1_score = h1_correct / len(task_ids)
    evo_score = evo_correct / len(task_ids)

    # Find gained/lost
    h1_passed = {tid for tid in task_ids if h1_by_id[tid].get('success', False)}
    evo_passed = {tid for tid in task_ids if evo_by_id[tid].get('success', False)}
    gained = len(evo_passed - h1_passed)
    lost = len(h1_passed - evo_passed)
    both = len(h1_passed & evo_passed)

    # Evolution times
    h1_evo_time = h1_history[i]['evo_elapsed'] if i < len(h1_history) else 0
    evo_evo_time = evo_history[i]['evo_elapsed'] if i < len(evo_history) else 0

    delta = evo_score - h1_score
    delta_str = f"{delta:+.1%}"

    print(f"│ {batch_num:<6}│ {date_range:<21}│ {h1_score:.1%} ({h1_correct}/{len(task_ids)}){'':>6}│ {evo_score:.1%} ({evo_correct}/{len(task_ids)}){'':>6}│ {delta_str:<11}│ {both:<11}│ {gained:<11}│ {lost:<11}│ {h1_evo_time:<11.0f}│ {evo_evo_time:<11.0f}│")

    all_batch_data.append({
        'batch_num': batch_num,
        'date_range': date_range,
        'dates': dates,
        'n_tasks': len(task_ids),
        'h1_score': h1_score,
        'evo_score': evo_score,
        'h1_correct': h1_correct,
        'evo_correct': evo_correct,
        'gained': gained,
        'lost': lost,
        'both': both,
        'h1_evo_time': h1_evo_time,
        'evo_evo_time': evo_evo_time,
    })

# Totals
total_tasks = sum(d['n_tasks'] for d in all_batch_data)
total_h1 = sum(d['h1_correct'] for d in all_batch_data)
total_evo = sum(d['evo_correct'] for d in all_batch_data)
total_h1_time = sum(d['h1_evo_time'] for d in all_batch_data)
total_evo_time = sum(d['evo_evo_time'] for d in all_batch_data)

print("├" + "─" * 7 + "┼" + "─" * 22 + "┼" + "─" * 17 + "┼" + "─" * 17 + "┼" + "─" * 12 + "┼" + "─" * 12 + "┼" + "─" * 12 + "┼" + "─" * 12 + "┼" + "─" * 12 + "┼" + "─" * 12 + "┤")
print(f"│ {'TOTAL':<6}│ {'All dates':<21}│ {total_h1/total_tasks:.1%} ({total_h1}/{total_tasks}){'':>6}│ {total_evo/total_tasks:.1%} ({total_evo}/{total_tasks}){'':>6}│ {(total_evo-total_h1)/total_tasks:+.1%}{'':>6}│ {'-':<11}│ {'-':<11}│ {'-':<11}│ {total_h1_time:<11.0f}│ {total_evo_time:<11.0f}│")
print("└" + "─" * 7 + "┴" + "─" * 22 + "┴" + "─" * 17 + "┴" + "─" * 17 + "┴" + "─" * 12 + "┴" + "─" * 12 + "┴" + "─" * 12 + "┴" + "─" * 12 + "┴" + "─" * 12 + "┴" + "─" * 12 + "┘")

print()
print()

# Cumulative accuracy curves
print("=" * 140)
print("CUMULATIVE ACCURACY TRAJECTORIES")
print("=" * 140)
print()
print("┌" + "─" * 138 + "┐")
print("│" + " " * 50 + "CUMULATIVE RESULTS AFTER EACH BATCH" + " " * 52 + "│")
print("├" + "─" * 15 + "┬" + "─" * 20 + "┬" + "─" * 20 + "┬" + "─" * 15 + "┬" + "─" * 20 + "┬" + "─" * 20 + "┬" + "─" * 15 + "┤")
print(f"│ {'After Batch':<14}│ {'H1 Cumulative':<19}│ {'Evo Cumulative':<19}│ {'Delta':<14}│ {'H1 (n/total)':<19}│ {'Evo (n/total)':<19}│ {'Tasks So Far':<14}│")
print("├" + "─" * 15 + "┼" + "─" * 20 + "┼" + "─" * 20 + "┼" + "─" * 15 + "┼" + "─" * 20 + "┼" + "─" * 20 + "┼" + "─" * 15 + "┤")

cumulative_h1 = 0
cumulative_evo = 0
cumulative_tot = 0
for data in all_batch_data:
    cumulative_h1 += data['h1_correct']
    cumulative_evo += data['evo_correct']
    cumulative_tot += data['n_tasks']
    h1_acc = cumulative_h1 / cumulative_tot
    evo_acc = cumulative_evo / cumulative_tot
    delta = evo_acc - h1_acc

    print(f"│ {data['batch_num']:<14}│ {h1_acc:<19.2%}│ {evo_acc:<19.2%}│ {delta:+<14.2%}│ {cumulative_h1}/{cumulative_tot:<15}│ {cumulative_evo}/{cumulative_tot:<15}│ {cumulative_tot:<14}│")

print("└" + "─" * 15 + "┴" + "─" * 20 + "┴" + "─" * 20 + "┴" + "─" * 15 + "┴" + "─" * 20 + "┴" + "─" * 20 + "┴" + "─" * 15 + "┘")

print()
print()

# Evolution trajectories comparison
print("=" * 140)
print("EVOLUTION SYSTEM COMPARISON")
print("=" * 140)
print()

print("┌" + "─" * 138 + "┐")
print("│" + " " * 57 + "H1 EVOLUTION TRAJECTORY" + " " * 57 + "│")
print("├" + "─" * 10 + "┬" + "─" * 10 + "┬" + "─" * 18 + "┬" + "─" * 18 + "┬" + "─" * 22 + "┬" + "─" * 15 + "┬" + "─" * 20 + "┬" + "─" * 20 + "┤")
print(f"│ {'Cycle':<9}│ {'Batch':<9}│ {'Batch Score':<17}│ {'Batch Correct':<17}│ {'Cumulative Accuracy':<21}│ {'Mutated':<14}│ {'Evolution Time (s)':<19}│ {'Cum. Evo Time (s)':<19}│")
print("├" + "─" * 10 + "┼" + "─" * 10 + "┼" + "─" * 18 + "┼" + "─" * 18 + "┼" + "─" * 22 + "┼" + "─" * 15 + "┼" + "─" * 20 + "┼" + "─" * 20 + "┤")

cum_h1_evo_time = 0
for entry in h1_history:
    if entry:
        cum_acc = entry['cumulative_passed'] / entry['cumulative_total'] if entry['cumulative_total'] > 0 else 0
        cum_h1_evo_time += entry['evo_elapsed']
        print(f"│ {entry['cycle']:<9}│ {entry['batch_num']:<9}│ {entry['batch_score']:<17.1%}│ {entry['batch_passed']}/{entry['batch_total']:<13}│ {cum_acc:<21.2%}│ {str(entry['mutated']):<14}│ {entry['evo_elapsed']:<19.0f}│ {cum_h1_evo_time:<19.0f}│")

print("└" + "─" * 10 + "┴" + "─" * 10 + "┴" + "─" * 18 + "┴" + "─" * 18 + "┴" + "─" * 22 + "┴" + "─" * 15 + "┴" + "─" * 20 + "┴" + "─" * 20 + "┘")

print()

print("┌" + "─" * 138 + "┐")
print("│" + " " * 52 + "STRUCTURED EVOLUTION TRAJECTORY" + " " * 54 + "│")
print("├" + "─" * 10 + "┬" + "─" * 10 + "┬" + "─" * 18 + "┬" + "─" * 18 + "┬" + "─" * 22 + "┬" + "─" * 15 + "┬" + "─" * 20 + "┬" + "─" * 20 + "┤")
print(f"│ {'Cycle':<9}│ {'Batch':<9}│ {'Batch Score':<17}│ {'Batch Correct':<17}│ {'Cumulative Accuracy':<21}│ {'Mutated':<14}│ {'Evolution Time (s)':<19}│ {'Cum. Evo Time (s)':<19}│")
print("├" + "─" * 10 + "┼" + "─" * 10 + "┼" + "─" * 18 + "┼" + "─" * 18 + "┼" + "─" * 22 + "┼" + "─" * 15 + "┼" + "─" * 20 + "┼" + "─" * 20 + "┤")

cum_evo_evo_time = 0
for entry in evo_history:
    if entry:
        cum_acc = entry['cumulative_passed'] / entry['cumulative_total'] if entry['cumulative_total'] > 0 else 0
        cum_evo_evo_time += entry['evo_elapsed']
        print(f"│ {entry['cycle']:<9}│ {entry['batch_num']:<9}│ {entry['batch_score']:<17.1%}│ {entry['batch_passed']}/{entry['batch_total']:<13}│ {cum_acc:<21.2%}│ {str(entry['mutated']):<14}│ {entry['evo_elapsed']:<19.0f}│ {cum_evo_evo_time:<19.0f}│")

print("└" + "─" * 10 + "┴" + "─" * 10 + "┴" + "─" * 18 + "┴" + "─" * 18 + "┴" + "─" * 22 + "┴" + "─" * 15 + "┴" + "─" * 20 + "┴" + "─" * 20 + "┘")

print()
print()

# Date range analysis
print("=" * 140)
print("TIME-BASED PERFORMANCE ANALYSIS")
print("=" * 140)
print()

early_batches = [1, 2, 3]
mid_batches = [4, 5, 6]
late_batches = [7, 8, 9]

def analyze_period(name, batch_list):
    h1_cor = sum(all_batch_data[b-1]['h1_correct'] for b in batch_list if b <= len(all_batch_data))
    evo_cor = sum(all_batch_data[b-1]['evo_correct'] for b in batch_list if b <= len(all_batch_data))
    total = sum(all_batch_data[b-1]['n_tasks'] for b in batch_list if b <= len(all_batch_data))

    dates = []
    for b in batch_list:
        if b <= len(all_batch_data):
            dates.extend(all_batch_data[b-1].get('dates', []))

    date_range = ""
    if dates:
        dates.sort()
        date_range = f"{dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}"

    return {
        'name': name,
        'date_range': date_range,
        'h1': (h1_cor, total),
        'evo': (evo_cor, total),
        'delta': (evo_cor - h1_cor, total)
    }

periods = [
    analyze_period("Early (Batches 1-3)", early_batches),
    analyze_period("Mid (Batches 4-6)", mid_batches),
    analyze_period("Late (Batches 7-9)", late_batches),
]

print("┌" + "─" * 138 + "┐")
print("│" + " " * 52 + "PERFORMANCE BY TIME PERIOD" + " " * 59 + "│")
print("├" + "─" * 25 + "┬" + "─" * 35 + "┬" + "─" * 20 + "┬" + "─" * 20 + "┬" + "─" * 20 + "┬" + "─" * 15 + "┤")
print(f"│ {'Period':<24}│ {'Date Range':<34}│ {'H1 Accuracy':<19}│ {'Evo Accuracy':<19}│ {'Delta':<19}│ {'Winner':<14}│")
print("├" + "─" * 25 + "┼" + "─" * 35 + "┼" + "─" * 20 + "┼" + "─" * 20 + "┼" + "─" * 20 + "┼" + "─" * 15 + "┤")

for p in periods:
    h1_acc = p['h1'][0] / p['h1'][1] if p['h1'][1] > 0 else 0
    evo_acc = p['evo'][0] / p['evo'][1] if p['evo'][1] > 0 else 0
    delta = evo_acc - h1_acc

    if delta > 0.01:
        winner = "Evo"
    elif delta < -0.01:
        winner = "H1"
    else:
        winner = "Tie"

    print(f"│ {p['name']:<24}│ {p['date_range']:<34}│ {h1_acc:.1%} ({p['h1'][0]}/{p['h1'][1]}){'':>8}│ {evo_acc:.1%} ({p['evo'][0]}/{p['evo'][1]}){'':>8}│ {delta:+.1%}{'':>14}│ {winner:<14}│")

print("└" + "─" * 25 + "┴" + "─" * 35 + "┴" + "─" * 20 + "┴" + "─" * 20 + "┴" + "─" * 20 + "┴" + "─" * 15 + "┘")

print()
print()

# Key findings
print("=" * 140)
print("KEY FINDINGS & ANALYSIS")
print("=" * 140)
print()

findings = []

# Finding 1: Overall winner
findings.append(f"1. OVERALL PERFORMANCE:")
findings.append(f"   - Structured Evolution: {total_evo}/{total_tasks} = {total_evo/total_tasks:.2%}")
findings.append(f"   - H1 Baseline: {total_h1}/{total_tasks} = {total_h1/total_tasks:.2%}")
findings.append(f"   - Advantage: Structured Evolution by {(total_evo-total_h1)/total_tasks:+.2%} ({total_evo-total_h1:+d} tasks)")
findings.append("")

# Finding 2: Batch-level wins
evo_better = sum(1 for d in all_batch_data if d['evo_score'] > d['h1_score'])
h1_better = sum(1 for d in all_batch_data if d['h1_score'] > d['evo_score'])
tied = sum(1 for d in all_batch_data if d['h1_score'] == d['evo_score'])
findings.append(f"2. BATCH-LEVEL CONSISTENCY:")
findings.append(f"   - Structured Evolution wins: {evo_better}/{len(all_batch_data)} batches")
findings.append(f"   - H1 wins: {h1_better}/{len(all_batch_data)} batches")
findings.append(f"   - Tied: {tied}/{len(all_batch_data)} batches")
findings.append("")

# Finding 3: Divergence point
max_div_batch = max(all_batch_data, key=lambda x: abs(x['evo_score'] - x['h1_score']))
findings.append(f"3. MAXIMUM DIVERGENCE:")
findings.append(f"   - Occurs at Batch {max_div_batch['batch_num']}")
findings.append(f"   - Gap: {abs(max_div_batch['evo_score'] - max_div_batch['h1_score']):.1%}")
findings.append(f"   - Winner: {'Structured Evolution' if max_div_batch['evo_score'] > max_div_batch['h1_score'] else 'H1'}")
findings.append("")

# Finding 4: Evolution trends
h1_batch_scores = [h['batch_score'] for h in h1_history]
evo_batch_scores = [e['batch_score'] for e in evo_history]
h1_early_avg = sum(h1_batch_scores[:3]) / 3 if len(h1_batch_scores) >= 3 else 0
h1_late_avg = sum(h1_batch_scores[-3:]) / 3 if len(h1_batch_scores) >= 3 else 0
evo_early_avg = sum(evo_batch_scores[:3]) / 3 if len(evo_batch_scores) >= 3 else 0
evo_late_avg = sum(evo_batch_scores[-3:]) / 3 if len(evo_batch_scores) >= 3 else 0

findings.append(f"4. EVOLUTION TRAJECTORIES:")
findings.append(f"   - H1: {h1_early_avg:.1%} (early) → {h1_late_avg:.1%} (late) = {h1_late_avg - h1_early_avg:+.1%} change")
findings.append(f"   - Structured Evo: {evo_early_avg:.1%} (early) → {evo_late_avg:.1%} (late) = {evo_late_avg - evo_early_avg:+.1%} change")
if h1_late_avg > h1_early_avg:
    findings.append(f"   - H1 shows improvement over time (tools evolving positively)")
else:
    findings.append(f"   - H1 shows degradation over time (tools may not be generalizing)")
if evo_late_avg > evo_early_avg:
    findings.append(f"   - Structured Evo shows improvement over time")
else:
    findings.append(f"   - Structured Evo shows degradation over time")
findings.append("")

# Finding 5: Time period winner
findings.append(f"5. TIME-BASED PATTERNS:")
for p in periods:
    h1_acc = p['h1'][0] / p['h1'][1]
    evo_acc = p['evo'][0] / p['evo'][1]
    delta = evo_acc - h1_acc
    winner = "Structured Evo" if delta > 0 else "H1" if delta < 0 else "Tied"
    findings.append(f"   - {p['name']}: {winner} (Δ = {delta:+.1%})")
findings.append("")

# Finding 6: Evolution overhead
findings.append(f"6. EVOLUTION OVERHEAD:")
findings.append(f"   - H1 total evolution time: {total_h1_time:.0f}s = {total_h1_time/60:.1f} minutes")
findings.append(f"   - Structured Evo total time: {total_evo_time:.0f}s = {total_evo_time/60:.1f} minutes")
findings.append(f"   - Ratio: {total_evo_time/total_h1_time:.2f}x (Structured Evo takes {total_evo_time/total_h1_time:.1f}x longer per evolution)")
findings.append(f"   - Per-batch average:")
findings.append(f"     * H1: {total_h1_time/len(all_batch_data):.0f}s")
findings.append(f"     * Structured Evo: {total_evo_time/len(all_batch_data):.0f}s")
findings.append("")

# Finding 7: When divergence appears
cumulative_deltas = []
cum_h1 = 0
cum_evo = 0
cum_tot = 0
for data in all_batch_data:
    cum_h1 += data['h1_correct']
    cum_evo += data['evo_correct']
    cum_tot += data['n_tasks']
    cumulative_deltas.append((data['batch_num'], (cum_evo - cum_h1) / cum_tot))

max_cum_delta_batch, max_cum_delta = max(cumulative_deltas, key=lambda x: abs(x[1]))
findings.append(f"7. CUMULATIVE DIVERGENCE PATTERN:")
findings.append(f"   - Initial gap (after batch 1): {cumulative_deltas[0][1]:+.1%}")
findings.append(f"   - Maximum gap: {max_cum_delta:+.1%} (after batch {max_cum_delta_batch})")
findings.append(f"   - Final gap: {cumulative_deltas[-1][1]:+.1%} (after batch {cumulative_deltas[-1][0]})")
if abs(cumulative_deltas[0][1]) > abs(cumulative_deltas[-1][1]):
    findings.append(f"   - Gap NARROWS over time (systems converge)")
else:
    findings.append(f"   - Gap WIDENS or stabilizes over time")
findings.append("")

# Finding 8: Direction verdict
findings.append(f"8. FINAL VERDICT:")
if total_evo > total_h1:
    findings.append(f"   ✓ Structured Evolution OUTPERFORMS H1 baseline overall")
    findings.append(f"   ✓ Advantage is +{(total_evo-total_h1)/total_tasks:.2%} ({total_evo - total_h1} additional tasks solved)")
    findings.append(f"   ✓ Structured evolution provides modest but consistent gains")
elif total_evo < total_h1:
    findings.append(f"   ✗ H1 baseline OUTPERFORMS Structured Evolution overall")
    findings.append(f"   ✗ Disadvantage is {(total_evo-total_h1)/total_tasks:.2%} ({total_h1 - total_evo} fewer tasks solved)")
else:
    findings.append(f"   = Both systems achieve IDENTICAL overall performance")

findings.append("")

# Print all findings
for finding in findings:
    print(finding)

print("=" * 140)
