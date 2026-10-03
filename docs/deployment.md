# Deployment & Operations Guide — Portal RAG de Química Analítica

Operator-facing troubleshooting for the live Streamlit deployment. Read this before
escalating a "the app is broken" report: most incidents are a stale build, viewer
auth, a bad BYOK key, or missing source PDFs on the cloud instance — not a code bug.

---

## 1. How Streamlit Cloud picks up a change

Streamlit Community Cloud redeploys **automatically from the connected repository and
branch**. Being logged into GitHub in your browser has **nothing** to do with it. The
app pulls the code from the repo; your local login only affects what *you* see in the
Cloud dashboard.

Two things must be correct for an update to land:

- The app points at the **right repository** (Settings → App settings → Repository).
- The app points at the **right branch** (the same `main` branch that received the push).

If you pushed to `main` but the app still serves old behavior, the branch mapping is
the first thing to check.

---

## 2. Force a redeploy and confirm the new build landed

1. Open the app in Streamlit Cloud and go to **Settings → Redeploy** (rebuilds from the
   current repo/branch).
2. Then click **Reboot** to restart the running process.
3. **Confirm the new build actually landed**: open the deployed app, look at the sidebar
   footer. It renders a stamp like:

   ```
   Build 9ae4502 · main
   ```

   Compare that short SHA to your local tree:

   ```bash
   git rev-parse --short HEAD
   ```

   If the sidebar stamp matches the commit you just pushed, the new build is live. If it
   shows an older SHA, the redeploy did not pick up your change (wrong repo/branch, or
   the deploy is still in progress).

> The build stamp is the *only* reliable way to tell which commit a live instance is
> serving. This is exactly why it was added (work unit 1, commit `9ae4502`).

---

## 3. Is the app publicly reachable?

Probe the three endpoints from your machine:

```bash
# Liveness probe — the ONLY path that stays anonymous when viewer auth is on.
curl -sI https://analytical01.streamlit.app/healthz

# Anonymous page load — gated by viewer auth when sign-in is on.
curl -sI https://analytical01.streamlit.app/

# App-level health — ALSO gated when viewer auth is on. Do not use it as an
# anonymous liveness probe; it reports an auth-protected deployment as unhealthy.
curl -sI https://analytical01.streamlit.app/_stcore/health
```

- `GET /healthz` returning `200` means the **edge is serving**. This is Streamlit's
  own liveness endpoint and it is not behind the auth gate, so it is the one reliable
  anonymous check.
- `GET /` returning `303` and a `Location:` of
  `https://share.streamlit.io/-/auth/app?...` means **viewer sign-in is enabled**.
  Anonymous visitors (and automated smoke tests) are bounced to the sign-in page, so the
  page renders blank for them.
- `GET /_stcore/health` is the *app-level* health path. When viewer auth is enabled it
  returns `303` too, so a `200` there is only meaningful once the app is public.

> **Edge vs. app.** `/healthz` only proves the edge answers. It does **not** prove the
> Streamlit server booted — an instance can answer `/healthz` while the app itself
> fails to import. Only the browser-backed `build_stamp` check proves the app renders,
> and that check requires the deployment to be public.

**How to turn viewer auth off:** in Streamlit Cloud, go to **Settings → App settings →
Viewer authentication** and switch it **off** (or set "Who can view this app" to
"Anyone with the link" if you want public access without a login wall). After changing
it, **Redeploy + Reboot**.

> The automated smoke script reports this exact condition as the named finding
> `VIEWER_AUTH_REQUIRED`. That is a distinct, non-outage result: the app is up, it just
> requires sign-in, so anonymous verification is impossible. See
> `scripts/smoke_live.py` for interpretation.

---

## 4. The failure mode that motivated this doc: stale build rejects modern keys

A valid, modern API key was once rejected by the deployed app with
`"La clave contiene caracteres inválidos"` even though the key was correct. Root cause:
the deployed build was **older than commit `36db361`**, which is where modern `AQ.`
Google AI Studio keys were first supported. The old charset pattern excluded the dot
(`.`), so any `AQ.…` key looked "invalid" to that build.

How to tell a **stale build** from a **genuinely bad key**:

