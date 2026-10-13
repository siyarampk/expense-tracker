"""
Tests for Step 6: Date Filter for Profile page.

Spec: .claude/specs/06-date-filter-profile.md

Scope (per task): preset button rendering/active-state for "This Month" /
"Last 3 Months" / "Last 6 Months" / "All Time", correctness of the computed
date ranges for those presets, the "Clear" link's conditional visibility,
consistency between presets and equivalent manual date ranges, date
validation fallback (malformed/reversed ranges), and the auth guard on
/profile.

These tests exercise the *behavior* described in the spec (what the filtered
page should show), not implementation internals.
"""
import sqlite3
from datetime import date, timedelta

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
        # Deliberately do NOT call seed_db() — each test seeds its own data
        # so expectations stay self-contained and deterministic.

    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def register_and_login(client, email="tester@example.com", password="password123", name="Tester"):
    client.post("/register", data={"name": name, "email": email, "password": password})
    return email


def get_user_id(email):
    conn = db_module.get_db()
    try:
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        return row["id"]
    finally:
        conn.close()


def insert_expense(user_id, amount, category, expense_date, description="test expense"):
    conn = db_module.get_db()
    try:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, expense_date, description),
        )
        conn.commit()
    finally:
        conn.close()


def iso(d):
    return d.strftime("%Y-%m-%d")


def this_month_bounds(today=None):
    today = today or date.today()
    start = today.replace(day=1)
    return iso(start), iso(today)


def last_month_bounds(today=None):
    today = today or date.today()
    this_month_start = today.replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    return iso(last_month_start), iso(last_month_end)


def _months_ago_start(this_month_start, n):
    year = this_month_start.year
    month = this_month_start.month - n
    while month <= 0:
        month += 12
        year -= 1
    return this_month_start.replace(year=year, month=month)


def last_3_months_bounds(today=None):
    today = today or date.today()
    this_month_start = today.replace(day=1)
    return iso(_months_ago_start(this_month_start, 2)), iso(today)


def last_6_months_bounds(today=None):
    today = today or date.today()
    this_month_start = today.replace(day=1)
    return iso(_months_ago_start(this_month_start, 5)), iso(today)


# --------------------------------------------------------------------- #
# Auth guard                                                            #
# --------------------------------------------------------------------- #

class TestAuthGuard:
    def test_profile_without_login_redirects(self, client):
        """Unauthenticated GET /profile redirects, consistent with existing
        /profile behavior (not a 200 render of the filter bar)."""
        response = client.get("/profile")
        assert response.status_code == 302, "Expected redirect for unauthenticated /profile"
        assert "/login" in response.headers["Location"]

    def test_profile_with_filter_params_without_login_still_redirects(self, client):
        """Auth guard applies even when date filter query params are present."""
        response = client.get("/profile?date_from=2026-01-01&date_to=2026-01-31")
        assert response.status_code == 302, "Filter params must not bypass the auth guard"
        assert "/login" in response.headers["Location"]


# --------------------------------------------------------------------- #
# Preset rendering / active state                                      #
# --------------------------------------------------------------------- #

class TestPresetButtons:
    def test_all_time_is_active_preset_with_no_query_params(self, client):
        """Visiting /profile with no params should mark 'All Time' as active
        and render all four preset buttons."""
        email = register_and_login(client)
        response = client.get("/profile")
        assert response.status_code == 200
        html = response.data.decode()
        assert "This Month" in html
        assert "Last 3 Months" in html
        assert "Last 6 Months" in html
        assert "All Time" in html
        # The All Time button should carry the active class, the others should not.
        assert 'filter-preset-btn--active">All Time' in html or (
            'filter-preset-btn filter-preset-btn--active' in html and 'All Time' in html
        )

    def test_this_month_preset_link_marks_active_state(self, client):
        """Clicking the This Month preset link's resulting URL should
        highlight the This Month button as active."""
        register_and_login(client)
        date_from, date_to = this_month_bounds()
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        assert response.status_code == 200
        html = response.data.decode()
        # This Month link should be flagged active.
        assert "This Month" in html
        this_month_idx = html.index("This Month")
        preceding = html[max(0, this_month_idx - 200):this_month_idx]
        assert "filter-preset-btn--active" in preceding, "This Month button should be active"

    def test_last_3_months_preset_link_marks_active_state(self, client):
        register_and_login(client)
        date_from, date_to = last_3_months_bounds()
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        assert response.status_code == 200
        html = response.data.decode()
        idx = html.index("Last 3 Months")
        preceding = html[max(0, idx - 200):idx]
        assert "filter-preset-btn--active" in preceding, "Last 3 Months button should be active"

    def test_last_6_months_preset_link_marks_active_state(self, client):
        register_and_login(client)
        date_from, date_to = last_6_months_bounds()
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        assert response.status_code == 200
        html = response.data.decode()
        idx = html.index("Last 6 Months")
        preceding = html[max(0, idx - 200):idx]
        assert "filter-preset-btn--active" in preceding, "Last 6 Months button should be active"

    def test_custom_range_not_matching_any_preset_has_no_active_preset_button(self, client):
        """A manual range that doesn't align with any named preset should not
        highlight any of the four preset buttons."""
        register_and_login(client)
        # An arbitrary custom range far outside all presets.
        response = client.get("/profile?date_from=2020-01-01&date_to=2020-06-30")
        assert response.status_code == 200
        html = response.data.decode()
        for label in ("This Month", "Last 3 Months", "Last 6 Months", "All Time"):
            idx = html.index(label)
            preceding = html[max(0, idx - 200):idx]
            assert "filter-preset-btn--active" not in preceding, (
                f"{label} should not be active for a non-matching custom range"
            )


