#!/usr/bin/env python3
"""
scripts/smoke_live.py - Standalone, CI-runnable smoke test for a deployed
Streamlit instance of the Química Analítica RAG portal.

USAGE
-----
    .venv/bin/python scripts/smoke_live.py --url https://example.streamlit.app \
        [--expect-sha 9ae4502] [--api-key "...", or env SMOKE_API_KEY] \
        [--timeout 120] [--headed] [--skip-browser] [--json]

WHAT EACH CHECK PROVES
----------------------
The checks run in order. The first two use only the stdlib (urllib) so they can
run in a minimal CI image with no browser. The browser-backed checks (3, 4, 5)
import Playwright lazily and degrade to SKIPPED when Playwright is missing or
when ``--skip-browser`` is passed.

1. health (stdlib, no credentials)
   ``GET <url>/healthz`` must return HTTP 200. This is Streamlit's *edge*
   liveness endpoint and is the one path that stays reachable anonymously
   even when viewer auth is on. IMPORTANT: do NOT substitute
   ``/_stcore/health`` here -- that path is itself gated behind
   ``share.streamlit.io/-/auth/app`` when viewer auth is enabled, so it would
   report every auth-protected deployment as unhealthy. A non-200 on
   ``/healthz`` means the instance is down or mis-routed. Note this proves
   the edge is serving, not that the Streamlit server booted; only the
   browser-backed build_stamp check proves the app itself renders.

2. no_auth_redirect (stdlib, no credentials)
   Anonymous ``GET <url>/`` must NOT redirect to the Streamlit sign-in gate.
   We detect a redirect to ``share.streamlit.io/-/auth/app`` both via the
   ``Location`` header of the initial response and via the final URL after
   following redirects.

   INTERPRETING VIEWER_AUTH_REQUIRED
   ---------------------------------
   If check 2 fails it reports the named finding ``VIEWER_AUTH_REQUIRED`` with
   the plain-language reason: "the app requires sign-in, so anonymous automated
   verification is impossible." This is a FAIL for the ``public`` verification
   goal but is *intentionally distinguishable* from a real outage. It does NOT
   mean the app is broken -- it means the deployment has viewer auth enabled and
   you must either disable it (see docs/deployment.md) or supply credentials /
   rely on an internal runner to exercise the browser checks. When this finding
   fires, checks 3-5 are SKIPPED rather than failed, because there is no
   anonymously reachable page to load.

3. build_stamp (browser, only when the page is reachable anonymously)
   Loads the page and reads the sidebar build stamp ``Build <sha> · <branch>``.
   Compares the 7-char short SHA against ``--expect-sha`` (prefix match).

     * PASS            - a stamp was found and it matches ``--expect-sha``.
     * STALE_BUILD     - a stamp was found but it does NOT match (you are
                         looking at an older deploy than the one you built).
     * NO_BUILD_STAMP  - the app rendered but shows no stamp at all, which
                         means the deployed build predates the build-stamp
                         work unit (commit 9ae4502) and cannot be verified.

4. api_key (browser, only when ``--api-key`` is supplied and page reachable)
   Pastes the key into the sidebar password input, presses Enter, and asserts
   the green validation badge ("Clave válida") appears. On failure it reports
   the exact failure message the app rendered.

5. rag (browser, only when ``--api-key`` is supplied and page reachable)
   Runs one real RAG question through the Tutor tab and asserts a non-empty
   answer with at least one bibliographic citation. Polls with a bounded
   timeout (default 120s, ``--timeout``).

SECURITY
--------
The API key is NEVER printed, not even truncated to more than its first 3
characters and its length. It is read from ``--api-key`` or, as a fallback, the
``SMOKE_API_KEY`` environment variable so it never has to appear in a shell
history or CI log echo. In CI, pass it exclusively through the environment.

EXIT CODES
----------
0 - every executed check was PASS or SKIP (with a documented reason).
1 - at least one executed check FAILED.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from typing import List, Optional

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
# Streamlit's edge liveness endpoint. Chosen over /_stcore/health because the
# latter is auth-gated whenever viewer sign-in is enabled, which would make a
# healthy-but-private deployment look like an outage.
HEALTH_PATH = "/healthz"
AUTH_GATE_MARKER = "share.streamlit.io/-/auth/app"
BUILD_STAMP_RE = re.compile(r"Build\s+([0-9a-f]{7,40})")
VALID_BADGE_TEXT = "Clave válida"
RAG_QUESTION = "Como se calcula el error relativo de una medicion de masa?"
CITATION_MARKER = "Fuentes Bibliográficas Consultadas"
USER_AGENT = "quimica-analitica-smoke/1.0 (+https://github.com/)"


@dataclass
class CheckResult:
    name: str
    status: str  # "PASS" | "FAIL" | "SKIP"
    reason: str
    finding: str = ""  # named finding code when applicable
    detail: str = ""   # extra context (never includes secrets)


# --------------------------------------------------------------------------- #
# HTTP probes (stdlib only)
# --------------------------------------------------------------------------- #
def _http_get(url: str, *, timeout: int, follow_redirects: bool):
    """
    Performs a GET request.

    Returns a tuple ``(status, final_url, location_header, body)``.

    When ``follow_redirects`` is False the request is configured to NOT follow
    redirects: a redirect status (3xx) is raised as ``urllib.error.HTTPError``
    and captured so we can inspect the ``Location`` header.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    if follow_redirects:
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
            return resp.getcode(), resp.geturl(), "", resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:  # pragma: no cover - surfaced as status
            return e.code, e.geturl(), "", e.read().decode("utf-8", "replace")
    else:
        class _NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *_args, **_kwargs):
                return None  # stop after the first redirect response

        opener = urllib.request.build_opener(_NoRedirect)
        try:
            resp = opener.open(req, timeout=timeout)
            return resp.getcode(), resp.geturl(), "", resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            location = e.headers.get("Location", "")
            return e.code, e.geturl(), location, e.read().decode("utf-8", "replace")


