#!/usr/bin/env python3
"""
Analyze bash tool usage in FutureX structured evolution trajectories.
"""

import json
import glob
import os
from collections import defaultdict
from pathlib import Path

results_dir = "/home/ec2-user/A-EVOLVE-V2/a-evolve/results/futurex_smoke_structured_evo"

# Load results.json for success rates
with open(f"{results_dir}/results.json") as f:
    results = json.load(f)

results_map = {r["instance_id"]: r for r in results}

# Find all trajectory files
trajectory_files = glob.glob(f"{results_dir}/trajectory_*.json")

print(f"Found {len(trajectory_files)} trajectory files")

bash_usage = []
no_bash_usage = []

for traj_file in trajectory_files:
    instance_id = Path(traj_file).stem.replace("trajectory_", "")

    with open(traj_file) as f:
        traj_data = json.load(f)

    # Look for bash tool calls in trajectory
    has_bash = False
    bash_commands = []

    # traj_data is a list of messages
    if isinstance(traj_data, list):
        turn_num = 0
        for msg in traj_data:
            if msg.get("role") == "assistant":
                turn_num += 1
                content = msg.get("content", "")
                # Look for [tool_use: bash] pattern
                if "[tool_use: bash]" in content:
                    has_bash = True
                    # Extract command and find corresponding output
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if "[tool_use: bash]" in line:
                            # Get the JSON following
                            if i + 1 < len(lines):
                                try:
                                    cmd_json = json.loads(lines[i + 1])
                                    cmd = cmd_json.get("command", "")
                                    # Find the next user message for output
                                    output = ""
                                    idx = traj_data.index(msg)
                                    if idx + 1 < len(traj_data) and traj_data[idx + 1].get("role") == "user":
                                        output = traj_data[idx + 1].get("content", "")
                                    bash_commands.append({
                                        "command": cmd,
                                        "output": output[:500] if output else "",
                                        "turn": turn_num
                                    })
                                except:
                                    pass

    result_info = results_map.get(instance_id, {})
    success = result_info.get("success", False)
    score = result_info.get("score", 0.0)

    entry = {
        "instance_id": instance_id,
        "success": success,
        "score": score,
        "bash_commands": bash_commands,
        "turns": len(traj_data) if isinstance(traj_data, list) else 0,
        "traj_file": traj_file
    }

    if has_bash:
        bash_usage.append(entry)
    else:
        no_bash_usage.append(entry)

print(f"\n{'='*80}")
print(f"SUMMARY")
print(f"{'='*80}")
print(f"Tasks with bash: {len(bash_usage)}")
print(f"Tasks without bash: {len(no_bash_usage)}")

if bash_usage:
    bash_successes = sum(1 for e in bash_usage if e["success"])
    print(f"Bash success rate: {bash_successes}/{len(bash_usage)} = {bash_successes/len(bash_usage)*100:.1f}%")

if no_bash_usage:
    no_bash_successes = sum(1 for e in no_bash_usage if e["success"])
    print(f"No-bash success rate: {no_bash_successes}/{len(no_bash_usage)} = {no_bash_successes/len(no_bash_usage)*100:.1f}%")

# Categorize bash commands
categories = {
    "search_pipeline": [],
    "python_compute": [],
    "curl_wget": [],
    "other_infra": [],
    "file_ops": [],
    "other": []
}

for entry in bash_usage:
    for cmd_info in entry["bash_commands"]:
        cmd = cmd_info["command"]

        if "/infra/search_pipeline.py" in cmd or "search_pipeline" in cmd:
            categories["search_pipeline"].append((entry, cmd_info))
        elif "python3 -c" in cmd or "python -c" in cmd:
            categories["python_compute"].append((entry, cmd_info))
        elif "curl" in cmd or "wget" in cmd:
            categories["curl_wget"].append((entry, cmd_info))
        elif "/infra/" in cmd:
            categories["other_infra"].append((entry, cmd_info))
        elif any(op in cmd for op in ["ls", "cat", "grep", "find", "head", "tail"]):
            categories["file_ops"].append((entry, cmd_info))
        else:
            categories["other"].append((entry, cmd_info))

print(f"\n{'='*80}")
print(f"COMMAND CATEGORIES")
print(f"{'='*80}")
for cat, items in categories.items():
    print(f"{cat}: {len(items)} commands")

# Show detailed examples
print(f"\n{'='*80}")
print(f"DETAILED EXAMPLES")
print(f"{'='*80}")

for cat, items in categories.items():
    if items:
        print(f"\n{cat.upper()} ({len(items)} commands)")
        print("-" * 80)
        for i, (entry, cmd_info) in enumerate(items[:5]):  # Show first 5
            print(f"\nExample {i+1}: {entry['instance_id']} (success={entry['success']})")
            print(f"Turn {cmd_info['turn']}")
            print(f"Command: {cmd_info['command'][:200]}")
            print(f"Output (first 200 chars): {cmd_info['output'][:200]}")

# Save detailed report
output_file = f"{results_dir}/bash_usage_analysis.json"
with open(output_file, "w") as f:
    json.dump({
        "summary": {
            "total_tasks": len(bash_usage) + len(no_bash_usage),
            "tasks_with_bash": len(bash_usage),
            "tasks_without_bash": len(no_bash_usage),
            "bash_success_rate": bash_successes / len(bash_usage) if bash_usage else 0,
            "no_bash_success_rate": no_bash_successes / len(no_bash_usage) if no_bash_usage else 0
        },
        "category_counts": {cat: len(items) for cat, items in categories.items()},
        "tasks_with_bash": bash_usage,
        "tasks_without_bash": no_bash_usage
    }, f, indent=2)

print(f"\n\nDetailed report saved to: {output_file}")
