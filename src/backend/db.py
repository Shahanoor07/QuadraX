"""Database connection and utility helpers for ShipTrack (PS-05).

All database operations enforce parameterized SQL queries to prevent SQL injection.
Foreign key constraints are strictly enabled on every connection.
"""

import os
import sqlite3
from flask import g, current_app

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "shiptrack.db")


def get_db():
    """Retrieve or create an SQLite database connection for the current request context."""
    db_path = current_app.config.get("DATABASE", DEFAULT_DB_PATH) if current_app else DEFAULT_DB_PATH

    if "db" not in g:
        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        # Enforce foreign key constraints
        g.db.execute("PRAGMA foreign_keys = ON;")

    return g.db


def close_db(e=None):
    """Close the database connection if open at end of request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app=None):
    """Initialize database tables and indexes from schema.sql."""
    db_path = app.config.get("DATABASE", DEFAULT_DB_PATH) if app else DEFAULT_DB_PATH
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def query_db(query: str, args: tuple = (), one: bool = False):
    """Execute a parameterized SELECT query.

    Args:
        query: SQL query with '?' placeholders.
        args: Tuple of parameters matching the placeholders.
        one: If True, return only the first row or None.
    """
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def execute_db(query: str, args: tuple = ()) -> int:
    """Execute a parameterized INSERT/UPDATE/DELETE query and commit.

    Args:
        query: SQL query with '?' placeholders.
        args: Tuple of parameters matching the placeholders.

    Returns:
        The last inserted row id.
    """
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id
