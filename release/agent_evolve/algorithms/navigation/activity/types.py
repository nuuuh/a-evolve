"""Port types carried on ``ObjectFlow`` wires.

A closed enum of the semantic types an ``Activity`` may move between its
nodes.  Extending this enum is the only safe way to add a new kind of
data that can flow between nodes.
"""

from __future__ import annotations

from enum import Enum


class Type(str, Enum):
    """Semantic type of a value on a wire (an UML ObjectFlow token)."""

    TRAJECTORIES_FOLDER = "TrajectoriesFolder"
    GIT_TREE = "GitTree"
    WORKSPACE = "Workspace"
    BATCH_RESULTS = "BatchResults"
    CONFIG = "Config"
    PROMPT_TEXT = "PromptText"
    LLM_RESPONSE = "LLMResponse"
    PLAN = "Plan"
    BRANCH_SPEC = "BranchSpec"
    BRANCH_SPEC_LIST = "BranchSpecList"
    WORKSPACE_SNAPSHOT = "WorkspaceSnapshot"
    MUTATION_REPORT = "MutationReport"
    BOOLEAN = "Boolean"
    STRING = "String"
    STRING_LIST = "StringList"
    INTEGER = "Integer"
    VOID = "Void"
