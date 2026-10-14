import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = "expense_tracker.db"


def create_user(name, email, password):
    """Create a new user. Returns (user_id, error) tuple."""
    conn = get_db()
    try:
        password_hash = generate_password_hash(password)
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash)
        )
        conn.commit()
        return (cursor.lastrowid, None)
    except sqlite3.IntegrityError:
        return (None, "An account with this email already exists")
    finally:
        conn.close()


def create_expense(user_id, amount, category, date, description):
    """Create a new expense. Returns (expense_id, error) tuple."""
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        conn.commit()
        return (cursor.lastrowid, None)
    except sqlite3.IntegrityError:
        return (None, "Could not save this expense")
    finally:
        conn.close()


def get_expense_by_id(expense_id, user_id):
    """Get a single expense scoped to user_id. Returns a Row or None."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT id, amount, category, date, description FROM expenses "
            "WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        ).fetchone()
    finally:
        conn.close()


def update_expense(expense_id, user_id, amount, category, date, description):
    """Update an expense scoped to user_id. Returns (success, error) tuple."""
    conn = get_db()
    try:
        cursor = conn.execute(
            "UPDATE expenses SET amount = ?, category = ?, date = ?, "
            "description = ? WHERE id = ? AND user_id = ?",
            (amount, category, date, description, expense_id, user_id),
        )
        conn.commit()
        return (cursor.rowcount > 0, None)
    except sqlite3.IntegrityError:
        return (False, "Could not update this expense")
    finally:
        conn.close()


def delete_expense_row(expense_id, user_id):
    """Delete an expense scoped to user_id. Returns True if a row was deleted."""
    conn = get_db()
    try:
        cursor = conn.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_user_by_email(email):
    """Get user by email. Returns a Row or None."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT id, name, email, password_hash, created_at FROM users WHERE email = ?",
            (email,)
        ).fetchone()
    finally:
        conn.close()


def verify_user(email, password):
    """Verify user credentials. Returns user dict if valid, None otherwise."""
    user = get_user_by_email(email)
    if user and check_password_hash(user["password_hash"], password):
        return {"id": user["id"], "name": user["name"], "email": user["email"]}
    return None


