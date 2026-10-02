"""tests/test_build_info.py - Build provenance metadata tests.

Mirrors the pytest + monkeypatch style used in tests/conftest.py. Confirms
that get_build_info() resolves known git metadata, degrades gracefully to an
``unknown`` record on every git failure mode, honors the BUILD_SHA CI override,
and memoizes the lookup (same built_at across calls).
"""

from __future__ import annotations

import subprocess

import pytest

from src import build_info
from src.build_info import BuildInfo, get_build_info


class _FakeResult:
    """Minimal stand-in for subprocess.CompletedProcess."""

    def __init__(self, stdout: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.returncode = returncode


def _fake_run_ok(cmd, **kwargs) -> _FakeResult:
    """Simulates a working git with a known HEAD / branch and clean tree."""
    if cmd == ["git", "rev-parse", "HEAD"]:
        return _FakeResult(stdout="57ed7c5abcdef1234567890abcdef1234567890")
    if cmd == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
        return _FakeResult(stdout="main")
    if cmd == ["git", "status", "--porcelain"]:
        return _FakeResult(stdout="")
    return _FakeResult()


def test_known_git_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """Known git metadata resolves to a populated, non-unknown BuildInfo."""
    monkeypatch.setattr(build_info, "_BUILD_INFO", None)
    monkeypatch.setattr(build_info.subprocess, "run", _fake_run_ok)

    info = get_build_info()
    assert info.unknown is False
    assert len(info.short_sha) == 7
    assert info.branch == "main"
    assert info.dirty is False


def test_missing_git_binary_returns_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing git binary (FileNotFoundError) yields an unknown record, no raise."""

    def _boom(*args, **kwargs):
        raise FileNotFoundError("git: command not found")

    monkeypatch.setattr(build_info, "_BUILD_INFO", None)
    monkeypatch.setattr(build_info.subprocess, "run", _boom)

    info = get_build_info()
    assert info.unknown is True
    assert info.sha == "unknown"
    assert info.branch == "unknown"
    assert info.dirty is False


def test_nonzero_returncode_returns_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-zero git exit code yields an unknown record, no exception."""

    def _fail(cmd, **kwargs):
        return _FakeResult(stdout="", returncode=128)

    monkeypatch.setattr(build_info, "_BUILD_INFO", None)
    monkeypatch.setattr(build_info.subprocess, "run", _fail)

    info = get_build_info()
    assert info.unknown is True
    assert info.sha == "unknown"
    assert info.branch == "unknown"
    assert info.dirty is False


def test_empty_stdout_returns_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty git stdout yields an unknown record, no exception."""

    def _empty(cmd, **kwargs):
        return _FakeResult(stdout="", returncode=0)

    monkeypatch.setattr(build_info, "_BUILD_INFO", None)
    monkeypatch.setattr(build_info.subprocess, "run", _empty)

    info = get_build_info()
    assert info.unknown is True
    assert info.sha == "unknown"
    assert info.branch == "unknown"
    assert info.dirty is False


def test_build_sha_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """BUILD_SHA overrides the git lookup for the commit SHA."""
    monkeypatch.setattr(build_info, "_BUILD_INFO", None)
    monkeypatch.setenv("BUILD_SHA", "abcdef1234567890abcdef1234567890abcdef12")
    monkeypatch.setattr(build_info.subprocess, "run", _fake_run_ok)

    info = get_build_info()
    assert info.unknown is False
    assert info.sha == "abcdef1234567890abcdef1234567890abcdef12"
    assert info.short_sha == "abcdef1"
    assert info.branch == "main"


def test_memoization_same_built_at(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two calls return the same built_at (lookup memoized in module state)."""
    monkeypatch.setattr(build_info, "_BUILD_INFO", None)
    monkeypatch.setattr(build_info.subprocess, "run", _fake_run_ok)

    info1 = get_build_info()
    info2 = get_build_info()
    assert info1 is info2
    assert info1.built_at == info2.built_at
