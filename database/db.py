import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = "expense_tracker.db"


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
    """Inserts sample data for development. Safe to call multiple times."""
    conn = get_db()
    try:
        # Check if seed data already exists
        existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if existing > 0:
            return

        # Insert demo user
        password_hash = generate_password_hash("demo123")
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", password_hash)
        )
        user_id = cursor.lastrowid

        # Sample expenses for October 2026
        expenses = [
            (user_id, 150.00, "Food", "2026-10-01", "Lunch at restaurant"),
            (user_id, 45.00, "Transport", "2026-10-02", "Metro ride"),
            (user_id, 2500.00, "Bills", "2026-10-05", "Electricity bill"),
            (user_id, 800.00, "Health", "2026-10-06", "Medicines"),
            (user_id, 320.00, "Food", "2026-10-08", "Grocery shopping"),
            (user_id, 120.00, "Transport", "2026-10-10", "Taxi fare"),
            (user_id, 550.00, "Entertainment", "2026-10-11", "Movie tickets"),
            (user_id, 299.00, "Shopping", "2026-10-11", "Online purchase"),
        ]

        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            expenses
        )
        conn.commit()
    finally:
        conn.close()