# --------------------------------------------------------------------- #
# This Month / Last Month date range correctness                       #
# --------------------------------------------------------------------- #

class TestPresetDateRangeCorrectness:
    def test_this_month_includes_only_current_month_expenses(self, client):
        email = register_and_login(client)
        user_id = get_user_id(email)

        today = date.today()
        in_range_date = iso(today.replace(day=1))
        out_of_range_date = iso(today.replace(day=1) - timedelta(days=1))  # last day of prior month

        insert_expense(user_id, 100.0, "Food", in_range_date, "in this month")
        insert_expense(user_id, 200.0, "Food", out_of_range_date, "before this month")

        date_from, date_to = this_month_bounds()
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        html = response.data.decode()

        assert "in this month" in html
        assert "before this month" not in html

    def test_last_3_months_includes_expenses_within_window(self, client):
        email = register_and_login(client)
        user_id = get_user_id(email)

        date_from, date_to = last_3_months_bounds()
        start = date.fromisoformat(date_from)

        insert_expense(user_id, 50.0, "Transport", iso(start), "start of window")
        insert_expense(user_id, 999.0, "Transport", iso(start - timedelta(days=1)), "before window")

        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        html = response.data.decode()

        assert "start of window" in html
        assert "before window" not in html

    def test_last_6_months_includes_expenses_within_window(self, client):
        email = register_and_login(client)
        user_id = get_user_id(email)

        date_from, date_to = last_6_months_bounds()
        start = date.fromisoformat(date_from)

        insert_expense(user_id, 50.0, "Transport", iso(start), "start of window")
        insert_expense(user_id, 999.0, "Transport", iso(start - timedelta(days=1)), "before window")

        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        html = response.data.decode()

        assert "start of window" in html
        assert "before window" not in html

    def test_this_month_and_last_3_months_ranges_share_end_date(self):
        """Pure date-math check: Last 3 Months and This Month share the same
        end date (today), and Last 3 Months starts on or before This Month."""
        this_start, this_end = this_month_bounds()
        last3_start, last3_end = last_3_months_bounds()

        assert last3_end == this_end
        assert date.fromisoformat(last3_start) <= date.fromisoformat(this_start)


# --------------------------------------------------------------------- #
# All Time clears filters                                               #
# --------------------------------------------------------------------- #

class TestAllTimePreset:
    def test_all_time_preset_link_has_no_query_params(self, client):
        """Spec: the All Time preset must pass no query params (clean
        /profile URL)."""
        register_and_login(client)
        response = client.get("/profile?date_from=2026-01-01&date_to=2026-01-31")
        html = response.data.decode()
        all_time_idx = html.index("All Time")
        tag_start = html.rfind("<a", 0, all_time_idx)
        tag = html[tag_start:all_time_idx]
        assert 'href="/profile"' in tag, "All Time link must point to a clean /profile URL with no query params"

    def test_all_time_shows_all_expenses_regardless_of_date(self, client):
        email = register_and_login(client)
        user_id = get_user_id(email)

        insert_expense(user_id, 10.0, "Food", "2000-01-01", "ancient expense")
        insert_expense(user_id, 20.0, "Food", iso(date.today()), "todays expense")

        response = client.get("/profile")
        html = response.data.decode()

        assert "ancient expense" in html
        assert "todays expense" in html


# --------------------------------------------------------------------- #
# Clear link visibility                                                 #
# --------------------------------------------------------------------- #

class TestClearLink:
    def test_clear_link_hidden_when_no_filter_active(self, client):
        register_and_login(client)
        response = client.get("/profile")
        html = response.data.decode()
        assert "Clear" not in html, "Clear link should not render when no filter is active"

    def test_clear_link_visible_when_preset_filter_active(self, client):
        register_and_login(client)
        date_from, date_to = this_month_bounds()
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        html = response.data.decode()
        assert "Clear" in html, "Clear link should render when a preset filter is active"

    def test_clear_link_visible_when_custom_range_active(self, client):
        register_and_login(client)
        response = client.get("/profile?date_from=2020-01-01&date_to=2020-06-30")
        html = response.data.decode()
        assert "Clear" in html, "Clear link should render for an active custom date range"

    def test_clear_link_points_to_clean_profile_url(self, client):
        register_and_login(client)
        date_from, date_to = this_month_bounds()
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        html = response.data.decode()
        clear_idx = html.index(">Clear<")
        tag_start = html.rfind("<a", 0, clear_idx)
        tag = html[tag_start:clear_idx]
        assert 'href="/profile"' in tag, "Clear link must navigate to an unfiltered /profile URL"

    def test_clear_link_visible_with_only_date_from_set(self, client):
        """Edge case: a single-sided range (only date_from) still counts as
        an active filter and should surface the Clear link."""
        register_and_login(client)
        response = client.get("/profile?date_from=2026-01-01")
        html = response.data.decode()
        assert "Clear" in html


