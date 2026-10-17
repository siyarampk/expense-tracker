"""
Tests for Spec 10 — Mobile Responsive UI.

This spec is presentation-layer only (CSS/JS breakpoints, hamburger nav
markup in base.html). Per the spec's own Definition of Done, most checks
(no horizontal scrollbar at 360/480/768px, hamburger open/close animation,
~40px tap targets) are inherently visual/manual and cannot be meaningfully
asserted through pytest + Flask's test client, which has no layout engine.

What IS testable without reading template/CSS/JS source:
- No new routes/DB changes were introduced by this step (regression smoke
  test of every page named in the spec still renders/redirects correctly).
- Auth guards on protected pages are unchanged, since this step touches the
  shared base.html used by every page.
- The spec explicitly requires the hamburger toggle button to be
  keyboard-accessible with `aria-expanded` — we can assert that marker
  string appears in rendered HTML (string-level check only, not a judgment
  on CSS/JS correctness).

NOT tested here (manual/visual verification required per spec DoD):
- No horizontal scrollbar at 360px / 480px / 768px viewport widths.
- Hamburger menu visually opens/closes and animates on tap.
- Tap targets measuring ~40px on mobile.
- Keyboard operability (Tab + Enter/Space) of the hamburger button —
  this requires a real browser/DOM, not just HTML string inspection.
"""
import os

import pytest

from app import app as flask_app
from database import db as db_module


@pytest.fixture
def app(tmp_path, monkeypatch):
    # Point the DB helpers at an isolated, per-test SQLite file so test
    # data (registered users) never collides across tests or with the
    # real dev expense_tracker.db. DB_PATH has no app.config hook, so we
    # monkeypatch the module-level constant directly.
    test_db_path = str(tmp_path / "test_expense_tracker.db")
    monkeypatch.setattr(db_module, "DB_PATH", test_db_path)

    flask_app.config.update({"TESTING": True, "SECRET_KEY": "test-secret"})

    with flask_app.app_context():
        db_module.init_db()
        db_module.seed_db()
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """A test client logged in as a freshly registered user."""
    client.post(
        "/register",
        data={
            "name": "Test User",
            "email": "mobiletest@example.com",
            "password": "testpass123",
            "confirm_password": "testpass123",
        },
    )
    return client


class TestPublicPagesRenderAfterResponsivePass:
    """Spec: 'No new routes, data, or behavior — this is a presentation-layer
    pass.' These pages must still render exactly as before (200 OK)."""

    @pytest.mark.parametrize("path", ["/", "/register", "/login", "/terms", "/privacy"])
    def test_public_page_returns_200(self, client, path):
        response = client.get(path)
        assert response.status_code == 200, f"Expected {path} to render at 200 after responsive CSS/JS changes"


class TestProtectedPagesAuthGuardUnchanged:
    """Spec touches templates/base.html, used by every page. This step
    must not alter the existing auth-guard behavior on protected routes."""

    @pytest.mark.parametrize(
        "path", ["/profile", "/analytics", "/expenses/add", "/expenses/1/edit"]
    )
    def test_protected_page_redirects_to_login_when_logged_out(self, client, path):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 302, f"Expected {path} to redirect when logged out"
        assert "/login" in response.headers.get("Location", ""), (
            f"Expected {path} to redirect to /login when unauthenticated"
        )

    def test_delete_expense_redirects_to_login_when_logged_out(self, client):
        response = client.post("/expenses/1/delete", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers.get("Location", "")


class TestProtectedPagesRenderWhenAuthenticated:
    """Smoke test that logged-in access to profile/dashboard, add expense,
    and analytics (all named in the spec's Templates section) still
    succeeds after the responsive markup/CSS changes."""

    def test_profile_renders_for_logged_in_user(self, auth_client):
        response = auth_client.get("/profile")
        assert response.status_code == 200, "Expected profile/dashboard to render for a logged-in user"

    def test_analytics_renders_for_logged_in_user(self, auth_client):
        response = auth_client.get("/analytics")
        assert response.status_code == 200, "Expected analytics page to render for a logged-in user"

    def test_add_expense_get_renders_for_logged_in_user(self, auth_client):
        response = auth_client.get("/expenses/add")
        assert response.status_code == 200, "Expected add-expense form to render for a logged-in user"

    def test_edit_expense_get_renders_for_logged_in_user(self, auth_client):
        add_response = auth_client.post(
            "/expenses/add",
            data={
                "amount": "250.00",
                "category": "Food",
                "date": "2026-01-15",
                "description": "Groceries",
            },
            follow_redirects=False,
        )
        assert add_response.status_code == 302, "Setup: expected add_expense to redirect on success"

        profile_response = auth_client.get("/profile")
        assert b"Groceries" in profile_response.data, "Setup: expected newly added expense to appear on profile"

        edit_response = auth_client.get("/expenses/1/edit")
        assert edit_response.status_code == 200, "Expected edit-expense form to render for a logged-in user"


class TestHamburgerNavAccessibilityMarker:
    """Spec: base.html must add a mobile nav toggle (hamburger button)
    that is 'keyboard-accessible (button element, aria-expanded)'.

    This only checks for the presence of the aria-expanded attribute
    string in rendered HTML served from base.html (every page extends
    it) — it does not verify CSS/JS toggle behavior, which requires a
    real browser.
    """

    def test_landing_page_contains_aria_expanded_marker(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"aria-expanded" in response.data, (
            "Expected base.html's hamburger nav toggle to expose an aria-expanded "
            "attribute per the spec's accessibility requirement"
        )

    def test_profile_page_contains_aria_expanded_marker(self, auth_client):
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"aria-expanded" in response.data, (
            "Expected the shared base.html hamburger toggle to be present on the "
            "profile/dashboard page as well, since it extends base.html"
        )

    def test_hamburger_toggle_is_a_real_button_element(self, client):
        """Spec explicitly calls for a 'button element' (not e.g. a div/span
        with a click handler) for keyboard operability."""
        response = client.get("/")
        html = response.data.decode("utf-8", errors="ignore")
        assert "<button" in html, (
            "Expected at least one <button> element in the rendered page, "
            "consistent with the spec's hamburger nav toggle requirement"
        )


class TestNoNewRoutesOrDbChanges:
    """Spec explicitly states 'No new routes. No database changes.' This is
    a regression guard: existing CRUD behavior for expenses (the feature
    most likely to be accidentally broken by template/CSS edits around
    forms and tables) must still work end-to-end."""

    def test_add_expense_happy_path_creates_db_row_still_works(self, auth_client):
        response = auth_client.post(
            "/expenses/add",
            data={
                "amount": "99.50",
                "category": "Transport",
                "date": "2026-02-01",
                "description": "Bus pass",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Bus pass" in response.data, "Expected newly added expense to appear after responsive template changes"

    def test_add_expense_validation_error_still_returns_200_with_error(self, auth_client):
        response = auth_client.post(
            "/expenses/add",
            data={
                "amount": "not-a-number",
                "category": "Food",
                "date": "2026-02-01",
                "description": "Bad amount",
            },
        )
        assert response.status_code == 200
        assert b"valid amount" in response.data.lower() or b"error" in response.data.lower()

    def test_edit_expense_unknown_id_still_404s(self, auth_client):
        response = auth_client.get("/expenses/9999/edit")
        assert response.status_code == 404, "Expected unchanged 404 behavior for a non-existent/other-user expense id"
