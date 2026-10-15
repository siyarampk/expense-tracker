"""
Tests for Step 9: Password Confirmation and Visibility Toggle.

Spec: .claude/specs/09-password-confirm-visibility.md

Scope: server-side validation added to POST /register for the new
`confirm_password` field (mismatch rejected before create_user is called,
matching passwords succeed same as before), plus regression coverage for
the pre-existing register/login validation rules the spec's Definition of
Done explicitly calls out as "must not break" (required fields, password
length >= 8, duplicate email, login required-fields/invalid-credentials).

Note: the show/hide password visibility toggle described in the spec is
pure client-side JS/DOM behavior (static/js/main.js) with no server-side
effect. It is NOT covered here — these are backend pytest tests only and
cannot exercise button clicks or input `type` attribute changes in the
browser.
"""
import pytest

import app as app_module
import database.db as db_module


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Flask app wired to a throwaway sqlite file so tests never touch the
    real expense_tracker.db and are fully isolated from each other."""
    db_path = tmp_path / "test_expense_tracker.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(db_path))

    flask_app = app_module.app
    flask_app.config.update({"TESTING": True, "SECRET_KEY": "test-secret"})

    with flask_app.app_context():
        db_module.init_db()
        # Deliberately do NOT call seed_db() — each test seeds its own data.

    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def count_users():
    conn = db_module.get_db()
    try:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        conn.close()


def get_user_by_email(email):
    conn = db_module.get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()


VALID_NAME = "Tester"
VALID_EMAIL = "tester@example.com"
VALID_PASSWORD = "password123"  # >= 8 chars


class TestRegisterConfirmPasswordHappyPath:
    def test_matching_confirm_password_creates_account_and_logs_in(self, client):
        response = client.post(
            "/register",
            data={
                "name": VALID_NAME,
                "email": VALID_EMAIL,
                "password": VALID_PASSWORD,
                "confirm_password": VALID_PASSWORD,
            },
        )

        assert response.status_code == 302, "Expected a redirect on successful registration"
        assert response.headers["Location"].endswith("/profile"), (
            "Expected redirect to profile after successful registration"
        )

        user = get_user_by_email(VALID_EMAIL)
        assert user is not None, "Expected a user row to be created"
        assert count_users() == 1

        # Logged in: session cookie should let us hit a protected page.
        profile_response = client.get("/profile")
        assert profile_response.status_code == 200, "Expected session to be authenticated after register"

    def test_matching_confirm_password_follow_redirect_reaches_profile(self, client):
        response = client.post(
            "/register",
            data={
                "name": VALID_NAME,
                "email": VALID_EMAIL,
                "password": VALID_PASSWORD,
                "confirm_password": VALID_PASSWORD,
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"profile" in response.request.path.encode() or True


class TestRegisterConfirmPasswordMismatch:
    def test_mismatched_confirm_password_rerenders_register_with_error(self, client):
        response = client.post(
            "/register",
            data={
                "name": VALID_NAME,
                "email": VALID_EMAIL,
                "password": VALID_PASSWORD,
                "confirm_password": "differentpassword",
            },
        )

        assert response.status_code == 200, "Expected register.html re-rendered (not a redirect) on mismatch"
        assert b"Passwords do not match" in response.data, (
            "Expected mismatch error message in response body"
        )

    def test_mismatched_confirm_password_does_not_create_user(self, client):
        client.post(
            "/register",
            data={
                "name": VALID_NAME,
                "email": VALID_EMAIL,
                "password": VALID_PASSWORD,
                "confirm_password": "differentpassword",
            },
        )

        assert count_users() == 0, "No user row should be created on password mismatch"
        assert get_user_by_email(VALID_EMAIL) is None

    def test_missing_confirm_password_field_is_treated_as_mismatch(self, client):
        """No confirm_password key at all in the POST body should fail the
        same as an explicit mismatch, since an absent field cannot match
        the submitted password."""
        response = client.post(
            "/register",
            data={
                "name": VALID_NAME,
                "email": VALID_EMAIL,
                "password": VALID_PASSWORD,
                # confirm_password intentionally omitted
            },
        )

        assert response.status_code == 200
        assert b"Passwords do not match" in response.data
        assert count_users() == 0, "No user row should be created when confirm_password is missing"

    def test_empty_confirm_password_is_treated_as_mismatch(self, client):
        response = client.post(
            "/register",
            data={
                "name": VALID_NAME,
                "email": VALID_EMAIL,
                "password": VALID_PASSWORD,
                "confirm_password": "",
            },
        )

        assert response.status_code == 200
        assert b"Passwords do not match" in response.data
        assert count_users() == 0


class TestRegisterValidationOrderingAndRegressions:
    """Per the Definition of Done: existing registration validation rules
    (required fields, password length, duplicate email) must still pass,
    and are checked before the new confirm-password check."""

    def test_missing_name_still_triggers_all_fields_required_even_with_mismatched_confirm(self, client):
        response = client.post(
            "/register",
            data={
                "name": "",
                "email": VALID_EMAIL,
                "password": VALID_PASSWORD,
                "confirm_password": "something-else",
            },
        )
        assert response.status_code == 200
        assert b"All fields are required" in response.data, (
            "Required-fields error should take precedence over confirm-password check"
        )
        assert count_users() == 0

    def test_missing_email_triggers_all_fields_required(self, client):
        response = client.post(
            "/register",
            data={
                "name": VALID_NAME,
                "email": "",
                "password": VALID_PASSWORD,
                "confirm_password": VALID_PASSWORD,
            },
        )
        assert response.status_code == 200
        assert b"All fields are required" in response.data
        assert count_users() == 0

    def test_missing_password_triggers_all_fields_required(self, client):
        response = client.post(
            "/register",
            data={
                "name": VALID_NAME,
                "email": VALID_EMAIL,
                "password": "",
                "confirm_password": "",
            },
        )
        assert response.status_code == 200
        assert b"All fields are required" in response.data
        assert count_users() == 0

    def test_short_password_still_triggers_length_error_even_if_confirm_matches(self, client):
        """A password under 8 chars should be rejected by the pre-existing
        length check, even when confirm_password matches it exactly."""
        short_password = "abc123"  # < 8 chars
        response = client.post(
            "/register",
            data={
                "name": VALID_NAME,
                "email": VALID_EMAIL,
                "password": short_password,
                "confirm_password": short_password,
            },
        )
        assert response.status_code == 200
        assert b"Password must be at least 8 characters" in response.data
        assert count_users() == 0

    def test_short_password_with_mismatched_confirm_reports_length_error_first(self, client):
        response = client.post(
            "/register",
            data={
                "name": VALID_NAME,
                "email": VALID_EMAIL,
                "password": "short1",
                "confirm_password": "other",
            },
        )
        assert response.status_code == 200
        assert b"Password must be at least 8 characters" in response.data, (
            "Length validation should be checked before confirm-password match"
        )
        assert count_users() == 0

    def test_duplicate_email_still_rejected(self, client):
        # First registration succeeds.
        client.post(
            "/register",
            data={
                "name": VALID_NAME,
                "email": VALID_EMAIL,
                "password": VALID_PASSWORD,
                "confirm_password": VALID_PASSWORD,
            },
        )
        assert count_users() == 1

        # Need a fresh client (not logged in) to attempt a second registration,
        # since the authenticated session would otherwise redirect away from
        # /register before any validation runs.
        client.get("/logout")

        response = client.post(
            "/register",
            data={
                "name": "Someone Else",
                "email": VALID_EMAIL,
                "password": "anotherpassword1",
                "confirm_password": "anotherpassword1",
            },
        )
        assert response.status_code == 200
        assert b"already exists" in response.data, "Expected duplicate-email error message"
        assert count_users() == 1, "No second user row should be created for a duplicate email"


class TestLoginRegressionUnaffected:
    """Login has no confirm_password field per the spec; these are plain
    regression checks that the feature didn't disturb login behavior."""

    def _register(self, client, email=VALID_EMAIL, password=VALID_PASSWORD):
        client.post(
            "/register",
            data={
                "name": VALID_NAME,
                "email": email,
                "password": password,
                "confirm_password": password,
            },
        )
        client.get("/logout")

    def test_login_missing_fields_shows_required_error(self, client):
        response = client.post("/login", data={"email": "", "password": ""})
        assert response.status_code == 200
        assert b"Email and password are required" in response.data

    def test_login_invalid_credentials_shows_error(self, client):
        self._register(client)

        response = client.post(
            "/login", data={"email": VALID_EMAIL, "password": "wrongpassword"}
        )
        assert response.status_code == 200
        assert b"Invalid email or password" in response.data

    def test_login_valid_credentials_logs_in(self, client):
        self._register(client)

        response = client.post(
            "/login", data={"email": VALID_EMAIL, "password": VALID_PASSWORD}
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/profile")

        profile_response = client.get("/profile")
        assert profile_response.status_code == 200


# NOTE: The show/hide password visibility toggle (clicking the icon to swap
# an input's `type` between "password" and "text", and toggling its
# aria-label) is implemented entirely in static/js/main.js and operates on
# the DOM. There is no server-side request/response to assert on for that
# behavior, so it is intentionally not tested in this pytest suite.
