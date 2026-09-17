#!/usr/bin/env python3
"""Standalone E2E Test Runner for Quimica Analitica Educational Portal & Chatbot.

Executes the complete 4-Tier verification suite with detailed tier-by-tier reporting,
timing diagnostics, and zero-cost mock assertion verification.

Usage:
    python3 tests/run_e2e_tests.py
    python3 tests/run_e2e_tests.py --tier 1
    python3 tests/run_e2e_tests.py --tier 2
    python3 tests/run_e2e_tests.py --tier 3
    python3 tests/run_e2e_tests.py --tier 4
    python3 tests/run_e2e_tests.py --verbose
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ANSI Colors
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
RESET = "\033[0m"


class TierResult:
    def __init__(self, name: str, directory: str):
        self.name = name
        self.directory = directory
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.duration = 0.0
        self.exit_code = 0


class MinimalPlugin:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def pytest_runtest_logreport(self, report):
        if report.when == "call":
            if report.passed:
                self.passed += 1
            elif report.failed:
                self.failed += 1
            elif report.skipped:
                self.skipped += 1


def run_tier(tier_name: str, test_dir: str, verbose: bool = False, failfast: bool = False) -> TierResult:
    result = TierResult(tier_name, test_dir)
    print(f"\n{BOLD}{CYAN}▶ Executing {tier_name} ({test_dir})...{RESET}")

    args = [test_dir, "-q"]
    if verbose:
        args.append("-v")
    if failfast:
        args.append("-x")

    plugin = MinimalPlugin()
    start_time = time.time()
    exit_code = pytest.main(args, plugins=[plugin])
    result.duration = time.time() - start_time
    result.exit_code = int(exit_code)
    result.passed = plugin.passed
    result.failed = plugin.failed
    result.skipped = plugin.skipped

    status_color = GREEN if result.exit_code == 0 and result.failed == 0 else RED
    status_str = "PASSED" if result.exit_code == 0 and result.failed == 0 else "FAILED"
    print(
        f"{status_color}{BOLD}✔ {tier_name}: {status_str} "
        f"({result.passed} passed, {result.failed} failed, {result.skipped} skipped in {result.duration:.2f}s){RESET}"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Química Analítica E2E Test Suite Runner")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], help="Run a specific test tier (1, 2, 3, or 4)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose test output")
    parser.add_argument("--failfast", "-x", action="store_true", help="Stop immediately on first failure")
    args = parser.parse_args()

    print(f"{BOLD}{MAGENTA}========================================================================={RESET}")
    print(f"{BOLD}{MAGENTA}       PORTAL EDUCATIVO QUÍMICA ANALÍTICA — E2E TEST SUITE RUNNER       {RESET}")
    print(f"{BOLD}{MAGENTA}========================================================================={RESET}")
    print(f"Runtime: Python {sys.version.split()[0]} | Zero-Cost BYOK Mock Harness: Active")
    print(f"Directory: {PROJECT_ROOT}\n")

    tier_configs = [
        ("Tier 1: Feature Isolation", "tests/tier1_features"),
        ("Tier 2: Boundary & Edge Cases", "tests/tier2_boundaries"),
        ("Tier 3: Pairwise Combinations", "tests/tier3_combinations"),
        ("Tier 4: Real-World Student Workflows", "tests/tier4_real_world"),
    ]

    selected_tiers = []
    if args.tier:
        selected_tiers = [tier_configs[args.tier - 1]]
    else:
        selected_tiers = tier_configs

    total_start = time.time()
    results: list[TierResult] = []

    for name, dir_path in selected_tiers:
        full_dir = os.path.join(PROJECT_ROOT, dir_path)
        if not os.path.exists(full_dir):
            print(f"{RED}Error: Directory '{full_dir}' not found.{RESET}")
            return 1
        res = run_tier(name, full_dir, verbose=args.verbose, failfast=args.failfast)
        results.append(res)
        if res.exit_code != 0 and args.failfast:
            break

    total_duration = time.time() - total_start
    total_passed = sum(r.passed for r in results)
    total_failed = sum(r.failed for r in results)
    total_skipped = sum(r.skipped for r in results)
    all_passed = (total_failed == 0) and all(r.exit_code == 0 for r in results)

    # Print Summary Dashboard
    print(f"\n{BOLD}========================================================================={RESET}")
    print(f"{BOLD}                        E2E EXECUTION DASHBOARD                          {RESET}")
    print(f"{BOLD}========================================================================={RESET}")
    for r in results:
        status_color = GREEN if r.exit_code == 0 and r.failed == 0 else RED
        status_text = "PASS" if r.exit_code == 0 and r.failed == 0 else "FAIL"
        print(f"  {status_color}[{status_text}]{RESET} {r.name:<38} | {r.passed:>3} passed | {r.failed:>2} failed | {r.duration:>5.2f}s")

    print(f"{BOLD}-------------------------------------------------------------------------{RESET}")
    summary_color = GREEN if all_passed else RED
    verdict = "ALL TIERS PASSED - SUITE 100% GREEN" if all_passed else "FAILURES DETECTED IN TEST RUN"
    print(
        f"{summary_color}{BOLD}VERDICT: {verdict}\n"
        f"TOTALS : {total_passed} Passed | {total_failed} Failed | {total_skipped} Skipped | Duration: {total_duration:.2f}s{RESET}"
    )
    print(f"{BOLD}========================================================================={RESET}\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
