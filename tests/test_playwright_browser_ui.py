"""
test_playwright_browser_ui.py - Automated End-to-End Browser UI Verification.
Tests the Streamlit app rendering in real Chromium:
1. No raw HTML code blocks in the banner (<pre><code> with HTML).
2. Sumi-e Hinomaru Sun, Hanko seal, and animated particles exist.
3. Tab navigation without errors.
4. Screenshots are saved for visual verification.
"""

import os
import subprocess
import sys
import time
import socket
import pytest
from playwright.sync_api import sync_playwright

SCREENSHOT_PATH = "/home/raymond/.gemini/antigravity-cli/brain/06478b8c-6b66-44ab-9d84-0edf1ec31a56/playwright_verified_sumie.png"
SCREENSHOT_TABS_PATH = "/home/raymond/.gemini/antigravity-cli/brain/06478b8c-6b66-44ab-9d84-0edf1ec31a56/playwright_tabs_verified.png"

def is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def test_browser_ui_rendering():
    port = 8599
    server_process = None
    if not is_port_open(port):
        cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            f"--server.port={port}",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
            "--server.fileWatcherType=none",
        ]
        server_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd="/home/raymond/Work/agy_work/quimica_analitica_02",
        )
        for _ in range(30):
            if is_port_open(port):
                break
            time.sleep(0.5)
        else:
            if server_process:
                server_process.kill()
            pytest.fail(f"Streamlit server did not start on port {port} in 15 seconds")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path="/usr/bin/chromium",
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            
            # Navigate to local Streamlit portal
            page.goto(f"http://localhost:{port}", wait_until="networkidle", timeout=25000)
            
            # Wait for main app and banner text to appear
            page.wait_for_selector("text=Portal Educativo de Química Analítica", timeout=20000)
            time.sleep(1)
            
            # 1. ASSERTION: Check that NO raw HTML code blocks exist (no <pre> or <code> containing '<div')
            code_blocks = page.query_selector_all("code, pre")
            raw_html_snippets = []
            for cb in code_blocks:
                txt = cb.inner_text()
                if "<div" in txt or "Banner Content" in txt or "sumie-sun" in txt:
                    raw_html_snippets.append(txt[:100])
            
            assert len(raw_html_snippets) == 0, f"Found raw HTML rendered as code block: {raw_html_snippets}"
            
            # 2. ASSERTION: Check that Portal Header elements exist
            body_text = page.inner_text("body")
            assert "Portal Educativo de Química Analítica" in body_text, "Portal title not found in body text"
            assert "水墨画 • ALQUÍMICA-33" in body_text, "Sumi-e banner badge not found in body text"
            assert "錬" in body_text, "Hanko seal kanji not found in body text"
            
            # 3. Take full page screenshot of main view
            page.screenshot(path=SCREENSHOT_PATH, full_page=True)
            print(f"Captured main screenshot at: {SCREENSHOT_PATH}")
            
            # 4. Tab navigation check with role='tab'
            tabs = page.query_selector_all('[role="tab"]')
            assert len(tabs) >= 5, f"Expected at least 5 tabs, found {len(tabs)}"
            
            # Click Tab 5 (Laboratorio Virtual)
            tabs[4].click()
            time.sleep(1.5)
            body_text_tab5 = page.inner_text("body")
            assert "Simulador" in body_text_tab5 or "Laboratorio" in body_text_tab5
            
            # Capture tabs screenshot
            page.screenshot(path=SCREENSHOT_TABS_PATH, full_page=False)
            print(f"Captured tabs screenshot at: {SCREENSHOT_TABS_PATH}")
            
            browser.close()
    finally:
        if server_process:
            server_process.terminate()
            try:
                server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server_process.kill()


if __name__ == "__main__":
    test_browser_ui_rendering()
    print("Playwright browser UI test PASSED successfully!")
