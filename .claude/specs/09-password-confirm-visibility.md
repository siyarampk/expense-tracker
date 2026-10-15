# Spec: Password Confirmation and Visibility Toggle

## Overview
The register page currently collects a single password field with no way for the user to verify they typed it correctly, and no way to review what they typed before submitting. This feature adds a "Confirm password" field to the registration form (validated server-side to match the original password) and a show/hide visibility toggle icon on both the registration and login password fields, improving usability without changing the underlying auth logic.

## Depends on
- 02-registration.md (registration route and `create_user`)
- 03-login-logout.md (login route)

## Routes
No new routes.

- `POST /register` (existing) — modified to additionally require and validate a `confirm_password` form field before calling `create_user`.

## Database changes
No database changes.

## Templates
- **Modify:** `templates/register.html` — add a "Confirm password" field (`name="confirm_password"`) and wrap both password inputs with a toggle-visibility icon/button.
- **Modify:** `templates/login.html` — wrap the existing password input with the same toggle-visibility icon/button for consistency.

## Files to change
- `app.py` — in `register()`, read `confirm_password` from the form; if it doesn't match `password`, re-render `register.html` with an error (before calling `create_user`), preserving entered `name`/`email` as with existing error paths.
- `templates/register.html` — add confirm password field; add visibility-toggle markup around both password fields.
- `templates/login.html` — add visibility-toggle markup around the password field.
- `static/js/main.js` — add the toggle behavior: clicking the icon switches the associated input's `type` between `password` and `text` and swaps the icon state; must work independently per-field when both fields are present.
- `static/css/style.css` — add styling for the password-field wrapper and the toggle icon button, using existing CSS variables only.

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- No hardcoded usernames, passwords, API keys, tokens, or secrets anywhere in source — read any such values from environment variables, never commit a literal credential
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- The confirm-password check happens server-side in `app.py`, independent of any client-side JS (JS is for visibility toggling only, not validation)
- The visibility toggle must be a plain button (`type="button"`) so it never submits the form
- Toggle icon must use an accessible label (e.g. `aria-label` that updates between "Show password" / "Hide password")

## Definition of done
- [ ] Visiting `/register`, submitting mismatched `password` and `confirm_password` re-renders the form with an error and does not create a user
- [ ] Visiting `/register` with matching passwords (both ≥ 8 chars) creates the account and logs the user in, same as before
- [ ] On `/register`, clicking the toggle icon on the password field reveals the plaintext password and changes the icon/label; clicking again hides it
- [ ] On `/register`, the confirm-password field has its own independent toggle icon
- [ ] On `/login`, clicking the toggle icon on the password field reveals/hides the plaintext password
- [ ] No existing registration or login test behavior breaks (name/email required, password length ≥ 8, duplicate email error) when run via `pytest`