def get_db():
    """Returns a SQLite connection with row_factory and foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Creates all tables using CREATE TABLE IF NOT EXISTS."""
    conn = get_db()
    try:
        # Users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Expenses table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """No-op: Spendly has no demo/seed accounts. Users register for real
    accounts via the /register flow instead of relying on hardcoded
    credentials (a security risk in a public repository)."""
    return


# ------------------------------------------------------------------ #
# Pure query helpers — no Flask imports. Each function opens its own  #
# connection via get_db() and closes it before returning. All queries #
# are parameterised — never string-format values into SQL.            #
# ------------------------------------------------------------------ #

def get_user_by_id(user_id):
    """Returns a dict with: name, email, member_since, initials — or None if
    no user with that id exists.

    - member_since: derived from users.created_at ("YYYY-MM-DD HH:MM:SS"),
      formatted as "Month YYYY" (e.g. "January 2026").
    - initials: first letter of each of the first two whitespace-separated
      words in `name`, uppercased (e.g. "Demo User" -> "DU"; "Madonna" ->
      "M"; empty/blank name -> "").
    """
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    name = row["name"] or ""
    email = row["email"]
    created_at = row["created_at"]

    dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
    member_since = dt.strftime("%B %Y")

    words = name.split()
    initials = "".join(word[0].upper() for word in words[:2])

    return {
        "name": name,
        "email": email,
        "member_since": member_since,
        "initials": initials,
    }


def get_summary_stats(user_id, date_from=None, date_to=None):
    """Returns a dict with: total_spent (float), transaction_count (int),
    top_category (str).

    - Scoped to expenses.user_id = user_id, optionally filtered by
      date >= date_from and/or date <= date_to (lexicographic comparison on
      'YYYY-MM-DD' text works for this purpose).
    - top_category: category with the highest summed amount among matching
      rows. Ties are broken alphabetically (highest total first, then
      category name ascending), which is a deterministic, documented choice.
    - If there are no matching expenses, returns exactly
      {"total_spent": 0, "transaction_count": 0, "top_category": "\u2014"}.
    """
    conn = get_db()
    try:
        query = "SELECT amount, category FROM expenses WHERE user_id = ?"
        params = [user_id]
        if date_from is not None:
            query += " AND date >= ?"
            params.append(date_from)
        if date_to is not None:
            query += " AND date <= ?"
            params.append(date_to)

        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    if not rows:
        return {"total_spent": 0, "transaction_count": 0, "top_category": "\u2014"}

    total_spent = sum(r["amount"] for r in rows)
    transaction_count = len(rows)

    totals_by_category = {}
    for r in rows:
        totals_by_category[r["category"]] = totals_by_category.get(r["category"], 0) + r["amount"]

    # Highest total first; ties broken alphabetically by category name.
    top_category = sorted(
        totals_by_category.items(), key=lambda item: (-item[1], item[0])
    )[0][0]

    return {
        "total_spent": total_spent,
        "transaction_count": transaction_count,
        "top_category": top_category,
    }


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    """Returns a list of dicts for the given user's expenses, newest-first.

    Each dict has: id, date, description, category, amount
    (amount is a float, not pre-formatted with currency symbols).

    - Filters by expenses.user_id = user_id.
    - If date_from is given, only includes rows with date >= date_from.
    - If date_to is given, only includes rows with date <= date_to.
    - Orders by date DESC, then id DESC (stable ordering for same-day rows).
    - Limits to `limit` rows.
    - Uses parameterised queries only.
    - Returns an empty list if there are no matching expenses; never raises.
    """
    conn = get_db()
    try:
        query = (
            "SELECT id, date, description, category, amount "
            "FROM expenses WHERE user_id = ?"
        )
        params = [user_id]

        if date_from is not None:
            query += " AND date >= ?"
            params.append(date_from)

        if date_to is not None:
            query += " AND date <= ?"
            params.append(date_to)

        query += " ORDER BY date DESC, id DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()

        return [
            {
                "id": row["id"],
                "date": row["date"],
                "description": row["description"],
                "category": row["category"],
                "amount": float(row["amount"]),
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_category_breakdown(user_id, date_from=None, date_to=None):
    """Returns a list of dicts, one per distinct category the user has
    expenses in, each with: name (str), amount (float), pct (int).

    - Scoped to expenses.user_id = user_id.
    - If date_from given, only include date >= date_from; if date_to given,
      only include date <= date_to.
    - amount: sum of amount for that category among matching rows.
    - List ordered by amount DESC.
    - pct: integer percentage of total spend that category represents, with
      rounding remainder absorbed into the largest category so the pct
      values always sum to exactly 100.
    - Returns [] if the user has no matching expenses.
    """
    conn = get_db()
    try:
        query = (
            "SELECT category AS name, SUM(amount) AS amount "
            "FROM expenses WHERE user_id = ?"
        )
        params = [user_id]

        if date_from is not None:
            query += " AND date >= ?"
            params.append(date_from)
        if date_to is not None:
            query += " AND date <= ?"
            params.append(date_to)

        query += " GROUP BY category ORDER BY amount DESC"

        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    categories = [{"name": row["name"], "amount": float(row["amount"])} for row in rows]
    total = sum(c["amount"] for c in categories)

    if total == 0:
        for c in categories:
            c["pct"] = 0
        categories[0]["pct"] = 100
        return categories

    raw_pcts = [(c["amount"] / total) * 100 for c in categories]
    rounded_pcts = [round(p) for p in raw_pcts]
    remainder = 100 - sum(rounded_pcts)
    rounded_pcts[0] += remainder

    for c, pct in zip(categories, rounded_pcts):
        c["pct"] = pct

    return categories