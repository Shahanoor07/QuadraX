"""Database Seeding Script for ShipTrack (PS-05).

Creates one Admin account and one Delivery Person account for testing.
All passwords must be supplied via environment variables to prevent hardcoded credentials.

Usage:
    export ADMIN_PASSWORD="YourAdminSecurePassword123!"
    export DELIVERY_PASSWORD="YourDeliverySecurePassword123!"
    python -m src.backend.seed
"""

import os
import sys
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

try:
    from .db import init_db, query_db, execute_db
except (ImportError, ValueError):
    from db import init_db, query_db, execute_db

# Load .env if available
load_dotenv()


def seed():
    """Seed test accounts from environment variables."""
    # Ensure database tables exist
    init_db()

    admin_username = os.environ.get("ADMIN_USERNAME", "admin").strip()
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@shiptrack.local").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD")
    admin_name = os.environ.get("ADMIN_NAME", "System Administrator").strip()

    delivery_username = os.environ.get("DELIVERY_USERNAME", "courier_agent1").strip()
    delivery_email = os.environ.get("DELIVERY_EMAIL", "courier1@shiptrack.local").strip().lower()
    delivery_password = os.environ.get("DELIVERY_PASSWORD")
    delivery_name = os.environ.get("DELIVERY_NAME", "Express Courier One").strip()
    delivery_phone = os.environ.get("DELIVERY_PHONE", "+91 9876543210").strip()

    # Enforce passwords read from environment variables
    missing_vars = []
    if not admin_password:
        missing_vars.append("ADMIN_PASSWORD")
    if not delivery_password:
        missing_vars.append("DELIVERY_PASSWORD")

    if missing_vars:
        print(f"ERROR: Missing required environment variable(s): {', '.join(missing_vars)}", file=sys.stderr)
        print("Please set them in your environment or .env file before running seed.", file=sys.stderr)
        print("Example:", file=sys.stderr)
        print("  ADMIN_PASSWORD=AdminSecurePassword123!", file=sys.stderr)
        print("  DELIVERY_PASSWORD=CourierSecurePassword123!", file=sys.stderr)
        sys.exit(1)

    # 1. Seed or Update Admin Account
    admin_hash = generate_password_hash(admin_password)
    existing_admin = query_db(
        "SELECT id FROM users WHERE username = ? OR email = ?",
        (admin_username, admin_email),
        one=True
    )
    if existing_admin:
        execute_db(
            "UPDATE users SET password_hash = ?, role = 'admin', full_name = ? WHERE id = ?",
            (admin_hash, admin_name, existing_admin["id"])
        )
        print(f"[OK] Admin user '{admin_username}' updated (ID: {existing_admin['id']}).")
    else:
        admin_id = execute_db(
            """INSERT INTO users (username, email, password_hash, role, full_name, phone)
               VALUES (?, ?, ?, 'admin', ?, ?)""",
            (admin_username, admin_email, admin_hash, admin_name, None)
        )
        print(f"[OK] Admin user '{admin_username}' created (ID: {admin_id}).")

    # 2. Seed or Update Delivery Person Account
    delivery_hash = generate_password_hash(delivery_password)
    existing_delivery = query_db(
        "SELECT id FROM users WHERE username = ? OR email = ?",
        (delivery_username, delivery_email),
        one=True
    )
    if existing_delivery:
        execute_db(
            "UPDATE users SET password_hash = ?, role = 'delivery_person', full_name = ?, phone = ? WHERE id = ?",
            (delivery_hash, delivery_name, delivery_phone, existing_delivery["id"])
        )
        print(f"[OK] Delivery user '{delivery_username}' updated (ID: {existing_delivery['id']}).")
    else:
        delivery_id = execute_db(
            """INSERT INTO users (username, email, password_hash, role, full_name, phone)
               VALUES (?, ?, ?, 'delivery_person', ?, ?)""",
            (delivery_username, delivery_email, delivery_hash, delivery_name, delivery_phone)
        )
        print(f"[OK] Delivery user '{delivery_username}' created (ID: {delivery_id}).")

    print("\n[SUCCESS] Seeding completed successfully.")


if __name__ == "__main__":
    seed()
