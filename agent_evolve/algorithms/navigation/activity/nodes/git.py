"""Git actions.

Wrap ``VersionControl`` operations as typed nodes.  Each unpacks the
``GitTree`` pin (a ``(VersionControl, StrategyTree)`` tuple) and calls
the appropriate method.

These are pure adapters — no logic duplicated.
"""

from __future__ import annotations

import logging
from typing import Any

from ..action import Action
from ..pin import InputPin, OutputPin
from ..types import Type

logger = logging.getLogger(__name__)


class GitCommit(Action):
    """Commit workspace changes + optionally tag.

    Config keys (evaluated with simple ``{evo_number}`` / ``{branch}``
    templating):
        message:  commit message template (default ``"evo-{evo_number}"``)
        tag:      optional tag template
    """

    action_kind = "op.git_commit"

    @classmethod
    def input_pins(cls, config=None):
        return [
            InputPin(name="git", type=Type.GIT_TREE),
            InputPin(name="evo_number", type=Type.INTEGER),
            InputPin(name="report", type=Type.MUTATION_REPORT, required=False),
            InputPin(name="branch", type=Type.STRING, required=False),
        ]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="done", type=Type.VOID)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        vc, _ = inputs["git"]
        evo_number = int(inputs["evo_number"])
        branch = inputs.get("branch") or "main"
        report = inputs.get("report") or {}
        summary = report.get("summary", "")

        msg_tmpl = self.config.get("message", "evo-{evo_number}: {summary}")
        tag_tmpl = self.config.get("tag", "evo-{evo_number}")

        ctx_vars = {"evo_number": evo_number, "branch": branch, "summary": summary}
        msg = msg_tmpl.format(**ctx_vars)
        tag = tag_tmpl.format(**ctx_vars) if tag_tmpl else None
        vc.commit(message=msg, tag=tag)
        return {"done": None}


class GitCheckout(Action):
    """Checkout a branch.  Returns the GitTree pin re-exposed for chaining."""

    action_kind = "op.git_checkout"

    @classmethod
    def input_pins(cls, config=None):
        return [
            InputPin(name="git", type=Type.GIT_TREE),
            InputPin(name="branch", type=Type.STRING),
        ]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="git", type=Type.GIT_TREE)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        vc, tree = inputs["git"]
        try:
            vc.checkout_branch(inputs["branch"])
        except Exception as e:
            logger.warning("git checkout %r failed: %s", inputs["branch"], e)
        return {"git": (vc, tree)}


class GitEnsureMain(Action):
    """Ensure HEAD is on ``main``; no-op if already there.

    Config:
        safe: bool (default False) — when True, exceptions are swallowed
              and a second checkout attempt is made (mirrors the post-LLM
              safety net in ``InlineTemplate``).
    """

    action_kind = "op.git_ensure_main"

    @classmethod
    def input_pins(cls, config=None):
        return [InputPin(name="git", type=Type.GIT_TREE)]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="git", type=Type.GIT_TREE)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        vc, tree = inputs["git"]
        safe = bool(self.config.get("safe", False))
        try:
            current = vc.get_current_branch()
            if current != "main":
                if safe:
                    logger.warning(
                        "Evolver left workspace on branch %r, returning to main",
                        current,
                    )
                vc.checkout_branch("main")
        except Exception:
            if not safe:
                raise
            try:
                vc.checkout_branch("main")
            except Exception:
                pass
        return {"git": (vc, tree)}


class GitListBranches(Action):
    """List all non-main branch names currently in the repo."""

    action_kind = "op.git_list_branches"

    @classmethod
    def input_pins(cls, config=None):
        return [InputPin(name="git", type=Type.GIT_TREE)]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="branches", type=Type.STRING_LIST)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        vc, _ = inputs["git"]
        return {"branches": sorted(vc.list_branches())}


class GitDiscoverNewBranches(Action):
    """Return branch names that appeared since the ``before`` snapshot."""

    action_kind = "op.git_discover_new_branches"

    @classmethod
    def input_pins(cls, config=None):
        return [
            InputPin(name="git", type=Type.GIT_TREE),
            InputPin(name="before", type=Type.STRING_LIST),
        ]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="new_branches", type=Type.STRING_LIST)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        vc, _ = inputs["git"]
        after = set(vc.list_branches())
        new = sorted(after - set(inputs["before"]))
        return {"new_branches": new}


