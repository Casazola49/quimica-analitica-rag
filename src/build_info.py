"""
src/build_info.py - Build & deployment provenance metadata for the portal.

Exposes ``get_build_info()`` so a running instance can report exactly which
git commit / branch it serves. This closes the gap where an external observer
had no way to tell which commit a deployed Streamlit instance was running.

The lookup is defensive by construction: it NEVER raises and NEVER blocks
startup. Any git failure (missing binary, non-zero exit, timeout, or OSError)
yields an ``unknown`` BuildInfo whose ``sha`` / ``short_sha`` / ``branch`` are
the literal string ``"unknown"`` and whose ``dirty`` is ``False``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

# Repository root is the parent of the ``src`` package directory, so git
# commands run from a stable, known location regardless of the process CWD.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Module-level memoization: the git lookup runs at most once per process.
_BUILD_INFO: "BuildInfo | None" = None


@dataclass(frozen=True)
class BuildInfo:
    """Immutable snapshot of the build provenance for a running instance.

    Attributes:
        sha: Full git commit SHA, or ``"unknown"``.
        short_sha: First 7 characters of ``sha``, or ``"unknown"``.
        branch: Current git branch name, or ``"unknown"``.
        dirty: True if the working tree has uncommitted changes.
        built_at: ISO 8601 UTC timestamp of the first ``get_build_info`` call.
        python_version: Interpreter version (e.g. ``"3.12.1"``).
        unknown: True when git metadata could not be resolved.
    """

    sha: str
    short_sha: str
    branch: str
    dirty: bool
    built_at: str
    python_version: str
    unknown: bool


def _run_git(args: list[str]) -> str:
    """
    Runs a git command from the repository root and returns stripped stdout.

    Args:
        args: Git CLI arguments (e.g. ``["rev-parse", "HEAD"]``).

    Returns:
        Stripped stdout on success, or the empty string on any failure
        (missing binary, non-zero exit, timeout, or OSError). Never raises.

    The lookup uses a short (2s) timeout and ``capture_output=True`` so a
    stalled or absent git cannot block process startup.
    """
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return (result.stdout or "").strip()


def _resolve_build_info() -> BuildInfo:
    """
    Resolves build metadata via git, falling back to an ``unknown`` record.

    Returns:
        A BuildInfo. On any git failure, an ``unknown`` BuildInfo is returned
        with ``sha`` / ``short_sha`` / ``branch`` == ``"unknown"`` and
        ``dirty`` == ``False``.

    The ``BUILD_SHA`` environment variable (used by CI) takes precedence over
    the git lookup for the commit SHA; branch / dirty still resolve via git.
    """
    python_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    env_sha = os.environ.get("BUILD_SHA", "").strip()
    if env_sha:
        branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
        dirty = bool(_run_git(["status", "--porcelain"]))
        return BuildInfo(
            sha=env_sha,
            short_sha=env_sha[:7],
            branch=branch,
            dirty=dirty,
            built_at=built_at,
            python_version=python_version,
            unknown=False,
        )

    sha = _run_git(["rev-parse", "HEAD"])
    if not sha:
        return BuildInfo(
            sha="unknown",
            short_sha="unknown",
            branch="unknown",
            dirty=False,
            built_at=built_at,
            python_version=python_version,
            unknown=True,
        )

    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
    dirty = bool(_run_git(["status", "--porcelain"]))

    return BuildInfo(
        sha=sha,
        short_sha=sha[:7],
        branch=branch,
        dirty=dirty,
        built_at=built_at,
        python_version=python_version,
        unknown=False,
    )


def get_build_info() -> BuildInfo:
    """
    Returns memoized build provenance for the running instance.

    The git lookup is performed at most once per process and cached in a
    module-level variable; subsequent calls return the cached value at no cost.

    Returns:
        BuildInfo: a frozen dataclass with ``sha``, ``short_sha``, ``branch``,
        ``dirty``, ``built_at`` (ISO 8601 UTC of the first call),
        ``python_version``, and ``unknown`` (True if git metadata could not be
        resolved). Never raises.
    """
    global _BUILD_INFO
    if _BUILD_INFO is None:
        _BUILD_INFO = _resolve_build_info()
    return _BUILD_INFO
