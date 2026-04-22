"""Wrapper: patches evolver system prompt, then runs solve_all_with_evolution.

This script monkey-patches DEFAULT_EVOLVER_SYSTEM_PROMPT with a custom prompt
focused on infrastructure evolution, then executes the standard entry point.
No existing codebase files are modified.
"""
import sys
from pathlib import Path

# Resolve project root
root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root))

# Monkey-patch the evolver system prompt in BOTH the prompts module
# AND the engine module (which imports a local copy)
import agent_evolve.algorithms.aevolve.prompts as _prompts
import agent_evolve.algorithms.aevolve.engine as _engine

_custom_prompt_path = Path(__file__).parent / "evolver_prompt.md"
_custom_prompt = _custom_prompt_path.read_text()
_prompts.DEFAULT_EVOLVER_SYSTEM_PROMPT = _custom_prompt
_engine.DEFAULT_EVOLVER_SYSTEM_PROMPT = _custom_prompt

# Run the standard entry point
exec(compile((root / "solve_all_with_evolution.py").read_text(),
             str(root / "solve_all_with_evolution.py"), "exec"))
