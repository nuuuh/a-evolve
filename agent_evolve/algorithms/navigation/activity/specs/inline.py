"""Reference Activity: ``InlineTemplate.execute()`` as a UML Activity.

One flat Activity, no sub-Activities.  The evolver LLM is allowed full
git access via its sandbox; post-hoc this Activity discovers what
branches appeared and registers them in the StrategyTree.

Exact node-by-node mapping (lines refer to ``templates/inline.py``
before rewrite):

    52    list_branches                 -> op.git_list_branches
    54-56 ensure on main                 -> op.git_ensure_main(safe=False)
    58-62 snapshot state                  -> op.snapshot_workspace
    65-75 build_evolution_prompt         -> op.build_evolution_prompt
    75    append branching section       -> op.append_branching_section
    77-85 protect + call_llm             -> op.call_llm
    87    clear drafts (BEFORE diff!)    -> op.clear_drafts
    92-105 safe-ensure main              -> op.git_ensure_main(safe=True)
    108-113 detect mutations              -> op.detect_mutations
    118-121 commit main                   -> op.git_commit
    124-155 discover + register           -> op.git_discover_new_branches +
                                              op.git_register_branches
    157-170 tag branch heads              -> op.git_tag_branch_heads
"""

from __future__ import annotations

from ..builder import ActivityBuilder
from ..spec import Activity
from ..types import Type


def build_inline_activity() -> Activity:
    return (
        ActivityBuilder(
            "inline",
            description="Single-call evolution: evolver uses git inside sandbox; "
                        "post-hoc we discover + register the branches it created.",
        )
        .parameter("workspace", Type.WORKSPACE, direction="in")
        .parameter("git", Type.GIT_TREE, direction="in")
        .parameter("batch", Type.BATCH_RESULTS, direction="in")
        .parameter("cfg", Type.CONFIG, direction="in")
        .parameter("evo_number", Type.INTEGER, direction="in")
        .parameter("mutated", Type.MUTATION_REPORT, direction="out")

        # 1. Snapshot branches before LLM runs
        .action("list_before", "op.git_list_branches")

        # 2. Ensure HEAD on main (strict — raises on failure)
        .action("ensure_main_pre", "op.git_ensure_main", safe=False)

        # 3. Workspace snapshot
        .action("snap", "op.snapshot_workspace")

        # 4. Build evolution prompt
        .action("prompt", "op.build_evolution_prompt")

        # 5. Append branching section
        .action("prompt_with_branching", "op.append_branching_section")

        # 6. Run the sandboxed LLM
        .action("call", "op.call_llm")

        # 7. Clear drafts (before diff — inline-specific ordering)
        .action("clear", "op.clear_drafts")

        # 8. Safe-ensure main (evolver may have left us elsewhere)
        .action("ensure_main_post", "op.git_ensure_main", safe=True)

        # 9. Detect mutations
        .action("diff", "op.detect_mutations")

        # 10. Commit main (always, even if no-op — matches original)
        .action(
            "commit_main",
            "op.git_commit",
            message="evo-{evo_number}-main: inline evolution",
            tag="evo-{evo_number}-main",
        )

        # 11. Discover + register new branches
        .action("discover", "op.git_discover_new_branches")
        .action("register", "op.git_register_branches")

        # 12. Tag branch heads
        .action("tag", "op.git_tag_branch_heads")

        # ── Wires ──
        .object_flow("git", "list_before.git")
        .object_flow("git", "ensure_main_pre.git")

        .object_flow("workspace", "snap.workspace")

        .object_flow("workspace", "prompt.workspace")
        .object_flow("batch", "prompt.batch_results")
        .object_flow("cfg", "prompt.config")
        .object_flow("snap.drafts", "prompt.drafts")
        .object_flow("evo_number", "prompt.evo_number")

        .object_flow("prompt.text", "prompt_with_branching.prompt")
        .object_flow("git", "prompt_with_branching.git")
        .object_flow("batch", "prompt_with_branching.batch_results")

        .object_flow("prompt_with_branching.text", "call.prompt")
        .object_flow("workspace", "call.workspace")
        .object_flow("cfg", "call.config")

        .object_flow("workspace", "clear.workspace")

        .object_flow("git", "ensure_main_post.git")

        .object_flow("workspace", "diff.workspace")
        .object_flow("snap.snapshot", "diff.snapshot")

        .object_flow("git", "commit_main.git")
        .object_flow("evo_number", "commit_main.evo_number")
        .object_flow("diff.report", "commit_main.report")

        .object_flow("git", "discover.git")
        .object_flow("list_before.branches", "discover.before")

        .object_flow("git", "register.git")
        .object_flow("discover.new_branches", "register.new_branches")
        .object_flow("evo_number", "register.evo_number")

        .object_flow("git", "tag.git")
        .object_flow("evo_number", "tag.evo_number")

        .object_flow("diff.report", "mutated")

        # ── ControlFlows (enforce execution ordering) ──
        # The LLM mutates the workspace in place; downstream nodes read
        # live workspace state rather than a token on a wire.  Explicit
        # ControlFlows ensure those observers run *after* the LLM call.
        .control_flow("list_before", "ensure_main_pre")
        .control_flow("ensure_main_pre", "snap")
        .control_flow("snap", "prompt")
        .control_flow("prompt", "prompt_with_branching")
        .control_flow("prompt_with_branching", "call")
        .control_flow("call", "clear")
        .control_flow("clear", "ensure_main_post")
        .control_flow("ensure_main_post", "diff")
        .control_flow("diff", "commit_main")
        .control_flow("commit_main", "discover")
        .control_flow("discover", "register")
        .control_flow("register", "tag")

        .build_unchecked()
    )