def check_health(base_url: str, timeout: int) -> CheckResult:
    """Check 1: GET <url>/healthz proves the edge is serving.

    A ``200`` is the canonical liveness signal. Defensively, if the probe still
    returns a ``303`` to the auth gate we still report the instance as alive --
    it answered us, so it is running -- and let ``no_auth_redirect`` carry the
    ``VIEWER_AUTH_REQUIRED`` finding. A connection error, timeout, or a
    non-redirect error status (4xx/5xx) is a genuine outage -> FAIL.

    This proves the edge responds, not that the Streamlit server booted; the
    browser-backed ``build_stamp`` check is what proves the app renders.
    """
    url = base_url.rstrip("/") + HEALTH_PATH
    try:
        status, _final, location, _body = _http_get(url, timeout=timeout, follow_redirects=False)
    except Exception as exc:  # DNS / TLS / connection refused / timeout
        return CheckResult("health", "FAIL", f"health probe error (instance unreachable): {exc}")
    if status == 200:
        return CheckResult("health", "PASS", f"instance is alive (HTTP 200 on {HEALTH_PATH})")
    if status in (301, 302, 303, 307, 308) and AUTH_GATE_MARKER in location:
        return CheckResult(
            "health",
            "PASS",
            f"instance is alive but behind viewer auth (HTTP 303 to auth gate on {HEALTH_PATH})",
        )
    return CheckResult("health", "FAIL", f"health probe returned HTTP {status}")


def check_no_auth_redirect(base_url: str, timeout: int) -> CheckResult:
    """
    Check 2: anonymous GET / must not redirect to the Streamlit auth gate.

    Detects the redirect both via the ``Location`` header (no-follow request)
    and via the final URL after redirects.
    """
    url = base_url.rstrip("/") + "/"
    # 1) No-follow: inspect the Location header on the initial response.
    try:
        status, _final, location, _body = _http_get(url, timeout=timeout, follow_redirects=False)
        initial_redirects = status in (301, 302, 303, 307, 308) and AUTH_GATE_MARKER in location
    except Exception:
        initial_redirects = False
    # 2) Follow redirects: inspect where we actually land.
    try:
        _status, final_url, _loc, _body = _http_get(url, timeout=timeout, follow_redirects=True)
        final_redirects = AUTH_GATE_MARKER in final_url
    except Exception:
        final_redirects = False

    if initial_redirects or final_redirects:
        return CheckResult(
            "no_auth_redirect",
            "FAIL",
            "app requires sign-in, so anonymous automated verification is impossible",
            finding="VIEWER_AUTH_REQUIRED",
        )
    return CheckResult(
        "no_auth_redirect",
        "PASS",
        "anonymous GET / did not redirect to the Streamlit auth gate",
    )


