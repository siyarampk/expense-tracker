from flask import Flask, render_template, request, redirect, url_for, session, flash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email, verify_user

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
    if not session.get("user_id"): return redirect(url_for("login"))
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    expenses = db.execute("SELECT * FROM expenses WHERE user_id=? ORDER BY date DESC LIMIT 5", (session["user_id"],)).fetchall()
    stats={"total":"₹12,450.75","count":len(expenses),"top_category":"Food"}
    return render_template("profile.html", user=user, expenses=expenses, stats=stats, transactions=expenses, categories=[{"name":"Food","amount":"2240","percent":55},{"name":"Bills","amount":"2200","percent":45},{"name":"Transport","amount":"500","percent":15},{"name":"Health","amount":"800","percent":20}])


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
