"""
Tests for Step 7: Add Expense.

Spec: .claude/specs/07-add-expense.md

Scope: auth guard on GET/POST /expenses/add, happy-path form rendering
(today's date default), happy-path submission (DB insert scoped to the
current user, redirect to /profile, visibility in profile summary/
transactions/category breakdown), each validation rule (amount, category,
date) rejecting without inserting a row and preserving submitted values,
blank description succeeding, and the PRG pattern preventing duplicate
inserts on refresh.

These tests exercise the *behavior* described in the spec, not
implementation internals of app.py/database/db.py.
"""
from datetime import date

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


def register_and_login(client, email="tester@example.com", password="password123", name="Tester"):
    client.post("/register", data={"name": name, "email": email, "password": password})
    client.post("/login", data={"email": email, "password": password})
    return email


def get_user_id(email):
    conn = db_module.get_db()
    try:
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        return row["id"]
    finally:
        conn.close()


def get_all_expenses(user_id):
    conn = db_module.get_db()
    try:
        return conn.execute(
            "SELECT * FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchall()
    finally:
        conn.close()


def count_all_expenses():
    conn = db_module.get_db()
    try:
        return conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    finally:
        conn.close()


VALID_PAYLOAD = {
    "amount": "250.50",
    "category": "Food",
    "date": "2026-10-05",
    "description": "Lunch with friends",
}


# --------------------------------------------------------------------- #
# Auth guard                                                             #
# --------------------------------------------------------------------- #

def test_get_add_expense_logged_out_redirects_to_login(client):
    """Spec: Visiting /expenses/add while logged out redirects to /login (GET)."""
    resp = client.get("/expenses/add")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_post_add_expense_logged_out_redirects_to_login(client):
    """Spec: logged-in only guard applies to POST as well as GET."""
    resp = client.post("/expenses/add", data=VALID_PAYLOAD)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
    assert count_all_expenses() == 0, "No row should be inserted for an unauthenticated POST"


# --------------------------------------------------------------------- #
# Happy path GET                                                         #
# --------------------------------------------------------------------- #

def test_get_add_expense_logged_in_renders_form(client):
    """Spec: logged in, GET shows a form with Amount, Category, Date, Description fields."""
    register_and_login(client)
    resp = client.get("/expenses/add")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "amount" in body.lower()
    assert "category" in body.lower()
    assert "date" in body.lower()
    assert "description" in body.lower()


def test_get_add_expense_defaults_date_to_today(client):
    """Spec: Date field defaults to today."""
    register_and_login(client)
    resp = client.get("/expenses/add")
    today = date.today().strftime("%Y-%m-%d")
    assert today in resp.data.decode(), "Expected today's date to prefill the date field"


# --------------------------------------------------------------------- #
# Happy path POST                                                        #
# --------------------------------------------------------------------- #

def test_post_valid_expense_redirects_to_profile(client):
    """Spec: Successful submission redirects (PRG), not re-renders the form."""
    email = register_and_login(client)
    resp = client.post("/expenses/add", data=VALID_PAYLOAD)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")


def test_post_valid_expense_inserts_row_scoped_to_user(client):
    """Spec: Valid submission creates a new row in expenses scoped to the current user."""
    email = register_and_login(client)
    user_id = get_user_id(email)

    client.post("/expenses/add", data=VALID_PAYLOAD)

    rows = get_all_expenses(user_id)
    assert len(rows) == 1
    row = rows[0]
    assert row["user_id"] == user_id
    assert row["amount"] == pytest.approx(250.50)
    assert row["category"] == "Food"
    assert row["date"] == "2026-10-05"
    assert row["description"] == "Lunch with friends"


def test_post_valid_expense_never_trusts_user_id_from_form(client):
    """Spec: insert must be scoped to session user_id, never a form-supplied user_id."""
    email = register_and_login(client)
    user_id = get_user_id(email)

    payload = dict(VALID_PAYLOAD)
    payload["user_id"] = str(user_id + 999)  # attempt to spoof a different owner

    client.post("/expenses/add", data=payload)

    rows = get_all_expenses(user_id)
    assert len(rows) == 1, "Expense should still be scoped to the logged-in session user"
    assert rows[0]["user_id"] == user_id


def test_post_valid_expense_appears_in_profile_summary(client):
    """Spec: new expense is reflected in profile's summary stats."""
    register_and_login(client)
    client.post("/expenses/add", data=VALID_PAYLOAD)

    resp = client.get("/profile")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "250.50" in body or "250.5" in body or "250" in body


def test_post_valid_expense_appears_in_profile_transactions(client):
    """Spec: new expense appears immediately in profile's recent transactions list."""
    register_and_login(client)
    client.post("/expenses/add", data=VALID_PAYLOAD)

    resp = client.get("/profile")
    body = resp.data.decode()
    assert "Lunch with friends" in body


def test_post_valid_expense_appears_in_category_breakdown(client):
    """Spec: new expense is reflected in the category breakdown."""
    register_and_login(client)
    client.post("/expenses/add", data=VALID_PAYLOAD)

    resp = client.get("/profile")
    body = resp.data.decode()
    assert "Food" in body


def test_profile_amounts_formatted_with_thousands_separator(client):
    """Spec: amounts continue to display with thousands separators after adding."""
    register_and_login(client)
    payload = dict(VALID_PAYLOAD)
    payload["amount"] = "12450"
    client.post("/expenses/add", data=payload)

    resp = client.get("/profile")
    body = resp.data.decode()
    assert "12,450" in body, "Expected thousands-separator formatting for large amounts"


# --------------------------------------------------------------------- #
# Validation: amount                                                     #
# --------------------------------------------------------------------- #

@pytest.mark.parametrize("bad_amount", ["not-a-number", "0", "-10", "", "abc123"])
def test_post_invalid_amount_rejected_no_insert(client, bad_amount):
    """Spec: non-numeric or zero/negative amounts are rejected with an error, no insert."""
    email = register_and_login(client)
    user_id = get_user_id(email)

    payload = dict(VALID_PAYLOAD)
    payload["amount"] = bad_amount

    resp = client.post("/expenses/add", data=payload)

    assert resp.status_code == 200, "Form should re-render (not redirect) on validation failure"
    assert len(get_all_expenses(user_id)) == 0


def test_post_invalid_amount_preserves_submitted_values(client):
    """Spec: on validation failure, the form redisplays the values the user already typed."""
    register_and_login(client)
    payload = dict(VALID_PAYLOAD)
    payload["amount"] = "not-a-number"
    payload["description"] = "My groceries run"

    resp = client.post("/expenses/add", data=payload)
    body = resp.data.decode()

    assert "not-a-number" in body
    assert "My groceries run" in body
    assert "2026-10-05" in body


# --------------------------------------------------------------------- #
# Validation: category                                                   #
# --------------------------------------------------------------------- #

def test_post_invalid_category_rejected_no_insert(client):
    """Spec: category must be one of the fixed allowed set; anything else is rejected."""
    email = register_and_login(client)
    user_id = get_user_id(email)

    payload = dict(VALID_PAYLOAD)
    payload["category"] = "NotARealCategory"

    resp = client.post("/expenses/add", data=payload)

    assert resp.status_code == 200
    assert len(get_all_expenses(user_id)) == 0


def test_post_invalid_category_preserves_submitted_values(client):
    """Spec: invalid category re-renders form with the user's submitted values."""
    register_and_login(client)
    payload = dict(VALID_PAYLOAD)
    payload["category"] = "NotARealCategory"

    resp = client.post("/expenses/add", data=payload)
    body = resp.data.decode()

    assert VALID_PAYLOAD["amount"] in body


# --------------------------------------------------------------------- #
# Validation: date                                                       #
# --------------------------------------------------------------------- #

@pytest.mark.parametrize("bad_date", ["2026-13-40", "not-a-date", "10/05/2026", ""])
def test_post_malformed_date_rejected_no_insert(client, bad_date):
    """Spec: date must be well-formed YYYY-MM-DD; malformed dates are rejected."""
    email = register_and_login(client)
    user_id = get_user_id(email)

    payload = dict(VALID_PAYLOAD)
    payload["date"] = bad_date

    resp = client.post("/expenses/add", data=payload)

    assert resp.status_code == 200
    assert len(get_all_expenses(user_id)) == 0


def test_post_malformed_date_preserves_submitted_values(client):
    """Spec: malformed date re-renders form with submitted values preserved."""
    register_and_login(client)
    payload = dict(VALID_PAYLOAD)
    payload["date"] = "not-a-date"

    resp = client.post("/expenses/add", data=payload)
    body = resp.data.decode()

    assert "not-a-date" in body
    assert VALID_PAYLOAD["amount"] in body


# --------------------------------------------------------------------- #
# Description optional                                                   #
# --------------------------------------------------------------------- #

def test_post_blank_description_succeeds(client):
    """Spec: description is optional; blank description still succeeds."""
    email = register_and_login(client)
    user_id = get_user_id(email)

    payload = dict(VALID_PAYLOAD)
    payload["description"] = ""

    resp = client.post("/expenses/add", data=payload)

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")
    rows = get_all_expenses(user_id)
    assert len(rows) == 1
    assert rows[0]["description"] in (None, "")


# --------------------------------------------------------------------- #
# PRG: no duplicate on refresh                                          #
# --------------------------------------------------------------------- #

def test_refresh_profile_after_successful_add_does_not_duplicate(client):
    """Spec: refreshing /profile after a successful add (PRG) doesn't duplicate the expense."""
    email = register_and_login(client)
    user_id = get_user_id(email)

    client.post("/expenses/add", data=VALID_PAYLOAD)
    assert len(get_all_expenses(user_id)) == 1

    # Simulate the browser following the redirect and then refreshing /profile.
    client.get("/profile")
    client.get("/profile")

    assert len(get_all_expenses(user_id)) == 1, "GET /profile must never re-insert the expense"
