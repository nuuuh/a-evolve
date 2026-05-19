"""Generate Figure 2 (unified system pipeline) for the paper using AutoFigure."""

import sys
sys.path.insert(0, '/home/ec2-user/A-EVOLVE-V2/a-evolve/AutoFigure')

from autofigure import AutoFigureAgent, Config

FIGURE_DESCRIPTION = """
Create a high-quality scientific figure for an academic paper (ACL conference style).
The figure shows a unified system pipeline with TWO panels stacked vertically, sharing one figure environment.

=== TOP PANEL: Solve-Time Adaptation (Strategy-Tree Navigation) ===

Show a git-backed strategy tree on the left and a routing mechanism on the right.

LEFT SIDE - Strategy Tree:
- A git repository visualization with branches:
  - "main" branch (horizontal, primary line)
  - "branch/crypto-classical" forking off main
  - "branch/binary-reversing" forking off main
  - "branch/web-modern" forking off main
- Each branch node shows it contains: prompts/system.md, skills/, tools/registry.yaml
- Label: "Strategy Tree (git repository)"

RIGHT SIDE - Routing at Solve Time:
- Input: "Task x_t" arrives
- A "Navigator LLM" box reads branch workspaces via "git show"
- Navigator outputs: {"branch": "binary-reversing", "confidence": 0.83}
- Arrow from navigator to selected branch
- Solver LLM operates on the selected branch's workspace
- Output: "Task result"

Flow: Task x_t → Navigator (reads all branches) → selects best branch → Solver executes on that branch → result

=== BOTTOM PANEL: Continual Auto-Harness (Multi-Agent Evolution) ===

Show a four-phase pipeline that operates BETWEEN batches (during evolution time).
The pipeline flows left-to-right through 4 phases:

PHASE 1 - ANALYST:
- Box labeled "Analyst"
- Reads: batch trajectories (from solver)
- Writes: task_board.md (failure regimes + priorities)
- No sandbox, no network

PHASE 2 - RESEARCHERS (parallel):
- 3 parallel boxes labeled "Researcher 1", "Researcher 2", "Researcher 3"
- Each assigned a different regime from task_board
- Each tests hypotheses independently
- Writes: research_log.jsonl (approach, works:true/false)
- Has sandbox + network

PHASE 3 - BUILDER:
- Box labeled "Builder"
- Reads: only works:true records from research_log
- Writes: solver workspace (infra/, tools/, prompts/system.md)
- Updates: architecture.md
- Has sandbox + network

PHASE 4 - VERIFIER:
- Box labeled "Verifier"
- Tests built artifacts against held-out tasks
- If PASS → commit to workspace
- If FAIL → retry (back to Builder, max 3 times)
- Has sandbox + network

PERSISTENT STATE (shown as files connecting across the bottom):
- task_board.md (persists across cycles, updated by Analyst)
- research_log.jsonl (persists across cycles, appended by Researchers)
- architecture.md (persists across cycles, maintained by Builder)
- Label: "Persistent cross-cycle state"

HITL HOOKS (marked with special icons):
- Hook 1: Between Analyst and Researchers → "Task-board steering" (human reviews/adds to task board)
- Hook 2: During Research phase → "Interactive assistance" (human provides credentials/resources)

TEMPORAL-REVEAL GATE (shown as input to the whole evolution pipeline):
- Batch results arrive with a temporal gate
- Labels revealed only after resolution date
- Arrow labeled "temporal-reveal feedback" feeding into the pipeline

=== CONNECTING THE TWO PANELS ===
- Arrow from bottom panel output ("improved workspace") back to top panel's strategy tree
- Arrow from top panel's "batch results" down to bottom panel input
- This shows the cycle: solve → collect results → evolve → improved workspace → solve again

=== STYLE REQUIREMENTS ===
- Clean, professional academic figure style
- Use light blue/gray backgrounds for panels
- Use distinct colors for different agent roles (e.g., Analyst=blue, Researcher=green, Builder=orange, Verifier=purple)
- HITL hooks should be visually distinct (e.g., red/highlighted border or icon)
- Persistent state files should be shown with a database/file icon
- Git branches should look like a git log visualization
- The figure should be wide (paper width ~17cm) and ~6.5cm tall
- Text should be readable at paper scale (9-10pt equivalent)
- No unnecessary decoration; every element conveys information
"""

config = Config(
    generation_provider='bedrock',
    output_dir='/home/ec2-user/A-EVOLVE-V2/a-evolve/paper/acl_agentic_navigation/figures',
    max_iterations=5,
    quality_threshold=9.0,
)

agent = AutoFigureAgent(config)

print("Starting Figure 2 generation with Claude Opus 4 via Bedrock...")
print(f"Output dir: {config.output_dir}")
print(f"Max iterations: {config.max_iterations}")
print(f"Quality threshold: {config.quality_threshold}")

result = agent.generate(
    description=FIGURE_DESCRIPTION,
    max_iterations=5,
    output_format="svg",
    topic="paper",
)

if result.success:
    print(f"\nSuccess! Figure generated.")
    print(f"SVG: {result.svg_path}")
    print(f"Preview: {result.preview_path}")
    print(f"Score: {result.final_score}/10")
    print(f"Iterations: {result.iterations_used}")
else:
    print(f"\nGeneration failed: {result.error}")
    if result.logs:
        print("Logs:")
        for log in result.logs[-5:]:
            print(f"  {log}")
