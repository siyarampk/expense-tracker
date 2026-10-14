# Spec: Backend Connection

## Overview
Step 5 replaces all hardcoded data in the `/profile` route with live queries
against the SQLite database. The profile page currently renders a static demo
user, fixed summary stats, a hand-typed transaction list, and a hardcoded
category breakdown. This step wires those four sections to real data so that
every logged-in user sees their own expenses. Three parallel subagents handle
the three independent data concerns — transaction history, summary stats, and
category breakdown — before being integrated into the single `/profile` route.

## Depends on
- Step 1: Database setup (tables and `get_db()` exist)
- Step 2: Registration (users are stored in the database)
- Step 3: Login / Logout (`session["user_id"]` is set on login)
- Step 4: Profile page static UI (template already renders all four sections)

## Routes
No new routes. The existing `GET /profile` route is modified.

## Database changes
No database changes. The `users` and `expenses` tables already have all
required columns (`user_id`, `amount`, `category`, `date`, `description`,
`created_at`).

## Templates
- **Modify**: `templates/profile.html`
  - Amounts must be rendered with the ₹ symbol (Indian Rupee).
  - All four dynamic sections (user info, summary stats, transaction list,
    category breakdown) are already present — no structural changes needed,
    only the Jinja variables they consume are now real.

## Files to change
- `app.py` — replace hardcoded data in the `profile()` view with DB queries
- `templates/profile.html` — confirm ₹ symbol is used for all currency display

## Files to create
- `database/queries.py` — pure query helpers (no Flask imports), one function
  per data concern:
  - `get_user_by_id(user_id)` → dict with `name`, `email`, `member_since`
  - `get_summary_stats(user_id)` → dict with `total_spent`, `transaction_count`, `top_category`
  - `get_recent_transactions(user_id, limit=10)` → list of dicts, each with `date`, `description`, `category`, `amount`
  - `get_category_breakdown(user_id)` → list of dicts, each with `name`, `amount`, `pct` (percentage of total, rounded to nearest int)

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Foreign keys PRAGMA must be enabled on every connection (already done in `get_db()`)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Currency must always display as ₹ — never £ or $
- `member_since` must be derived from `users.created_at` and formatted as
  "Month YYYY" (e.g. "January 2026")
- `pct` values in category breakdown must sum to 100; use integer rounding and
  adjust the largest category to absorb any rounding remainder
- If a user has no expenses, summary stats should return zeros and empty lists
  rather than raising exceptions
- Query helpers in `database/queries.py` must call `get_db()` internally and
  close the connection before returning

## Tests to write

### Unit tests
File: `tests/test_backend_connection.py`

| Function | Input | Expected output |
|---|---|---|
| `get_user_by_id` | valid `user_id` | dict with correct `name`, `email`, `member_since` |
| `get_user_by_id` | non-existent id | `None` |
| `get_summary_stats` | `user_id` with expenses | correct `total_spent`, `transaction_count`, `top_category` |
| `get_summary_stats` | `user_id` with no expenses | `{"total_spent": 0, "transaction_count": 0, "top_category": "—"}` |
| `get_recent_transactions` | `user_id` with expenses | list ordered newest-first, each item has `date`, `description`, `category`, `amount` |
| `get_recent_transactions` | `user_id` with no expenses | empty list |
| `get_category_breakdown` | `user_id` with expenses | list ordered by `amount` desc; `pct` values are integers summing to 100 |
| `get_category_breakdown` | `user_id` with no expenses | empty list |

### Route tests
`GET /profile` — unauthenticated:
- Redirects to `/login` (302)

`GET /profile` — authenticated as a freshly registered user:
- Returns 200
- Response contains the registered user's name
- Response contains the registered user's email
- Response contains ₹ symbol
- A new user with no expenses shows ₹0.00 total spent, 0 transactions, and
  an empty category breakdown

## Definition of done
- [ ] Registering a new user and visiting `/profile` shows that user's name
  and email on the profile page
- [ ] Total spent displayed for a new user is ₹0.00
- [ ] Transaction count displayed for a new user is 0
- [ ] Category breakdown is empty for a new user, with no errors
- [ ] After adding expenses, total spent, transaction count, top category,
  and category breakdown all update to reflect them
- [ ] Transaction list shows rows ordered newest date first
- [ ] All amounts on the page display the ₹ symbol