# --------------------------------------------------------------------------- #
# Browser-backed checks (Playwright, imported lazily)
# --------------------------------------------------------------------------- #
def _load_page(page, base_url: str, timeout: int) -> None:
    page.goto(base_url.rstrip("/") + "/", wait_until="domcontentloaded", timeout=timeout * 1000)
    # Wait until the sidebar has rendered its persistent header.
    page.wait_for_selector("text=Clave Google AI Studio", timeout=timeout * 1000)


def check_build_stamp(page, expect_sha: Optional[str], timeout: int) -> CheckResult:
    """Check 3: sidebar build stamp matches --expect-sha (prefix match)."""
    body = page.inner_text("body")
    match = BUILD_STAMP_RE.search(body)
    if not match:
        return CheckResult(
            "build_stamp",
            "FAIL",
            "app rendered but shows no build stamp (deployed build predates the build-stamp work unit)",
            finding="NO_BUILD_STAMP",
        )
    found_sha = match.group(1)
    if not expect_sha:
        return CheckResult(
            "build_stamp",
            "PASS",
            f"build stamp present (sha={found_sha}); no --expect-sha to compare against",
            detail=found_sha,
        )
    # Prefix match on the 7-char short SHA (robust whether expect_sha is short or full).
    if found_sha.startswith(expect_sha) or expect_sha.startswith(found_sha):
        return CheckResult(
            "build_stamp",
            "PASS",
            f"build stamp matches --expect-sha ({found_sha})",
            detail=found_sha,
        )
    return CheckResult(
        "build_stamp",
        "FAIL",
        f"deployed build ({found_sha}) does not match expected ({expect_sha})",
        finding="STALE_BUILD",
        detail=found_sha,
    )


def check_api_key(page, api_key: str, timeout: int) -> CheckResult:
    """Check 4: paste key, press Enter, assert the green 'Clave válida' badge."""
    pw = page.query_selector("input[type=password]")
    if pw is None:
        return CheckResult("api_key", "FAIL", "no password input found in sidebar", detail="")
    pw.fill(api_key)
    pw.press("Enter")
    try:
        page.wait_for_selector(f"text={VALID_BADGE_TEXT}", timeout=timeout * 1000)
    except Exception:
        pass
    body = page.inner_text("body")
    if VALID_BADGE_TEXT in body:
        return CheckResult("api_key", "PASS", "green validation badge 'Clave válida' appeared")
    # Otherwise capture the rendered failure message.
    detail = ""
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("🔴") or "inválida" in line.lower() or "caracteres inválidos" in line:
            detail = line
            break
    return CheckResult(
        "api_key",
        "FAIL",
        "validation badge 'Clave válida' did not appear; key was rejected",
        detail=detail,
    )


def check_rag(page, timeout: int) -> CheckResult:
    """Check 5: run one real RAG question and assert a cited answer."""
    try:
        page.get_by_role("tab", name="Tutor Inteligente").click(timeout=timeout * 1000)
    except Exception:
        # Fallback: click whatever tab contains the Tutor label.
        try:
            page.click("text=Tutor Inteligente", timeout=timeout * 1000)
        except Exception as exc:
            return CheckResult("rag", "FAIL", f"could not open Tutor tab: {exc}")
    chat = page.get_by_placeholder("Escribe tu duda sobre Química Analítica...")
    chat.fill(RAG_QUESTION)
    chat.press("Enter")

    # Poll for the citations drawer (implies a non-empty, cited answer).
    deadline = timeout
    import time
    start = time.time()
    citation_found = False
    answer_len = 0
    while time.time() - start < deadline:
        try:
            if page.query_selector(f"text={CITATION_MARKER}"):
                citation_found = True
                break
        except Exception:
            pass
        time.sleep(2)
    body = page.inner_text("body")
    answer_len = len(body.strip())
    if citation_found:
        return CheckResult(
            "rag",
            "PASS",
            "RAG question returned a non-empty answer with at least one bibliographic citation",
        )
    return CheckResult(
        "rag",
        "FAIL",
        "RAG question produced no bibliographic citation within the timeout",
        detail=f"rendered body length={answer_len}",
    )


