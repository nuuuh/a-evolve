"""Bash tool spec and LLM provider factory for A-Evolve."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from ...config import EvolveConfig
from ...llm.base import LLMProvider

logger = logging.getLogger(__name__)

BASH_TOOL_SPEC = {
    "name": "workspace_bash",
    "description": (
        "Execute a bash command in the agent workspace directory. "
        "Use this to read/write skills, prompts, memory files, and inspect git history."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute in the workspace directory.",
            },
        },
        "required": ["command"],
    },
}

HUMAN_TOOL_SPEC = {
    "name": "request_human_action",
    "description": (
        "Request help from a human operator. Use this when you need something "
        "that requires human involvement: API keys, account signups, credential "
        "provisioning, manual verification, or domain expertise. The human will "
        "see your message and can respond with information or instructions."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Clear description of what you need the human to do.",
            },
            "action_type": {
                "type": "string",
                "enum": ["credential", "verification", "information", "approval"],
                "description": "Type of action needed.",
            },
        },
        "required": ["message"],
    },
}

SANDBOX_IMAGE = "evolver-sandbox:latest"
_SANDBOX_BASE = "alpine:latest"
_sandbox_image_ready = False


def _ensure_sandbox_image():
    """Build the sandbox image with bash+git pre-installed.

    We build a local image once so that containers started with
    --network none already have everything they need.
    """
    global _sandbox_image_ready
    if _sandbox_image_ready:
        return
    # Check if our pre-built image exists
    result = subprocess.run(
        ["docker", "image", "inspect", SANDBOX_IMAGE],
        capture_output=True,
    )
    if result.returncode == 0:
        _sandbox_image_ready = True
        return
    # Build it from alpine + common packages evolved tools need.
    logger.info("Building sandbox image %s (one-time)...", SANDBOX_IMAGE)
    dockerfile = (
        f"FROM {_SANDBOX_BASE}\n"
        "RUN apk add --no-cache bash git python3 py3-pip curl jq \\\n"
        "    && pip3 install --break-system-packages \\\n"
        "       requests beautifulsoup4 lxml htmldate \\\n"
        "       duckduckgo-search feedparser pyyaml \\\n"
        "       numpy sympy yfinance \\\n"
        "       pycryptodome python-dateutil\n"
    )
    result = subprocess.run(
        ["docker", "build", "-t", SANDBOX_IMAGE, "-"],
        input=dockerfile,
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to build sandbox image: {result.stderr}")
    _sandbox_image_ready = True
    logger.info("Sandbox image built: %s", SANDBOX_IMAGE)


class EvolverSandbox:
    """Docker-based sandbox for the evolver's workspace_bash tool.

    Bind-mounts the workspace into a lightweight container so the evolver
    LLM can only access workspace files. Changes persist to the host via
    the bind mount.
    """

    def __init__(
        self,
        workspace_root: str | Path,
        evolver_workspace: str | Path | None = None,
        network: str = "none",
        trajectories_dir: str | Path | None = None,
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.evolver_workspace = (
            Path(evolver_workspace).resolve() if evolver_workspace else None
        )
        self.trajectories_dir = (
            Path(trajectories_dir).resolve() if trajectories_dir else None
        )
        self.container_name = f"evolver-sandbox-{id(self)}"
        self.network = network
        self._running = False

    def start(self):
        _ensure_sandbox_image()
        # Remove stale container if exists
        subprocess.run(
            ["docker", "rm", "-f", self.container_name],
            capture_output=True,
        )
        # Run as current user so files created inside the bind mount
        # have correct ownership on the host (avoids root-owned .git/objects).
        import os
        uid_gid = f"{os.getuid()}:{os.getgid()}"

        # Build mount list: solver workspace always, evolver workspace optional
        mounts = ["-v", f"{self.workspace_root}:/solver_workspace"]
        work_dir = "/solver_workspace"
        if self.evolver_workspace:
            mounts += ["-v", f"{self.evolver_workspace}:/evolver_workspace"]
            work_dir = "/evolver_workspace"

        # Mask ground-truth observations and feedback_archive in whichever
        # workspace contains them. When evolver_workspace exists, the
        # Observer writes to evolver_workspace/evolution/; otherwise to
        # solver_workspace/evolution/.
        for mount_prefix, host_root in [
            ("/solver_workspace", self.workspace_root),
            ("/evolver_workspace", self.evolver_workspace),
        ]:
            if host_root is None:
                continue
            obs_dir = Path(host_root) / "evolution" / "observations"
            if obs_dir.exists():
                mounts += ["--tmpfs", f"{mount_prefix}/evolution/observations"]
            archive = Path(host_root) / "evolution" / "feedback_archive.jsonl"
            if archive.exists():
                mounts += ["-v", f"/dev/null:{mount_prefix}/evolution/feedback_archive.jsonl:ro"]

        # Read-only trajectories mount. Evolution ground truth
        # (success/score/feedback in batch_*.jsonl) is masked above and
        # is deliberately NOT exposed here — the evolver must infer
        # from behaviour alone.
        if self.trajectories_dir:
            mounts += [
                "-v",
                f"{self.trajectories_dir}:/trajectories:ro",
            ]

        result = subprocess.run(
            [
                "docker", "run", "-d",
                "--name", self.container_name,
                "--user", uid_gid,
                "-e", "HOME=/tmp",
                "--network", self.network,
                *mounts,
                "-w", work_dir,
                SANDBOX_IMAGE,
                "sleep", "infinity",
            ],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to start evolver sandbox: {result.stderr}")
        # Configure git inside container (needed for git diff etc.)
        for safe_dir in ["/solver_workspace", "/evolver_workspace"]:
            subprocess.run(
                ["docker", "exec", self.container_name,
                 "git", "config", "--global", "--add",
                 "safe.directory", safe_dir],
                capture_output=True, timeout=10,
            )
        self._running = True
        logger.info("Evolver sandbox started: %s", self.container_name)

    def exec(self, command: str) -> str:
        """Execute a bash command inside the sandbox container."""
        # Use /evolver_workspace as cwd if both workspaces mounted,
        # otherwise /solver_workspace (backward compat: /solver_workspace
        # is always mounted)
        cwd = "/evolver_workspace" if self.evolver_workspace else "/solver_workspace"
        try:
            result = subprocess.run(
                ["docker", "exec", "-w", cwd,
                 self.container_name, "bash", "-c", command],
                capture_output=True, text=True, timeout=60,
            )
            output = (result.stdout + result.stderr).strip()
            return output if output else "(no output)"
        except subprocess.TimeoutExpired:
            return "ERROR: Command timed out."
        except Exception as e:
            return f"ERROR: {e}"

    def stop(self):
        if self._running:
            subprocess.run(
                ["docker", "rm", "-f", self.container_name],
                capture_output=True,
            )
            self._running = False
            logger.info("Evolver sandbox stopped: %s", self.container_name)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


def _shell_quote(s: str) -> str:
    """Single-quote a string for safe shell embedding."""
    return "'" + s.replace("'", "'\\''") + "'"


def make_workspace_bash(
    workspace_root: str | Path,
    evolver_workspace: str | Path | None = None,
    network: str = "none",
    trajectories_dir: str | Path | None = None,
) -> EvolverSandbox:
    """Create a Docker sandbox for the evolver's workspace_bash tool.

    Returns a sandbox with:
    - /solver_workspace → workspace_root (always mounted)
    - /evolver_workspace → evolver_workspace (only when --navigation)
    - /trajectories → trajectories_dir (read-only, ground-truth-free)

    The evolver cannot access any files outside these mounts. In
    particular, evolution/observations/ (ground-truth-bearing) is never
    mounted.

    Raises RuntimeError if Docker is not available — there is no insecure
    fallback.
    """
    root = Path(workspace_root).resolve()

    try:
        docker_ok = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=5,
        ).returncode == 0
    except Exception:
        docker_ok = False

    if not docker_ok:
        raise RuntimeError(
            "Docker is required for evolver sandbox isolation. "
            "Install Docker or skip evolution (set evo_trigger_threshold: -1 in config)."
        )

    logger.info("Evolver using Docker sandbox (network=%s)", network)
    ew = Path(evolver_workspace).resolve() if evolver_workspace else None
    td = Path(trajectories_dir).resolve() if trajectories_dir else None
    return EvolverSandbox(root, ew, network=network, trajectories_dir=td)


def create_default_llm(config: EvolveConfig) -> LLMProvider:
    """Create the default LLM provider based on the evolver_model config string."""
    model = config.evolver_model

    if "." in model and ("anthropic" in model or "amazon" in model or "meta" in model):
        from ...llm.bedrock import BedrockProvider

        region = config.extra.get("region", "us-west-2")
        return BedrockProvider(model_id=model, region=region)

    if model.startswith("claude"):
        from ...llm.anthropic import AnthropicProvider

        return AnthropicProvider(model=model)

    if model.startswith(("gpt-", "o1", "o3")):
        from ...llm.openai import OpenAIProvider

        return OpenAIProvider(model=model)

    from ...llm.bedrock import BedrockProvider

    return BedrockProvider(model_id=model)
