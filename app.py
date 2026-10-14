from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
from database.db import (
    init_db,
    seed_db,
    create_user,
    get_user_by_email,
    verify_user,
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)

def _build_date_presets(today=None):
    """Returns a dict mapping preset key -> (start_date, end_date) tuples.

    - "this_month": first of current month -> today
    - "last_3_months": first of the month 3 months ago -> today
    - "last_6_months": first of the month 6 months ago -> today
    """
    today = today or date.today()
    this_month_start = today.replace(day=1)

    def months_ago_start(n):
        year = this_month_start.year
        month = this_month_start.month - n
        while month <= 0:
            month += 12
            year -= 1
        return this_month_start.replace(year=year, month=month)

    return {
        "this_month": (this_month_start, today),
        "last_3_months": (months_ago_start(2), today),
        "last_6_months": (months_ago_start(5), today),
    }


def _parse_date_filter(date_from, date_to):
    """Validates date_from/date_to, applying spec fallback rules.

    Returns (date_from, date_to, error) where date_from/date_to are either
    well-formed 'YYYY-MM-DD' strings or None (absent/invalid), and error is
    a user-facing message if the range was rejected, else None.
    """
    for value in (date_from, date_to):
        if value is not None:
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                return None, None, None

    if date_from is not None and date_to is not None and date_from > date_to:
        return None, None, "Start date must be before end date."

    return date_from, date_to, None


app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

# Initialize database on startup
with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            return render_template("register.html", error="All fields are required")

        if len(password) < 8:
            return render_template("register.html", error="Password must be at least 8 characters")

        user_id, error = create_user(name, email, password)
        if error:
            return render_template("register.html", error=error)

        session["user_id"] = user_id
        session["user_name"] = name
        flash("Account created successfully!")
        return redirect(url_for("profile"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template("login.html", error="Email and password are required")

        user = verify_user(email, password)
        if not user:
            return render_template("login.html", error="Invalid email or password")

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        flash("Welcome back!")
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out")
    return redirect(url_for("landing"))




@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    raw_date_from = request.args.get("date_from") or None
    raw_date_to = request.args.get("date_to") or None
    date_from, date_to, error = _parse_date_filter(raw_date_from, raw_date_to)
    if error:
        flash(error)

    presets = _build_date_presets()
    preset_bounds = {
        key: (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        for key, (start, end) in presets.items()
    }

    if date_from is None and date_to is None:
        active_preset = "all_time"
    else:
        active_preset = next(
            (key for key, bounds in preset_bounds.items() if (date_from, date_to) == bounds),
            None,
        )

    user = get_user_by_id(user_id)
    if user is None:
        # Account was deleted out from under an active session.
        session.clear()
        return redirect(url_for("login"))

    summary = get_summary_stats(user_id, date_from=date_from, date_to=date_to)
    stats = {
        "total": f"{summary['total_spent']:,.2f}",
        "count": summary["transaction_count"],
        "top_category": summary["top_category"],
    }

    expenses = [
        {
            "id": tx["id"],
            "date": tx["date"],
            "description": tx["description"],
            "category": tx["category"],
            "amount": f"{tx['amount']:,.2f}",
        }
        for tx in get_recent_transactions(user_id, date_from=date_from, date_to=date_to)
    ]

    categories = [
        {
            "name": cat["name"],
            "amount": f"{cat['amount']:,.2f}",
            "percent": cat["pct"],
        }
        for cat in get_category_breakdown(user_id, date_from=date_from, date_to=date_to)
    ]

    return render_template(
        "profile.html",
        user=user,
        expenses=expenses,
        stats=stats,
        transactions=expenses,
        categories=categories,
        date_from=date_from,
        date_to=date_to,
        active_preset=active_preset,
        preset_bounds=preset_bounds,
    )


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