class GitRegisterBranches(Action):
    """Register discovered branches into the StrategyTree.

    Mirrors the discovery block of ``InlineTemplate.execute`` (lines
    124-155): prefer ``README.md`` description, fall back to the commit
    message.
    """

    action_kind = "op.git_register_branches"

    @classmethod
    def input_pins(cls, config=None):
        return [
            InputPin(name="git", type=Type.GIT_TREE),
            InputPin(name="new_branches", type=Type.STRING_LIST),
            InputPin(name="evo_number", type=Type.INTEGER),
        ]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="done", type=Type.VOID)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        from .....types import BranchInfo

        vc, tree = inputs["git"]
        evo_number = int(inputs["evo_number"])
        known = {b.name for b in tree.branches}

        for branch_name in inputs["new_branches"]:
            if branch_name in known:
                continue
            description = ""
            try:
                readme = vc.show_file_at(branch_name, "README.md")
                for line in readme.splitlines():
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        description = stripped[:200]
                        break
            except Exception:
                pass
            if not description:
                try:
                    description = vc._git(
                        "log", "--format=%s", f"main..{branch_name}", "-1"
                    ).strip()
                except Exception:
                    pass
            tree.branches.append(
                BranchInfo(
                    name=branch_name,
                    created_at_cycle=evo_number,
                    description=description,
                )
            )
            logger.info("Discovered new branch: %s", branch_name)
        return {"done": None}


class GitTagBranchHeads(Action):
    """Tag every branch head that advanced during this evolution."""

    action_kind = "op.git_tag_branch_heads"

    @classmethod
    def input_pins(cls, config=None):
        return [
            InputPin(name="git", type=Type.GIT_TREE),
            InputPin(name="evo_number", type=Type.INTEGER),
        ]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="done", type=Type.VOID)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        vc, _ = inputs["git"]
        evo_number = int(inputs["evo_number"])
        for branch_name in vc.list_branches():
            tag_suffix = branch_name.replace("/", "-")
            try:
                diff = vc._git(
                    "log", "--oneline",
                    f"pre-nav-evo-{evo_number}..{branch_name}", "-1",
                )
                if diff.strip():
                    vc._git("tag", "-f",
                            f"evo-{evo_number}-{tag_suffix}", branch_name)
            except Exception:
                pass
        return {"done": None}


class GitRealiseBranches(Action):
    """Sanitise + create branches from a ``BranchSpecList``.

    Matches ``OrchestratedTemplate._realise_branches``.
    """

    action_kind = "op.git_realise_branches"

    @classmethod
    def input_pins(cls, config=None):
        return [
            InputPin(name="git", type=Type.GIT_TREE),
            InputPin(name="branches", type=Type.BRANCH_SPEC_LIST),
            InputPin(name="evo_number", type=Type.INTEGER),
        ]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="branches", type=Type.BRANCH_SPEC_LIST)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        from ...engine import NavigationEngine
        from .....types import BranchInfo

        vc, tree = inputs["git"]
        evo_number = int(inputs["evo_number"])
        seen: set[str] = set()
        realised: list[dict[str, Any]] = []
        current = vc.get_current_branch()

        for rec in inputs["branches"] or []:
            if not isinstance(rec, dict):
                continue
            raw_name = rec.get("name", "")
            clean = NavigationEngine._sanitize_branch_name(raw_name)
            if not clean or clean == "main" or clean in seen:
                if not clean or clean == "main":
                    logger.warning("Skipping unusable branch name: %r", raw_name)
                continue
            seen.add(clean)
            rec = dict(rec)
            rec["name"] = clean
            if vc.branch_exists(clean):
                realised.append(rec)
                continue
            try:
                vc.create_branch(clean, "main")
                logger.info("Created branch: %s", clean)
            except (ValueError, RuntimeError) as e:
                logger.warning("Failed to create branch %r: %s", clean, e)
                continue
            if not any(b.name == clean for b in tree.branches):
                tree.branches.append(
                    BranchInfo(
                        name=clean,
                        created_at_cycle=evo_number,
                        description=rec.get("description", ""),
                    )
                )
            realised.append(rec)
        try:
            vc.checkout_branch(current)
        except Exception:
            pass
        return {"branches": realised}


class GitRebaseBranches(Action):
    """Rebase every non-main branch onto main.  No-ops individual failures."""

    action_kind = "op.git_rebase_branches"

    @classmethod
    def input_pins(cls, config=None):
        return [InputPin(name="git", type=Type.GIT_TREE)]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="done", type=Type.VOID)]

    def execute(self, inputs: dict[str, Any], ctx) -> dict[str, Any]:
        vc, _ = inputs["git"]
        for br_name in vc.list_branches():
            try:
                vc.rebase_branch(br_name, "main")
            except Exception as e:
                logger.warning("Rebase %s failed: %s", br_name, e)
        return {"done": None}


BUILTINS = [
    GitCommit,
    GitCheckout,
    GitEnsureMain,
    GitListBranches,
    GitDiscoverNewBranches,
    GitRegisterBranches,
    GitTagBranchHeads,
    GitRealiseBranches,
    GitRebaseBranches,
]
