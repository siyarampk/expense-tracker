# Spec: Login and Logout

## Overview
User authentication and session management for Spendly. Provides secure login with email/password, session-based authentication, and logout functionality. This feature was implemented as part of Step 02 (Registration) and is now documented for completeness.

## Depends on
- Step 01: Database Setup (users table with password_hash)
- Step 02: Registration (user authentication functions)

## Routes
- `GET /login` — Login form — public
- `POST /login` — Authenticate user — public
- `GET /logout` — End session and redirect — logged-in
- `GET /dashboard` — User dashboard with expenses — logged-in

## Database changes
No database changes. Uses existing:
- `users` table (email unique, password_hash)

## Templates
- **Create:** none (already exist)
- **Modify:** none

Existing templates used:
- `templates/login.html` — Login form
- `templates/dashboard.html` — User dashboard with expense list and category totals
- `templates/base.html` — Navbar with conditional login/logout links

## Files to change
None — feature already implemented.

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug.security
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`

## Implementation details (already complete)
The following are implemented in `app.py`:

1. **Login route** (lines 49-67):
   - GET displays login form
   - POST validates email/password, creates session with user_id and user_name
   - Invalid credentials show error message

2. **Logout route** (lines 84-88):
   - Clears session
   - Flashes "You have been logged out"
   - Redirects to landing

3. **Dashboard route** (lines 91-128):
   - Requires login (redirects to /login if not authenticated)
   - Shows logged-in user's name
   - Displays user's expenses ordered by date
   - Shows category totals for current month

4. **Database functions** in `database/db.py`:
   - `verify_user(email, password)` — validates credentials, returns user dict
   - `get_user_by_email(email)` — fetches user by email

5. **Navbar** in `templates/base.html`:
   - Shows "Sign in" and "Get started" when logged out
   - Shows user greeting, "Dashboard", and "Logout" when logged in

## Definition of done
- [x] User can log in with email and password
- [x] Invalid credentials show error message
- [x] Login creates session with user_id and user_name
- [x] Logout clears session and shows flash message
- [x] Dashboard only shows logged-in user's expenses
- [x] Dashboard shows category totals for current month
- [x] Navbar changes based on authentication state
- [x] Unauthenticated access to dashboard redirects to login