| Observation | Stale build (old commit) | Genuinely bad key |
| --- | --- | --- |
| Sidebar stamp SHA | older than `36db361` | any / current |
| `AIzaSy…` classic key | accepted | rejected only if truly invalid |
| `AQ.…` modern key | rejected ("caracteres inválidos") | accepted |
| Fix | redeploy to a current commit (see §2) | obtain a fresh key from Google AI Studio |

Rule of thumb: if `AIzaSy…` works but `AQ.…` is rejected, you are on a stale build.
If **both** are rejected, the key itself is bad/expired/quota-dead.

---

## 5. Accepted API key formats

Both formats are accepted by the current build:

- **Classic:** `AIzaSy…` (legacy Google API key format).
- **Modern:** `AQ.…` (Google AI Studio keys; note the literal dot after `AQ`).

The key is **BYOK** (Bring Your Own Key) and **per-student**. Never store a real key in
the repository. The smoke test reads it from the `SMOKE_API_KEY` environment variable
and never prints it.

---

## 6. Why Vercel is not a valid target

This app is a **long-running Streamlit websocket server**, not a stateless serverless
function. Vercel (and similar FaaS platforms) terminate long-lived websocket connections
and impose strict execution-time limits, so the Streamlit runtime cannot serve a
persistent session there. Do not attempt a Vercel deploy.

Realistic alternatives to Streamlit Community Cloud:

- **Streamlit Community Cloud (public)** — the current target; free, simplest, redeploys
  from the repo/branch automatically.
- **Hugging Face Spaces (Docker)** — use a `Dockerfile` SDK space; good for more control
  and longer-running processes.
- **Render** — a web service with a persistent process; works for long-running Streamlit
  servers (configure the start command to `streamlit run app.py`).

---

## 7. Operational notes

- **`books/` is gitignored.** The cloud instance has **no source PDFs**. The RAG works
  anyway because the prebuilt `data/quimica_analitica.db` (BM25/FTS5 index) **is
  tracked** in the repo. Re-ingestion (`scripts/ingestion`) **cannot run on the cloud
  instance** — there are no PDFs to ingest there. To refresh the corpus, rebuild the DB
  locally (where `books/` exists) and commit `data/quimica_analitica.db`.
- **API key is BYOK and per-student.** The host pays $0 in tokens. Never commit a real
  key; the portal never stores it outside the ephemeral browser session.

---

## 8. Troubleshooting table (symptom → cause → action)

| Symptom | Likely cause | Action |
| --- | --- | --- |
| `curl /healthz` ≠ 200 | Instance down / wrong URL / routing | Check Cloud dashboard; Redeploy + Reboot |
| `curl /` returns `303` → `share.streamlit.io/-/auth/app` | Viewer auth enabled | Settings → Viewer authentication off; Redeploy |
| App loads but sidebar shows old `Build <sha>` | Stale deploy | Confirm repo/branch; Settings → Redeploy + Reboot; compare stamp to `git rev-parse --short HEAD` |
| `AQ.…` key rejected with "caracteres inválidos" | Build older than `36db361` | Redeploy to a current commit |
| Both `AIzaSy…` and `AQ.…` rejected | Bad/expired/quota-dead key | Issue a fresh key at Google AI Studio |
| Sidebar shows "Build desconocido" | Build-info lookup failed (no git at runtime) | Expected on some hosts; not fatal, but stamp unverifiable |
| RAG answers but cites nothing | DB missing/outdated or key lacks quota | Rebuild `data/quimica_analitica.db` locally; check key quota |
| RAG empty / timeout | No valid API key or network/quota | Verify key validity; check Google AI Studio status |
| Tutor tab blank for anonymous users | Viewer auth or websocket not connecting | See §3; check `curl -sI <url>/` for a `303` |
| Re-ingestion fails on cloud | `books/` not present in cloud instance | Run ingestion locally; commit the DB |

---

## 9. Automated verification

The smoke script `scripts/smoke_live.py` is the executable form of this guide. It checks
health, viewer-auth redirect, build stamp, optional BYOK key validation, and an optional
real RAG question. In CI it runs via `.github/workflows/deploy-smoke.yml` on every push
to `main` (and manually via `workflow_dispatch`). See the script's module docstring for
the exact meaning of each check and the `VIEWER_AUTH_REQUIRED` finding.
