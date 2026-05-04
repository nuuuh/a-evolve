#!/usr/bin/env python3
"""Extract specific bash examples from trajectories."""

import json
import glob
from pathlib import Path

results_dir = "/home/ec2-user/A-EVOLVE-V2/a-evolve/results/futurex_smoke_structured_evo"

# Load the analysis
with open(f"{results_dir}/bash_usage_analysis.json") as f:
    analysis = json.load(f)

# Select some interesting cases
cases_to_examine = [
    ("futurex_past_0135_20260130", "Success with bash"),
    ("futurex_past_0434_20260406", "Success with bash"),
    ("futurex_past_0093_20260125", "Failure with bash (2 cmds)"),
    ("futurex_past_0153_20260129", "Failure with bash (42 cmds)"),
    ("futurex_past_0191_20260308", "Failure with bash"),
]

for task_id, desc in cases_to_examine:
    print(f"\n{'='*80}")
    print(f"{desc}: {task_id}")
    print('='*80)

    # Find in analysis
    task_info = None
    for t in analysis['tasks_with_bash']:
        if t['instance_id'] == task_id:
            task_info = t
            break

    if not task_info:
        print(f"Not found in bash tasks")
        continue

    print(f"Success: {task_info['success']}, Score: {task_info['score']}")
    print(f"Total turns: {task_info['turns']}, Bash commands: {len(task_info['bash_commands'])}")

    print(f"\nBash commands:")
    for i, cmd_info in enumerate(task_info['bash_commands'][:10], 1):  # First 10
        print(f"\n--- Command {i} (turn {cmd_info['turn']}) ---")
        cmd = cmd_info['command']
        if len(cmd) > 300:
            print(f"Command (first 300 chars): {cmd[:300]}")
        else:
            print(f"Command: {cmd}")

        output = cmd_info['output']
        if len(output) > 300:
            print(f"Output (first 300 chars): {output[:300]}")
        else:
            print(f"Output: {output}")

print(f"\n{'='*80}")
print("COMPARISON: Tasks without bash")
print('='*80)
print(f"Total tasks without bash: {len(analysis['tasks_without_bash'])}")
successful = [t for t in analysis['tasks_without_bash'] if t['success']]
print(f"Successful: {len(successful)}")
print(f"\nSome successful tasks without bash:")
for t in successful[:5]:
    print(f"  {t['instance_id']}: score={t['score']}, turns={t['turns']}")
