# Feature: Deploy Verification & Hygiene

**Status:** in progress
**Started:** 2026-10-02
**Branch:** main (feature branch pending user decision)

## Problem

The BYOK API key (`AQ.` modern Google AI Studio auth key) is valid and the RAG
pipeline works end-to-end, but the deployed app at
`https://analytical01.streamlit.app/` rejected it. Root causes:

1. The deployed build predates commit `36db361`, which added `AQ.` key support.
   The previous `SAFE_KEY_CHARS_PATTERN = ^[A-Za-z0-9_\-]+$` rejected the `.`
   in any `AQ.` key with *"La clave contiene caracteres inválidos"*.
2. The live URL is behind Streamlit viewer auth (`303` →
   `share.streamlit.io/-/auth/app` on every path except `/_stcore/health`), so an
   anonymous browser connects the websocket and renders a blank page. No automated
   verification of the live deployment is possible.
3. There is no way to tell, from the outside, which commit a running instance
   serves. "Did the redeploy land?" is unanswerable without dashboard access.

There is no `.streamlit/config.toml` and no CI at all.

## Non-goals

- Migrating off Streamlit Cloud (Vercel is incompatible with a long-running
  Streamlit websocket server; no rewrite is in scope).
- Re-ingesting books or changing the RAG retrieval logic.
- Any change to the API key itself.

## Acceptance criteria

1. The running app displays its own commit SHA (short) in the sidebar, so the
   live build is identifiable without dashboard access.
2. `.streamlit/config.toml` exists with explicit, minimal runtime configuration.
3. `scripts/smoke_live.py` verifies a live Streamlit deployment end-to-end:
   `/healthz`, the build stamp, BYOK key validation, and a RAG query.
4. `.github/workflows/deploy-smoke.yml` runs that smoke test on demand and on
   `main` pushes.
5. The `TEST_KEY_SUBSTRINGS` format-check bypass in `src/gemini_client.py` is
   removed without breaking any existing test.
6. Existing test suite still passes.

## Tasks

| # | Task | Work unit | Status |
|---|------|-----------|--------|
| 1 | Build stamp module + sidebar render | WU1 | pending |
| 2 | `.streamlit/config.toml` | WU1 | pending |
| 3 | Remove `TEST_KEY_SUBSTRINGS` bypass | WU1 | pending |
| 4 | Unit test for `build_info` | WU1 | pending |
| 5 | `scripts/smoke_live.py` live E2E | WU2 | pending |
| 6 | GitHub Actions workflow | WU2 | pending |
| 7 | Deployment + troubleshooting docs | WU2 | pending |

## Commits

_(work-unit commit SHAs recorded here as evidence)_

## Verification log

- `validate_api_key("AQ.Ab8RN6...")` → `(True, 'Clave válida...')` — HEAD local
- REST `generateContent` on `gemini-2.5-flash` with the same key → HTTP 200
- Local UI E2E (Playwright, port 8599): 🟢 badge + RAG answer with citation
  (Skoog 9ed, Cap. 18, p. 581) and "Fuentes Bibliográficas Consultadas (4)"
- `https://analytical01.streamlit.app/_stcore/health` → 200 (app alive)
- `https://analytical01.streamlit.app/` → 303 to viewer auth (anon blocked)