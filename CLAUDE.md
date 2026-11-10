# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

The app is implemented and reviewed (steps 1–4 in `PROMPTS.md`). It is not yet pushed to GitHub or deployed. `PRD.md` holds the requirements, and docs are written in Korean. The app UI and AI output are Korean too. The only PRD item left out on purpose is F9 (camera input, a "Could" item).

## What this is

A single-file Streamlit app (`app.py`). A user uploads a face photo and an OpenAI vision model returns a for-fun physiognomy (관상) reading. It is meant to be deployed from GitHub to Streamlit Community Cloud.

## Commands

- Setup: `python -m venv .venv`, activate it, then `pip install -r requirements.txt`
- Run: `.venv\Scripts\streamlit.exe run app.py` (http://localhost:8501 by default, and another project may already be using that port; use `--server.port`)
- There is no test or lint setup. Verify with Playwright. To exercise error paths without spending API credits, point the app at a local mock server (`OPENAI_BASE_URL=http://127.0.0.1:9000/v1 OPENAI_API_KEY=x`). The OpenAI SDK reads both variables, and `load_dotenv()` does not override variables that are already set.
- Changes to `.streamlit/config.toml` (theme, `maxUploadSize`) need a server restart. Changes to `app.py` hot-reload.

## Architecture notes

- Flow: upload → Pillow (EXIF-rotate, RGB, longest side ≤1024px) → base64 JPEG data URI → `chat.completions` with system prompt + image (`detail: "low"`) → the result is split on `## ` headings and shown as one bordered card per section.
- Config lookup (`get_config`): `st.secrets` first, then env vars loaded from `.env`, falling back to the lowercase variable name. The lowercase fallback exists because the user's `.env` uses `openai_api_key`, which only works by accident on Windows otherwise. `OPENAI_MODEL` defaults to `gpt-4o-mini`.
- `analyze_face` converts every OpenAI failure (auth, rate limit, connection, bad request, status error, refusal, empty reply) into a `RuntimeError` with a user-facing Korean message. The UI shows only that message, never a traceback.
- Results are cached in `st.session_state["results"]` keyed by the SHA-256 of the uploaded bytes. That cache is what prevents duplicate API calls on double-clicks and reruns. A cached "no face" result is deliberately retried on the next click.
- The prompt returns exactly `NO_FACE_MESSAGE` when no face is found. The UI detects it by substring and shows a warning instead of cards and the download button.
- The token limit uses `max_completion_tokens`, since newer models reject `max_tokens`.
- Uploads are limited to 5MB twice: `server.maxUploadSize = 5` in `config.toml` (client-side, also drives the uploader label) and a `MAX_UPLOAD_BYTES` check in code.
- UI styling is a single `STYLE` CSS block in `app.py` plus the theme in `.streamlit/config.toml`. Streamlit's `data-testid` names differ between versions (for example there is no `stVerticalBlockBorderWrapper` in 1.67), so check the real DOM before writing selectors.

## Constraints

- `.env` is gitignored and must stay out of commits. Never read or print its contents. Keep `.env.example` as the template.
- Keep the app a single-file Streamlit app. No login, no database, no result persistence (PRD non-goals). Uploaded images are never written to disk.
- Always show the "for entertainment only" disclaimer and the notice that photos are sent to OpenAI.