# --------------------------------------------------------------------- #
# Consistency between presets and equivalent manual ranges              #
# --------------------------------------------------------------------- #

class TestPresetManualConsistency:
    def test_this_month_preset_matches_manual_range_with_same_bounds(self, client):
        """Hitting the This Month preset URL and manually typing the same
        date_from/date_to must produce identical filtered results and the
        same active-preset highlighting."""
        email = register_and_login(client)
        user_id = get_user_id(email)
        insert_expense(user_id, 42.0, "Food", iso(date.today()), "manual vs preset expense")
        # Drain the one-shot registration flash so it doesn't appear in only
        # the first of the two comparison responses below.
        client.get("/profile")

        date_from, date_to = this_month_bounds()
        preset_response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        manual_response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")

        assert preset_response.data == manual_response.data, (
            "Identical date_from/date_to params must render identical pages regardless of "
            "whether they came from a preset link or manual entry"
        )

    def test_manual_range_outside_presets_does_not_match_data_of_this_month(self, client):
        """A manual range that happens not to equal This Month's bounds must
        not be mislabeled as 'this_month' and must filter data independently."""
        email = register_and_login(client)
        user_id = get_user_id(email)

        today = date.today()
        insert_expense(user_id, 15.0, "Food", iso(today), "current expense")

        # A custom range covering only a single arbitrary day in the past,
        # guaranteed not to equal the This Month preset bounds.
        custom_day = iso(today - timedelta(days=200))
        response = client.get(f"/profile?date_from={custom_day}&date_to={custom_day}")
        html = response.data.decode()

        assert "current expense" not in html, "Manual range should filter independently of presets"


# --------------------------------------------------------------------- #
# Happy path / baseline (no filter == Step 5 behavior)                  #
# --------------------------------------------------------------------- #

class TestUnfilteredBaseline:
    def test_no_query_params_shows_currency_formatted_totals(self, client):
        email = register_and_login(client)
        user_id = get_user_id(email)
        insert_expense(user_id, 1234.5, "Bills", iso(date.today()), "rent")

        response = client.get("/profile")
        assert response.status_code == 200
        html = response.data.decode()
        assert "₹" in html, "Amounts must display with the ₹ symbol"

    def test_filtered_range_with_no_matching_expenses_shows_zero_state(self, client):
        """Spec DoD: a user with no expenses in the selected range sees
        ₹0.00 total, 0 transactions, empty category breakdown, no errors."""
        register_and_login(client)
        response = client.get("/profile?date_from=1999-01-01&date_to=1999-01-31")
        assert response.status_code == 200
        html = response.data.decode()
        assert "₹0.00" in html
        assert "No expenses found for this period." in html


# --------------------------------------------------------------------- #
# Date validation fallback (spec: malformed/reversed ranges)            #
# --------------------------------------------------------------------- #

class TestDateValidation:
    def test_malformed_date_from_falls_back_to_unfiltered(self, client):
        email = register_and_login(client)
        user_id = get_user_id(email)
        insert_expense(user_id, 10.0, "Food", "2000-01-01", "ancient expense")

        response = client.get("/profile?date_from=not-a-date&date_to=2026-01-31")
        assert response.status_code == 200
        html = response.data.decode()
        assert "ancient expense" in html, "Malformed date_from should fall back to unfiltered"

    def test_malformed_date_to_falls_back_to_unfiltered(self, client):
        email = register_and_login(client)
        user_id = get_user_id(email)
        insert_expense(user_id, 10.0, "Food", "2000-01-01", "ancient expense")

        response = client.get("/profile?date_from=2026-01-01&date_to=not-a-date")
        assert response.status_code == 200
        html = response.data.decode()
        assert "ancient expense" in html, "Malformed date_to should fall back to unfiltered"

    def test_date_from_after_date_to_falls_back_and_flashes_error(self, client):
        email = register_and_login(client)
        user_id = get_user_id(email)
        insert_expense(user_id, 10.0, "Food", "2000-01-01", "ancient expense")

        response = client.get("/profile?date_from=2026-06-01&date_to=2026-01-01")
        assert response.status_code == 200
        html = response.data.decode()
        assert "Start date must be before end date." in html
        assert "ancient expense" in html, "Reversed range should fall back to unfiltered"
