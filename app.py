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
    date_from = request.args.get("date_from") or None
    date_to = request.args.get("date_to") or None

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
    )


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
