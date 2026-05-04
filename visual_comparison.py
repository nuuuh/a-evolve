#!/usr/bin/env python3
"""
ASCII visualization of H1 vs Structured Evolution comparison.
"""

import json

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

print("=" * 140)
print("ASCII VISUALIZATION: H1 vs STRUCTURED EVOLUTION")
print("=" * 140)
print()

# Batch score comparison
print("BATCH SCORES COMPARISON")
print("-" * 140)
print()

batch_nums = range(1, 10)
for i, batch in enumerate(batch_nums):
    if i < len(h1_history) and i < len(evo_history):
        h1_score = h1_history[i]['batch_score']
        evo_score = evo_history[i]['batch_score']

        h1_bar = "█" * int(h1_score * 50)
        evo_bar = "█" * int(evo_score * 50)

        print(f"Batch {batch}:")
        print(f"  H1  ({h1_score:5.1%}): {h1_bar:<50}")
        print(f"  Evo ({evo_score:5.1%}): {evo_bar:<50}")
        if evo_score > h1_score:
            print(f"           Winner: Evo (+{(evo_score - h1_score):.1%})")
        elif h1_score > evo_score:
            print(f"           Winner: H1  (+{(h1_score - evo_score):.1%})")
        else:
            print(f"           Winner: Tie")
        print()

print()
print("=" * 140)
print("CUMULATIVE ACCURACY OVER TIME")
print("-" * 140)
print()

# Cumulative accuracy
cumulative_h1 = []
cumulative_evo = []
for i in range(len(h1_history)):
    if i < len(h1_history):
        cum_h1 = h1_history[i]['cumulative_passed'] / h1_history[i]['cumulative_total']
        cumulative_h1.append(cum_h1)
    if i < len(evo_history):
        cum_evo = evo_history[i]['cumulative_passed'] / evo_history[i]['cumulative_total']
        cumulative_evo.append(cum_evo)

# Draw chart
max_val = 0.6
height = 20
width = len(cumulative_h1)

print("  60% ┤")
for row in range(height, -1, -1):
    threshold = (row / height) * max_val
    line = "      │"
    for i in range(width):
        h1_val = cumulative_h1[i] if i < len(cumulative_h1) else 0
        evo_val = cumulative_evo[i] if i < len(cumulative_evo) else 0

        if abs(h1_val - threshold) < (max_val / height / 2) or abs(evo_val - threshold) < (max_val / height / 2):
            if abs(h1_val - threshold) < abs(evo_val - threshold):
                line += "H"
            else:
                line += "E"
        elif min(h1_val, evo_val) > threshold:
            line += "│"
        else:
            line += " "
    print(line)

print("   0% └" + "─" * width)
print("       " + "".join(str(i+1) for i in range(width)))
print()
print("  Legend: H = H1, E = Structured Evolution")
print()

# Divergence over time
print()
print("=" * 140)
print("CUMULATIVE DIVERGENCE (Evo - H1)")
print("-" * 140)
print()

for i in range(len(cumulative_h1)):
    batch = i + 1
    delta = cumulative_evo[i] - cumulative_h1[i]
    delta_pct = delta * 100

    # Create bar
    bar_length = int(abs(delta) * 200)
    if delta > 0:
        bar = " " * 40 + "│" + "█" * bar_length
    else:
        bar = " " * (40 - bar_length) + "█" * bar_length + "│"

    print(f"Batch {batch}: {bar} {delta_pct:+.1f}%")

print(" " * 30 + "-10% " + " " * 6 + "0%" + " " * 7 + "+10%")
print()

# Summary
print()
print("=" * 140)
print("SUMMARY")
print("-" * 140)
print()

final_h1 = cumulative_h1[-1]
final_evo = cumulative_evo[-1]
final_delta = final_evo - final_h1

print(f"Final Cumulative Accuracy:")
print(f"  H1:                 {final_h1:.2%}")
print(f"  Structured Evo:     {final_evo:.2%}")
print(f"  Advantage:          {final_delta:+.2%} (Structured Evolution)")
print()

h1_total_time = sum(h['evo_elapsed'] for h in h1_history)
evo_total_time = sum(h['evo_elapsed'] for h in evo_history)
time_ratio = evo_total_time / h1_total_time if h1_total_time > 0 else 0

print(f"Total Evolution Time:")
print(f"  H1:                 {h1_total_time:.0f}s ({h1_total_time/60:.1f} min)")
print(f"  Structured Evo:     {evo_total_time:.0f}s ({evo_total_time/60:.1f} min)")
print(f"  Ratio:              {time_ratio:.2f}x (Structured Evo takes {time_ratio:.1f}x longer)")
print()

# Batch wins
h1_wins = sum(1 for i in range(len(h1_history)) if h1_history[i]['batch_score'] > evo_history[i]['batch_score'])
evo_wins = sum(1 for i in range(len(evo_history)) if evo_history[i]['batch_score'] > h1_history[i]['batch_score'])
ties = sum(1 for i in range(min(len(h1_history), len(evo_history))) if h1_history[i]['batch_score'] == evo_history[i]['batch_score'])

print(f"Batch-Level Wins:")
print(f"  H1:                 {h1_wins}/{len(h1_history)} batches")
print(f"  Structured Evo:     {evo_wins}/{len(evo_history)} batches")
print(f"  Ties:               {ties}/{min(len(h1_history), len(evo_history))} batches")
print()

print("=" * 140)
