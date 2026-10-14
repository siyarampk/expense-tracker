# Spec: Edit Expense

## Overview
Step 8 implements the `/expenses/<id>/edit` route, letting a logged-in user
correct a previously recorded expense (amount, category, date, description).
The profile page's transaction table already links each row's "Edit" button
to `url_for('edit_expense', id=tx.id)`. This step replaces that placeholder
with a real `GET` (pre-filled form) / `POST` (validate + update) flow, reusing
the validation rules and form layout established in Step 7 (Add Expense), and
adding an `update_expense` helper to `database/db.py`. Delete (Step 9) remains
a placeholder.

## Depends on
- Step 1: Database setup (`expenses` table must exist)
- Step 3: Login/logout (route must be behind an authenticated session)
- Step 4: Profile page UI (the "Edit" link already points at
  `url_for('edit_expense', id=tx.id)`)
- Step 5: Backend connection (`get_db()` and query-helper conventions)
- Step 7: Add Expense (validation rules, `ALLOWED_CATEGORIES`, and
  `add_expense.html` form pattern to reuse for the edit form)

## Routes
- `GET /expenses/<int:id>/edit` — renders the edit form pre-filled with the
  expense's current values — logged-in only; 404 if the expense doesn't exist
  or belongs to another user
- `POST /expenses/<int:id>/edit` — validates and updates the expense, then
  redirects to `/profile` — logged-in only; same ownership check as GET

Both methods are handled by the existing `edit_expense` view function (same
pattern as `add_expense`: `methods=["GET", "POST"]` on one route).

## Database changes
No schema changes. Add two new helper functions in `database/db.py`:

- `get_expense_by_id(expense_id, user_id)` — returns the expense row (`id`,
  `amount`, `category`, `date`, `description`) scoped to `user_id`, or `None`
  if it doesn't exist or belongs to another user.
- `update_expense(expense_id, user_id, amount, category, date, description)`
  — updates the row via `UPDATE expenses SET ... WHERE id = ? AND user_id = ?`
  and returns `(success: bool, error)`, following the same tuple convention as
  `create_expense`. `success` is `False` (with no DB error) when the
  `WHERE` clause matches zero rows (wrong id/owner).

## Templates
- **Create:** `templates/edit_expense.html` — same field set as
  `add_expense.html` (`amount`, `category`, `date`, `description`), pre-filled
  with the expense's current values; submits to
  `url_for('edit_expense', id=expense.id)`; renders an `error` variable the
  same way `add_expense.html` does. Extends `base.html`. Reuses
  `static/css/add_expense.css` (no new stylesheet needed since the form is
  structurally identical).
- **Modify:** none. `templates/profile.html` already links to
  `url_for('edit_expense', id=tx.id)` — no change needed.

## Files to change
- `app.py`
  - Replace the `edit_expense` placeholder with a real view:
    - Look up the expense via `get_expense_by_id(id, session["user_id"])`;
      if `None`, return a 404 (`abort(404)`)
    - `GET`: render `edit_expense.html` pre-filled with the expense's current
      `amount`, `category`, `date`, `description`
    - `POST`: read `amount`, `category`, `date`, `description` from
      `request.form`; apply the same validation as `add_expense` (positive
      float amount, allowed category, well-formed date); call
      `update_expense`; on success `flash` a confirmation and redirect to
      `url_for('profile')`; on validation failure re-render
      `edit_expense.html` with `error` and the submitted values preserved
    - Require `session.get("user_id")`, redirecting to `login` otherwise (same
      guard pattern as `profile()` / `add_expense()`)
  - Import `get_expense_by_id`, `update_expense` from `database.db`, and
    `abort` from `flask`
- `database/db.py` — add `get_expense_by_id(expense_id, user_id)` and
  `update_expense(expense_id, user_id, amount, category, date, description)`

## Files to create
- `templates/edit_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- No hardcoded usernames, passwords, API keys, tokens, or secrets anywhere in
  source — read any such values from environment variables, never commit a
  literal credential
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Reuse `ALLOWED_CATEGORIES` and the same validation logic (positive float
  amount, allowed category, `YYYY-MM-DD` date) already defined for
  `add_expense` in `app.py` — do not duplicate divergent rules
- The route must scope both the lookup and the update to
  `session["user_id"]` — never trust a `user_id` from the form, and never
  allow one user to view or edit another user's expense (404, not a generic
  error, if the id doesn't belong to them)
- On any validation failure, the form must redisplay with the values the user
  already typed (no silent data loss) and a clear `error` message
- Successful submission must redirect (PRG pattern) to `/profile`, not
  re-render the form directly, so a page refresh doesn't resubmit the update

## Definition of done
- [ ] Visiting `/expenses/<id>/edit` while logged out redirects to `/login`
- [ ] Visiting `/expenses/<id>/edit` for an expense that doesn't exist, or
  belongs to another user, returns a 404
- [ ] Visiting `/expenses/<id>/edit` for your own expense shows a form
  pre-filled with its current amount, category, date, and description
- [ ] Submitting valid changes updates the expense row and redirects to
  `/profile`
- [ ] The updated values appear immediately in the profile page's recent
  transactions list, summary stats, and category breakdown
- [ ] Submitting a non-numeric or zero/negative amount shows an error and
  does not change the row
- [ ] Submitting an invalid category shows an error and does not change the
  row
- [ ] Submitting a malformed date shows an error and does not change the row
- [ ] Refreshing the profile page after a successful edit does not resubmit
  or duplicate the update (PRG pattern confirmed)
- [ ] All amounts continue to display the ₹ symbol with thousands separators
</content>
</invoke>
