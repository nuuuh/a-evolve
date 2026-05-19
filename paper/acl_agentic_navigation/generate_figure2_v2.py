"""Generate Figure 2 v2 — simplified description, mxGraph XML output, higher thinking budget."""

import sys
sys.path.insert(0, '/home/ec2-user/A-EVOLVE-V2/a-evolve/AutoFigure')

from autofigure import AutoFigureAgent, Config
from autofigure.generator import CONFIG

FIGURE_DESCRIPTION = """
Create a professional scientific figure for a top-tier NLP conference paper (ACL 2025).
The figure has TWO horizontally-wide panels stacked vertically. Total size: 17cm wide × 7cm tall.

== PANEL A (top, ~40% height): "Solve-Time Adaptation" ==

A simple left-to-right flow with 3 elements:

1. LEFT: A "Strategy Tree" showing a git branch diagram:
   - A "main" branch (horizontal line with dots)
   - Three branches forking off: "crypto", "binary", "web"
   - Each branch has a small label showing its specialty

2. MIDDLE: A "Navigator" box (rounded rectangle, light blue)
   - Arrow from "Task x_t" entering the Navigator
   - The Navigator reads branch workspaces (shown as "git show" label on arrows going to branches)
   - Outputs a routing decision

3. RIGHT: A "Solver" box (rounded rectangle)
   - Executes on the selected branch
   - Outputs "Result"

Simple flow arrows: Task → Navigator → (selects branch) → Solver → Result

== PANEL B (bottom, ~60% height): "Continual Auto-Harness" ==

A left-to-right pipeline of 4 phases, each as a distinct colored box:

1. "Analyst" (blue box)
   - Input: "Batch trajectories" from top
   - Output arrow to Researchers

2. "Researchers ×3" (green box, slightly wider to suggest parallelism)
   - Three small parallel lanes inside
   - Output arrow to Builder

3. "Builder" (orange box)
   - Output arrow to Verifier

4. "Verifier" (purple box)
   - Output: "Updated workspace" arrow going back up to Panel A
   - A curved "retry" arrow going back to Builder (labeled "max 3")

BELOW the pipeline: Three file icons in a dashed box labeled "Persistent Cross-Cycle State":
   - task_board.md
   - research_log.jsonl
   - architecture.md

TWO red diamond markers labeled "HITL":
   - One between Analyst and Researchers (labeled "steering")
   - One near Researchers (labeled "assistance")

LEFT of pipeline: An input arrow labeled "Temporal-reveal feedback" with a clock icon, representing batch results where labels are revealed only after resolution date.

== CONNECTING ARROWS between panels ==
- Dashed arrow from Panel B "Updated workspace" going UP to Panel A's strategy tree
- Dashed arrow from Panel A "Batch results" going DOWN to Panel B's input

== STYLE ==
- Clean minimalist academic style, white background
- Thin borders, subtle shadows
- Color palette: blue (#4A90D9), green (#5CB85C), orange (#F0AD4E), purple (#9B59B6), red (#E74C3C)
- Panel backgrounds: very light gray (#F8F9FA) with thin border
- Font: sans-serif, 9-10pt equivalent
- All text must be fully visible, no clipping
- Arrows: thin gray with arrowheads
- Keep generous whitespace between elements
"""

# Increase thinking budget for better quality
from autofigure.generator import _call_bedrock
import autofigure.generator as gen

# Patch to increase thinking budget
original_call_bedrock = gen._call_bedrock

def _call_bedrock_high_thinking(contents, model, region):
    """Call Bedrock with maximum thinking budget, using streaming for long requests."""
    import anthropic
    import io
    import base64
    from PIL import Image as PILImage

    try:
        client = anthropic.AnthropicBedrock(aws_region=region)
        message_content = []
        for part in contents:
            if isinstance(part, str):
                message_content.append({"type": "text", "text": part})
            elif isinstance(part, PILImage.Image):
                buf = io.BytesIO()
                part.save(buf, format='PNG')
                image_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                message_content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": image_b64}
                })

        # Use streaming to handle long requests (>10 min)
        text_parts = []
        with client.messages.stream(
            model=model,
            max_tokens=32000,
            thinking={"type": "enabled", "budget_tokens": 20000},
            messages=[{"role": "user", "content": message_content}]
        ) as stream:
            for event in stream:
                if hasattr(event, 'type'):
                    if event.type == 'content_block_start' and hasattr(event, 'content_block'):
                        pass
                    elif event.type == 'content_block_delta':
                        if hasattr(event, 'delta') and hasattr(event.delta, 'text'):
                            text_parts.append(event.delta.text)

        # If streaming didn't capture text via deltas, try the final message
        if not text_parts:
            final = stream.get_final_message()
            for block in final.content:
                if block.type == "text":
                    return block.text

        return ''.join(text_parts) if text_parts else None
    except Exception as e:
        print(f"[_call_bedrock] Error: {e}")
        return None

gen._call_bedrock = _call_bedrock_high_thinking

config = Config(
    generation_provider='bedrock',
    output_dir='/home/ec2-user/A-EVOLVE-V2/a-evolve/paper/acl_agentic_navigation/figures/v2',
    max_iterations=8,
    quality_threshold=8.5,
)

agent = AutoFigureAgent(config)

print("Starting Figure 2 v2 generation...")
print(f"  Provider: bedrock (Opus 4, 20k thinking tokens)")
print(f"  Output: mxGraph XML (editable in draw.io)")
print(f"  Max iterations: 8")
print(f"  Quality threshold: 8.5")

result = agent.generate(
    description=FIGURE_DESCRIPTION,
    max_iterations=8,
    output_format="mxgraphxml",
    topic="paper",
)

if result.success:
    print(f"\nSuccess!")
    print(f"  mxGraph XML: {result.mxgraph_path}")
    print(f"  Preview: {result.preview_path}")
    print(f"  Score: {result.final_score}/10")
    print(f"  Iterations: {result.iterations_used}")
else:
    print(f"\nFailed: {result.error}")
    if result.logs:
        for log in result.logs[-10:]:
            print(f"  {log}")