def _await_stamp(
    page,
    base_url: str,
    expect_sha: Optional[str],
    timeout: int,
    stamp_wait: int,
) -> CheckResult:
    """Polls the build stamp until it matches, the deadline passes, or it matches nothing.

    Streamlit Cloud redeploys asynchronously, so a CI run triggered by a push
    will usually reach the app while the *previous* build is still serving.
    Reloading the page starts a fresh Streamlit session, which is what actually
    picks up a newly deployed build -- so the retry reloads rather than just
    re-reading the DOM. With ``stamp_wait <= 0`` this is a single check.
    """
    result = check_build_stamp(page, expect_sha, timeout)
    if stamp_wait <= 0 or result.status != "FAIL":
        return result
    if result.finding not in ("STALE_BUILD", "NO_BUILD_STAMP"):
        return result

    deadline = time.monotonic() + stamp_wait
    while time.monotonic() < deadline:
        time.sleep(min(20, max(1, int(deadline - time.monotonic()))))
        try:
            _load_page(page, base_url, timeout)
        except Exception:
            continue
        result = check_build_stamp(page, expect_sha, timeout)
        if result.status != "FAIL":
            result.detail = (result.detail + f"; converged after waiting up to {stamp_wait}s").strip("; ")
            return result
    return result


def run_browser_checks(
    base_url: str,
    expect_sha: Optional[str],
    api_key: Optional[str],
    timeout: int,
    headed: bool,
    stamp_wait: int = 0,
) -> List[CheckResult]:
    """Loads the page with Playwright and runs checks 3-5. Returns the results."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        reason = f"Playwright unavailable ({exc}); browser checks skipped"
        return [
            CheckResult("build_stamp", "SKIP", reason),
            CheckResult("api_key", "SKIP", reason),
            CheckResult("rag", "SKIP", reason),
        ]

    launch_args = ["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
    results: List[CheckResult] = []
    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not headed, args=launch_args)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            _load_page(page, base_url, timeout)

            results.append(_await_stamp(page, base_url, expect_sha, timeout, stamp_wait))
            if api_key:
                results.append(check_api_key(page, api_key, timeout))
                results.append(check_rag(page, timeout))
            else:
                results.append(CheckResult("api_key", "SKIP", "no --api-key supplied"))
                results.append(CheckResult("rag", "SKIP", "no --api-key supplied"))
    except Exception as exc:
        # If loading itself failed, mark the remaining checks as SKIP/FAIL clearly.
        if not results:
            results.append(CheckResult("build_stamp", "FAIL", f"browser load failed: {exc}"))
            results.append(CheckResult("api_key", "SKIP", "browser load failed"))
            results.append(CheckResult("rag", "SKIP", "browser load failed"))
        else:
            results.append(CheckResult("api_key", "SKIP", f"browser error: {exc}"))
            results.append(CheckResult("rag", "SKIP", f"browser error: {exc}"))
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
    return results


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def _key_hint(api_key: Optional[str]) -> Optional[str]:
    if not api_key:
        return None
    return f"{api_key[:3]}… (len={len(api_key)})"


def run(args) -> int:
    base_url = args.url.rstrip("/")
    expect_sha = args.expect_sha
    # API key: explicit flag, else SMOKE_API_KEY env var (never logged in full).
    api_key = args.api_key or os.environ.get("SMOKE_API_KEY") or None
    timeout = args.timeout

    results: List[CheckResult] = []

    # --- Check 1: health (always runs, no credentials) ---
    results.append(check_health(base_url, timeout))

    # --- Check 2: anonymous auth redirect ---
    results.append(check_no_auth_redirect(base_url, timeout))

    no_auth = results[-1]  # check 2 result
    page_reachable = not (no_auth.status == "FAIL" and no_auth.finding == "VIEWER_AUTH_REQUIRED")

    # --- Checks 3-5: browser-backed (only if page reachable & not skipped) ---
    if not page_reachable:
        reason = "browser stage skipped: app requires sign-in (VIEWER_AUTH_REQUIRED)"
        results.extend([
            CheckResult("build_stamp", "SKIP", reason),
            CheckResult("api_key", "SKIP", reason),
            CheckResult("rag", "SKIP", reason),
        ])
    elif args.skip_browser:
        reason = "browser stage skipped (--skip-browser)"
        results.extend([
            CheckResult("build_stamp", "SKIP", reason),
            CheckResult("api_key", "SKIP", reason),
            CheckResult("rag", "SKIP", reason),
        ])
    else:
        results.extend(
            run_browser_checks(
                base_url, expect_sha, api_key, timeout, args.headed, args.stamp_wait
            )
        )
        # If --skip-browser was not set but Playwright was unavailable, the
        # browser checks come back as SKIP (handled inside run_browser_checks).

    # --- Determine exit code ---
    failed = [r for r in results if r.status == "FAIL"]
    exit_code = 1 if failed else 0

    # --- Report ---
    if args.json:
        payload = {
            "url": base_url,
            "expect_sha": expect_sha,
            "api_key_provided": api_key is not None,
            "api_key_hint": _key_hint(api_key),
            "page_reachable_anonymously": page_reachable,
            "exit_code": exit_code,
            "checks": [asdict(r) for r in results],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        _print_human(results, base_url, expect_sha, api_key, page_reachable, exit_code)

    return exit_code


def _print_human(results, base_url, expect_sha, api_key, page_reachable, exit_code) -> None:
    print("=" * 78)
    print("QUÍMICA ANALÍTICA — LIVE SMOKE SUMMARY")
    print("=" * 78)
    print(f"URL              : {base_url}")
    print(f"Expect SHA      : {expect_sha or '(none)'}")
    print(f"API key         : {_key_hint(api_key) or '(none)'}")
    print(f"Anon reachable  : {'yes' if page_reachable else 'no (viewer auth)'}")
    print("-" * 78)
    name_w = max(len(r.name) for r in results)
    print(f"{'CHECK'.ljust(name_w)}  {'STATUS':<6}  {'FINDING':<18}  REASON")
    print("-" * 78)
    for r in results:
        print(f"{r.name.ljust(name_w)}  {r.status:<6}  {r.finding or '-':<18}  {r.reason}")
        if r.detail:
            print(f"{'':<{name_w}}  {'':<6}  {'':<18}  detail: {r.detail}")
    print("-" * 78)
    verdict = "PASS" if exit_code == 0 else "FAIL"
    print(f"VERDICT: {verdict} (exit {exit_code})")
    print("=" * 78)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Anonymous/CI smoke test for a deployed Streamlit instance.",
    )
    parser.add_argument("--url", required=True, help="Base URL of the deployed app (e.g. https://x.streamlit.app)")
    parser.add_argument("--expect-sha", default=None, help="Expected 7-char short git SHA of the build stamp")
    parser.add_argument("--api-key", default=None, help="BYOK API key (prefer env SMOKE_API_KEY instead)")
    parser.add_argument("--timeout", type=int, default=120, help="Per-stage timeout in seconds (default 120)")
    parser.add_argument("--headed", action="store_true", help="Run the browser in headed mode")
    parser.add_argument("--skip-browser", action="store_true", help="Skip all Playwright-backed checks")
    parser.add_argument(
        "--stamp-wait",
        type=int,
        default=0,
        help=(
            "Seconds to keep reloading the page waiting for the build stamp to converge on "
            "--expect-sha. Use after a push, because Streamlit Cloud redeploys asynchronously "
            "(default 0 = single check)."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
