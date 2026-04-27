"""Actions that read/mutate an ``AgentWorkspace``.

Each action is a thin wrapper over existing methods on
``AgentWorkspace`` — no business logic duplicated here.  They translate
between the Activity's typed pins and the workspace API.
"""

from __future__ import annotations

from typing import Any

from ..action import Action
from ..pin import InputPin, OutputPin
from ..types import Type


class SnapshotWorkspace(Action):
    """Capture pre-mutation workspace state for later diffing.

    Output is an opaque ``WorkspaceSnapshot`` dict carrying the
    enumerated state of every layer at the time of snapshotting.
    """

    action_kind = "op.snapshot_workspace"

    @classmethod
    def input_pins(cls, config=None):
        return [InputPin(name="workspace", type=Type.WORKSPACE)]

    @classmethod
    def output_pins(cls, config=None):
        return [
            OutputPin(name="snapshot", type=Type.WORKSPACE_SNAPSHOT),
            OutputPin(name="drafts", type=Type.STRING_LIST),
        ]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        ws = inputs["workspace"]
        import hashlib

        def _hash_dir(d):
            """Hash filenames + contents for change detection."""
            h = hashlib.md5()
            if d.exists():
                for f in sorted(d.iterdir()):
                    if f.is_file():
                        h.update(f.name.encode())
                        try:
                            h.update(f.read_bytes())
                        except Exception:
                            pass
            return h.hexdigest()

        skills = {s.name for s in ws.list_skills()}
        prompt = ws.read_prompt()
        memory = ws.read_all_memories(limit=9999)
        tools = ws.read_tool_registry()
        tools_hash = _hash_dir(ws.root / "tools")
        infra_hash = _hash_dir(ws.root / "infra")
        drafts = ws.list_drafts()
        return {
            "snapshot": {
                "skills": skills,
                "prompt": prompt,
                "memory_len": len(memory),
                "tools": tools,
                "tools_hash": tools_hash,
                "infra_hash": infra_hash,
            },
            "drafts": drafts,
        }


class DetectMutations(Action):
    """Compare current workspace state against a snapshot.

    Emits a ``MutationReport`` whose ``mutated`` flag is True if any of
    the enumerated layers changed.  Matches the comparison used in
    ``InlineTemplate.execute`` / ``OrchestratedTemplate._execute_plan_step``.
    """

    action_kind = "op.detect_mutations"

    @classmethod
    def input_pins(cls, config=None):
        return [
            InputPin(name="workspace", type=Type.WORKSPACE),
            InputPin(name="snapshot", type=Type.WORKSPACE_SNAPSHOT),
        ]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="report", type=Type.MUTATION_REPORT)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        import hashlib
        ws = inputs["workspace"]
        snap = inputs["snapshot"]

        def _hash_dir(d):
            h = hashlib.md5()
            if d.exists():
                for f in sorted(d.iterdir()):
                    if f.is_file():
                        h.update(f.name.encode())
                        try:
                            h.update(f.read_bytes())
                        except Exception:
                            pass
            return h.hexdigest()

        skills_after = {s.name for s in ws.list_skills()}
        prompt_changed = ws.read_prompt() != snap["prompt"]
        memory_changed = len(ws.read_all_memories(limit=9999)) != snap["memory_len"]
        skills_changed = skills_after != snap["skills"]
        tools_changed = (ws.read_tool_registry() != snap["tools"]
                         or _hash_dir(ws.root / "tools") != snap.get("tools_hash", ""))
        infra_changed = _hash_dir(ws.root / "infra") != snap.get("infra_hash", "")

        mutated = (prompt_changed or memory_changed or skills_changed
                   or tools_changed or infra_changed)
        changed = []
        if prompt_changed:
            changed.append("prompt")
        if skills_changed:
            changed.append("skills")
        if memory_changed:
            changed.append("memory")
        if tools_changed:
            changed.append("tools")
        if infra_changed:
            changed.append("infra")
        summary = ", ".join(changed) if changed else "no mutation"

        return {
            "report": {
                "mutated": mutated,
                "summary": summary,
                "changed_layers": changed,
                "new_skills": sorted(skills_after - snap["skills"]),
            }
        }


class ClearDrafts(Action):
    """Delete the ``_drafts`` directory.  Matches ``workspace.clear_drafts``."""

    action_kind = "op.clear_drafts"

    @classmethod
    def input_pins(cls, config=None):
        return [InputPin(name="workspace", type=Type.WORKSPACE)]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="done", type=Type.VOID)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        inputs["workspace"].clear_drafts()
        return {"done": None}


BUILTINS = [SnapshotWorkspace, DetectMutations, ClearDrafts]
