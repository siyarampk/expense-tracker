# Spec: Registration

## Overview
User registration and authentication system for Spendly. Enables new users to create accounts, log in securely with session-based authentication, and access a personalized dashboard showing their expenses.

## Depends on
- Step 01: Database Setup (users and expenses tables must exist)

## Routes
- `GET /register` — Registration form — public
- `POST /register` — Create new user — public
- `GET /login` — Login form — public
- `POST /login` — Authenticate user — public
- `GET /logout` — End session — logged-in
- `GET /dashboard` — User dashboard — logged-in
- `GET /` — Redirect to dashboard if logged in, otherwise landing — public

## Database changes
No new tables or columns. Uses existing:
- `users` table (email unique constraint, password_hash)
- `expenses` table (user_id foreign key)

## Templates
- **Create:** `templates/dashboard.html`
- **Modify:** `templates/base.html` (navbar with conditional links, flash messages)

## Files to change
- `app.py` — Add POST handlers for register/login, dashboard route, logout, session
- `database/db.py` — Add `create_user()`, `get_user_by_email()`, `verify_user()` functions
- `templates/base.html` — Dynamic navbar based on session state
- `static/css/style.css` — Dashboard styles

## Files to create
- `templates/dashboard.html` — User dashboard with expenses list and category totals

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug.security
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Session stored in Flask session (server-side)
- Email stored lowercase for consistency

## Definition of done
- [ ] User can register with name, email, password (min 8 chars)
- [ ] Duplicate email shows error message
- [ ] User can log in with email and password
- [ ] Invalid credentials show error message
- [ ] Dashboard shows logged-in user's name
- [ ] Dashboard shows only that user's expenses
- [ ] Dashboard shows category totals for current month
- [ ] Logout clears session and redirects to landing
- [ ] Landing page redirects to dashboard if already logged in
- [ ] Flash messages appear for registration success, login, logout