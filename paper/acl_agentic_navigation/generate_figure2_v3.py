"""Generate Figure 2 v3 — SVG output, no icons, clean geometric shapes."""

import sys
sys.path.insert(0, '/home/ec2-user/A-EVOLVE-V2/a-evolve/AutoFigure')

from autofigure import AutoFigureAgent, Config

FIGURE_DESCRIPTION = """
Create a publication-quality SVG scientific figure for a top NLP conference (ACL).
Total canvas: 1400px wide × 750px tall. White background.

IMPORTANT RULES:
- Do NOT use any icons, emojis, or image references
- Use ONLY geometric shapes (rectangles, rounded rectangles, circles, diamonds, arrows, lines)
- Use text labels inside or next to shapes
- Keep all text fully visible, no overflow or clipping
- Use a clean sans-serif font (Arial or Helvetica), 11-13px
- All colors should be professional and muted (not saturated)

== COLOR PALETTE ==
- Panel A background: #EBF5FB (very light blue)
- Panel B background: #FEF9E7 (very light yellow)
- Analyst: #2E86C1 (blue)
- Researchers: #28B463 (green)
- Builder: #E67E22 (orange)
- Verifier: #8E44AD (purple)
- HITL markers: #E74C3C (red)
- Arrows: #566573 (dark gray)
- Text: #2C3E50 (near-black)
- Persistent state box: dashed border #AAB7B8

== PANEL A (top half, y=0 to y=300): "Solve-Time Adaptation" ==

Title "Solve-Time Adaptation" at top-left of panel in bold, 14px.

Layout left-to-right:

1. LEFT (x=30-350): Git branch diagram
   - A horizontal line labeled "main" with 4 small filled circles (commits)
   - Three diagonal lines branching off, ending in small filled circles:
     - "crypto" (branch label)
     - "binary" (branch label)
     - "web" (branch label)
   - Small rounded rect next to branches showing: "prompts/ skills/ tools/"

2. CENTER (x=400-700): "Task x_t" text with arrow into a rounded rectangle labeled "Navigator"
   - Below Navigator: small italic text "reads branches via git show"
   - Arrow out from Navigator labeled "selects branch"

3. RIGHT (x=750-1000): Rounded rectangle labeled "Solver"
   - Arrow from Navigator to Solver
   - Arrow out to text "Result"

4. FAR RIGHT (x=1050-1350): Dashed vertical arrows connecting to Panel B:
   - Downward arrow labeled "batch results"
   - Upward arrow labeled "updated workspace"

== PANEL B (bottom half, y=320 to y=750): "Continual Auto-Harness" ==

Title "Continual Auto-Harness (Multi-Agent Evolution)" at top-left in bold, 14px.

Layout left-to-right, pipeline of 4 rounded rectangles:

1. LEFT INPUT (x=30-100):
   - Small rounded rect with red-dashed border: "Temporal Reveal"
   - Below it: "labels after resolution" in 9px italic
   - Arrow pointing right into Analyst

2. PHASE 1 (x=120-280): Blue rounded rect "Analyst"
   - White text inside: "Analyst"
   - Below box: "failure patterns → task_board" in 9px

3. HITL-1 (x=290-320): Small red diamond shape labeled "HITL" with "steering" below in red italic 9px

4. PHASE 2 (x=340-560): Green rounded rect "Researchers ×3"
   - Inside: three horizontal lines suggesting parallel lanes
   - Below box: "test hypotheses → research_log" in 9px

5. HITL-2 (x=570-600): Small red diamond shape labeled "HITL" with "assist" below in red italic 9px

6. PHASE 3 (x=620-800): Orange rounded rect "Builder"
   - Below box: "verified → infra/ tools/ prompts/" in 9px

7. PHASE 4 (x=820-1000): Purple rounded rect "Verifier"
   - Below box: "test & gate deployment" in 9px
   - A curved arrow looping back from Verifier to Builder, labeled "retry (max 3)" in 9px

8. OUTPUT (x=1020-1150): Arrow to text "Updated Workspace"

9. BOTTOM (y=650-730): Dashed rectangle spanning x=120 to x=1000
   - Label inside: "Persistent Cross-Cycle State"
   - Three small file-shaped rectangles inside (rectangles with folded corner):
     - "task_board.md"
     - "research_log.jsonl"
     - "architecture.md"

== ARROWS ==
- All arrows are smooth, with proper arrowheads
- Phase-to-phase arrows flow left to right
- Connecting arrows between panels are dashed gray
"""

config = Config(
    generation_provider='bedrock',
    output_dir='/home/ec2-user/A-EVOLVE-V2/a-evolve/paper/acl_agentic_navigation/figures/v3',
    max_iterations=8,
    quality_threshold=8.5,
)

agent = AutoFigureAgent(config)

print("Starting Figure 2 v3 generation (SVG, no icons, geometric only)...")
print(f"  Max iterations: 8, threshold: 8.5")

result = agent.generate(
    description=FIGURE_DESCRIPTION,
    max_iterations=8,
    output_format="svg",
    topic="paper",
)

if result.success:
    print(f"\nSuccess!")
    print(f"  SVG: {result.svg_path}")
    print(f"  Preview: {result.preview_path}")
    print(f"  Score: {result.final_score}/10")
    print(f"  Iterations: {result.iterations_used}")
else:
    print(f"\nFailed: {result.error}")
    if result.logs:
        for log in result.logs[-5:]:
            print(f"  {log}")
