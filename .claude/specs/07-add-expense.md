# Spec: Add Expense

## Overview
Step 7 implements the first expense-mutation route: `/expenses/add`. So far
expenses only come from `seed_db()` — there is no way for a logged-in user to
record a new transaction. This step replaces the `/expenses/add` placeholder
with a real `GET` (render form) / `POST` (validate + insert) flow, wires it to
a new `create_expense` helper in `database/db.py`, and links the existing
"+ Add Expense" button on the profile page to a working form. Edit and delete
(Steps 8–9) remain placeholders.

## Depends on
- Step 1: Database setup (`expenses` table must exist)
- Step 3: Login/logout (route must be behind an authenticated session)
- Step 4: Profile page UI (the "+ Add Expense" button already links here via
  `url_for('add_expense')`)
- Step 5: Backend connection (`get_db()` and the existing query-helper
  conventions in `database/db.py`)

## Routes
- `GET /expenses/add` — renders the add-expense form, pre-filled with no
  values (date defaults to today in the template) — logged-in only
- `POST /expenses/add` — validates and inserts a new expense for the current
  user, then redirects to `/profile` — logged-in only

Both methods are handled by the existing `add_expense` view function (same
pattern as `register`/`login`: `methods=["GET", "POST"]` on one route).

## Database changes
No schema changes. The `expenses` table (`id`, `user_id`, `amount`, `category`,
`date`, `description`, `created_at`) already supports everything this feature
needs. Add one new helper function in `database/db.py`:

- `create_expense(user_id, amount, category, date, description)` — inserts a
  row into `expenses` and returns `(expense_id, error)`, following the same
  `(value, error)` tuple convention as `create_user`.

## Templates
- **Create:** `templates/add_expense.html` — form with fields: `amount`
  (number input, step 0.01, min 0.01), `category` (select: Food, Transport,
  Bills, Health, Entertainment, Shopping, Other — matching the badges already
  styled in `profile.css`), `date` (date input, defaults to today via Jinja/
  Python), `description` (text input, optional). Renders an `error` variable
  the same way `register.html`/`login.html` do. Extends `base.html`.
- **Modify:** none. `templates/profile.html` already links to
  `url_for('add_expense')` — no change needed.

## Files to change
- `app.py`
  - Replace the `add_expense` placeholder with a real view:
    - `GET`: render `add_expense.html` with `today` (ISO date string) for the
      date field's default value
    - `POST`: read `amount`, `category`, `date`, `description` from
      `request.form`; validate (see Rules); call `create_expense`; on success
      `flash` a confirmation and redirect to `url_for('profile')`; on
      validation failure re-render `add_expense.html` with `error` and the
      submitted values preserved
    - Require `session.get("user_id")`, redirecting to `login` otherwise (same
      guard pattern as `profile()`)
  - Import `create_expense` from `database.db`
- `database/db.py` — add `create_expense(user_id, amount, category, date,
  description)`

## Files to create
- `templates/add_expense.html`
- `static/css/add_expense.css` — form layout/styling, reusing existing CSS
  variables (`--accent`, `--ink-soft`, `--border-soft`, etc.) and the
  `cat-badge--*` category color tokens already defined in `profile.css` where
  it makes sense for category selection

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Passwords hashed with werkzeug (no changes to auth in this step)
- No hardcoded usernames, passwords, API keys, tokens, or secrets anywhere in
  source — read any such values from environment variables (e.g.
  `os.environ.get(...)`), never commit a literal credential
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- `amount` must parse as a positive float (`> 0`); reject non-numeric or
  zero/negative values with a user-facing error, re-rendering the form
- `category` must be one of the fixed set of allowed categories (reject
  anything else)
- `date` must be a well-formed `YYYY-MM-DD` string (`datetime.strptime`);
  reject malformed dates
- `description` is optional; store `None`/empty string as-is (no validation
  beyond trimming whitespace)
- On any validation failure, the form must redisplay with the values the user
  already typed (no silent data loss) and a clear `error` message
- Successful submission must redirect (PRG pattern) to `/profile`, not
  re-render the form directly, so a page refresh doesn't resubmit the expense
- The route must scope the insert to `session["user_id"]` — never trust a
  `user_id` from the form

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in shows a form with Amount,
  Category, Date (defaulted to today), and Description fields
- [ ] Submitting valid data creates a new row in `expenses` scoped to the
  current user and redirects to `/profile`
- [ ] The new expense appears immediately in the profile page's recent
  transactions list and is reflected in the summary stats and category
  breakdown
- [ ] Submitting a non-numeric or zero/negative amount shows an error and
  does not insert a row
- [ ] Submitting an invalid category shows an error and does not insert a row
- [ ] Submitting a malformed date shows an error and does not insert a row
- [ ] Submitting with description left blank still succeeds
- [ ] Refreshing the profile page after a successful add does not create a
  duplicate expense (PRG pattern confirmed)
- [ ] All amounts continue to display the ₹ symbol with thousands separators
