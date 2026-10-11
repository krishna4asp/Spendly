# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
# Activate the virtual environment (Windows)
venv\Scripts\activate

# Run the dev server (port 5001)
python app.py
```

The app runs at `http://localhost:5001`. The Flask dev server auto-reloads on file changes.

## Running tests

```bash
pytest
# Run a single test file
pytest tests/test_routes.py
```

## Architecture

This is a Flask app structured as a single-file backend with a flat template/static layout.

- **`app.py`** — all routes in one file. Currently only GET routes exist; POST routes for auth and expense CRUD are stub placeholders marked "coming in Step N". The app uses `render_template` only — no JSON API.
- **`database/db.py`** — currently a stub. Will contain `get_db()` (SQLite connection with row factory + foreign keys), `init_db()` (CREATE TABLE IF NOT EXISTS), and `seed_db()`. Not yet wired into `app.py`.
- **`templates/base.html`** — global layout shell: Google Fonts (`DM Serif Display` + `DM Sans`), `style.css`, navbar, `{% block content %}`, footer (with `/terms` and `/privacy` links), and a `{% block scripts %}` after the main script tag.
- **`static/css/style.css`** — single consolidated stylesheet. CSS custom properties on `:root` define the full design token set (`--ink`, `--accent` #1a472a, `--paper`, `--font-display`, etc.). Sections are labelled with banner comments: Variables, Reset, Navbar, Hero, Dashboard mock, Video modal, Features, CTA, Auth pages, Static pages, Footer, Responsive.
- **`static/js/main.js`** — currently a stub.

## Template conventions

- All pages extend `base.html` via `{% extends "base.html" %}` and fill `{% block content %}`.
- Landing page also fills `{% block scripts %}` for its video modal JS (vanilla IIFE, no libraries).
- Static/legal pages (terms, privacy) use `.static-page` / `.static-page-inner` / `.static-page-body` CSS classes.
- Auth pages (login, register) use `.auth-page` / `.auth-card` CSS classes.

## CSS conventions

- Never add a separate stylesheet; everything goes in `static/css/style.css`.
- New component styles go in a new labelled section (`/* --- Component name --- */`) before the `/* Responsive */` block at the bottom.
- The two responsive breakpoints are `@media (max-width: 900px)` and `@media (max-width: 600px)`, both consolidated at the end of the file.

## Git commits on Windows

Windows Git Bash chokes on single quotes inside `-m "..."`. Always use the heredoc form:

```bash
git commit -m "$(cat <<'EOF'
your message here
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```
