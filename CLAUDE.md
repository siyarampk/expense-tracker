# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## About this project

**Spendly** is a single-user personal expense tracker ("track every rupee") built as a teaching scaffold: most backend logic lives in placeholder stubs that are meant to be implemented progressively.

- **App entry point:** `app.py` — a single-file Flask app; `python app.py` starts the dev server on `http://127.0.0.1:5001` (debug mode enabled). Use the existing venv: `source venv/bin/activate && python app.py`.
- **Database:** `database/db.py` — implements `get_db()` (SQLite connection with `row_factory` and foreign keys enabled), `init_db()` (CREATE TABLE IF NOT EXISTS), and `seed_db()` (sample dev data). The DB file is `expense_tracker.db` in the repo root and is gitignored.
- **UI:** Jinja2 templates (`templates/`) + vanilla CSS (`static/css/style.css`) + vanilla JS (`static/js/main.js`). Design uses the DM Serif Display / DM Sans font pair with a green/earth accent palette (`--accent`, `--accent-2`).

## How to run, lint, and test

- **Run the server:**
  ```bash
  source venv/bin/activate && python app.py
  ```
- **Run tests (as the test suite is added for each curriculum step):**
  ```bash
  source venv/bin/activate && pytest
  source venv/bin/activate && pytest tests/test_<step>.py::test_<name>
  ```
  (There is no `tests/` directory yet — it is created as each step's tests are written.)
- **Install dependencies:** `source venv/bin/activate && pip install -r requirements.txt`
- **Rebuild the dev DB** (e.g. after changing schema in `database/db.py`): delete `expense_tracker.db`, then import `database.db` and call `init_db()`.

`requirements.txt` pins: flask, werkzeug, pytest, pytest-flask.

## High-level architecture

**Flask app (`app.py`)** — routes are grouped into two blocks:
- Implemented: `/` landing, `/register`, `/login` (all GET, returning rendered templates).
- Placeholders for the teaching curriculum, to be implemented next: `/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`.

**Database (`database/db.py`)** — thin SQLite helper module. `get_db()` returns a `sqlite3.Connection` with `row_factory = sqlite3.Row` and `PRAGMA foreign_keys = ON`; `init_db()` creates the tables; `seed_db()` inserts sample rows. Add new helper functions (e.g. user registration/validation, expense create/read/update/delete) here so the app layer stays thin.

**Templates (`templates/`)** — `base.html` is the master layout (navbar, footer, blocks: `title`, `head`, `content`, `scripts`). `landing.html`, `login.html`, `register.html` extend it. Note: `login.html` and `register.html` render an optional `error` variable and POST to the hardcoded `/login` and `/register` endpoints (these POST handlers don't exist yet in `app.py`).

**Static assets** — `static/css/style.css` holds the full design system (CSS custom properties, reset, layout sections, responsive breakpoints at 900px and 600px). `static/js/main.js` is intentionally empty for you to add frontend behavior.

## Data model to implement (expense tracker domain)

Based on the template hints (categories: Bills, Food, Health, Transport) and the curriculum, the app needs at least:

- `users` — id, name, email (unique), password hash. Register/login/auth session.
- `expenses` — id, user_id (FK), amount, category, date, description, created_at.

Profile and expense CRUD will query via `get_db()`, apply `user_id` scoping so one user can't see another's rows, and render results back into templates (a dashboard view is the next natural template to add beyond the four that exist).

## Working with git

- Current branch: `feature`. PRs should target `main`.
- Commit messages must end with: `Co-Authored-By: Claude Code <noreply@anthropic.com>`
- The recent history includes a recovery commit ("Restore expense tracker files after rebase accident") — if the working tree diverges from expectation, compare against `main` with `git diff main`.

## Notes for implementation

- Add a dashboard/home view for logged-in users (expense list by date, category totals, monthly summary) — the hero mock in `landing.html` shows the kind of visual (category bars, ₹ amounts, "March 2026" label) the final product should replicate.
- Passwords should be hashed at registration and verified at login (never store plain text); keep the existing form fields (`name`, `email`, `password`) in register and (`email`, `password`) in login.
- Flask's `url_for()` is used throughout templates, so new routes should be registered with a name used consistently in templates.
- Currency is INR (`₹`); amounts in templates are formatted with thousands separators (e.g. `₹12,450`).
