#!/usr/bin/env python3
"""Prepare FutureX-Online submission JSON from experiment results.

Reads results + trajectories, extracts \\boxed{} answers, maps back to
the original HuggingFace dataset IDs, and writes a JSON file ready to
email to FutureX-ai@outlook.com.

Usage:
    python evaluations/analysis_futurex/prepare_submission.py \
        --results-dir results/futurex_online_eval \
        --output futurex_submission.json

Output format (per submission guidelines):
    [
      {"id": "69b2b593782d0900685d5fcb", "prediction": "A"},
      {"id": "698dd05b7812fd005da4275d", "prediction": "B, C"},
      ...
    ]
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def load_online_id_mapping():
    """Map our internal task_ids to original HuggingFace hex IDs.

    Uses the same data_loader as the experiment to ensure task_ids match,
    then maps by index to the HF dataset's original hex IDs.
    """
    try:
        from datasets import load_dataset
        from agent_evolve.benchmarks.futurex.data_loader import FutureXDataLoader
        logging.getLogger("agent_evolve").setLevel(logging.WARNING)

        loader = FutureXDataLoader()
        _, online_tasks = loader.load_datasets()
        ds = load_dataset("futurex-ai/Futurex-Online", split="train")

        mapping = {}
        for i, task in enumerate(online_tasks):
            if i < len(ds):
                mapping[task.task_id] = ds[i]["id"]

        log.info("Mapped %d task IDs to HF IDs", len(mapping))
        return mapping
    except Exception as e:
        log.error("Failed to build ID mapping: %s", e)
        sys.exit(1)


def extract_prediction(results_dir, task_id):
    """Extract the \\boxed{} answer from a task's trajectory."""
    traj_file = results_dir / f"trajectory_{task_id}.json"
    if not traj_file.exists():
        return None

    traj = json.loads(traj_file.read_text())

    # Search backwards for the last \\boxed{} answer
    for msg in reversed(traj):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "")
        # Match \boxed{...} or \\boxed{...}
        matches = re.findall(r'\\?boxed\{([^}]+)\}', content)
        if matches:
            return matches[-1].strip()

    return None


def main():
    parser = argparse.ArgumentParser(description="Prepare FutureX submission")
    parser.add_argument("--results-dir", type=str,
                        default="results/futurex_online_eval",
                        help="Directory with results.jsonl and trajectories")
    parser.add_argument("--output", type=str,
                        default="futurex_submission.json",
                        help="Output JSON file")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    results_file = results_dir / "results.jsonl"

    if not results_file.exists():
        log.error("No results.jsonl in %s", results_dir)
        sys.exit(1)

    # Load results
    results = []
    with open(results_file) as f:
        for line in f:
            results.append(json.loads(line))
    log.info("Loaded %d results from %s", len(results), results_file)

    # Map task IDs to HF IDs
    id_mapping = load_online_id_mapping()

    # Extract predictions
    submission = []
    missing_answer = 0
    missing_id = 0

    for r in results:
        task_id = r["instance_id"]
        hf_id = id_mapping.get(task_id)

        if not hf_id:
            log.warning("No HF ID mapping for %s", task_id)
            missing_id += 1
            continue

        prediction = extract_prediction(results_dir, task_id)
        if not prediction:
            log.warning("No boxed answer for %s", task_id)
            missing_answer += 1
            prediction = ""  # Submit empty rather than skip

        submission.append({
            "id": hf_id,
            "prediction": prediction,
        })

    # Write output
    output_path = Path(args.output)
    output_path.write_text(json.dumps(submission, indent=2, ensure_ascii=False))

    log.info("")
    log.info("=== Submission Summary ===")
    log.info("Tasks: %d/%d", len(submission), len(results))
    log.info("With predictions: %d", len(submission) - missing_answer)
    log.info("Missing answers: %d", missing_answer)
    log.info("Missing ID mapping: %d", missing_id)
    log.info("Output: %s", output_path)
    log.info("")
    log.info("Submit to: FutureX-ai@outlook.com")
    log.info("Subject: FutureX Challenge Submission — A-EVOLVE-V2 [%s]",
             results_dir.name)


if __name__ == "__main__":
    main()
