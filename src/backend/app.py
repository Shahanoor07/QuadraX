"""ShipTrack Backend Application Entrypoint (PS-05).

Delivery & Shipment Management System.
Configured with SQLite, parameterized query helpers, and secure defaults.
"""

import os
from datetime import timedelta
from flask import Flask, jsonify
from dotenv import load_dotenv

from werkzeug.security import generate_password_hash

try:
    from .db import close_db, init_db, query_db, execute_db
    from .auth import auth_bp
    from .shipments import shipments_bp
    from .delivery import delivery_bp
    from .admin import admin_bp
    from .tracking import tracking_bp
except (ImportError, ValueError):
    from db import close_db, init_db, query_db, execute_db
    from auth import auth_bp
    from shipments import shipments_bp
    from delivery import delivery_bp
    from admin import admin_bp
    from tracking import tracking_bp

# Load environment variables if .env is present
load_dotenv()


def create_app(test_config=None):
    """Application factory for ShipTrack."""
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    app = Flask(__name__, instance_relative_config=True, static_folder=frontend_dir, static_url_path="")

    # Security configuration defaults
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secure-key-change-in-production"),
        DATABASE=os.path.join(os.path.dirname(__file__), "shiptrack.db"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
        PERMANENT_SESSION_LIFETIME=timedelta(days=1),
    )

    if test_config is not None:
        app.config.from_mapping(test_config)

    # Register database teardown
    app.teardown_appcontext(close_db)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(shipments_bp)
    app.register_blueprint(delivery_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(tracking_bp)

    # Auto-initialize database tables and seed default accounts on startup
    db_path = app.config.get("DATABASE")
    if db_path and db_path != ":memory:":
        with app.app_context():
            # 1. Guarantee schema tables and indexes exist
            db_dir = os.path.dirname(os.path.abspath(db_path))
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            init_db(app)

            # 2. Auto-seed Admin account if ADMIN_PASSWORD is set and account does not exist
            admin_pw = os.environ.get("ADMIN_PASSWORD")
            if admin_pw:
                admin_user = os.environ.get("ADMIN_USERNAME", "admin").strip()
                admin_mail = os.environ.get("ADMIN_EMAIL", "admin@shiptrack.local").strip().lower()
                admin_name = os.environ.get("ADMIN_NAME", "System Administrator").strip()
                existing_admin = query_db(
                    "SELECT id FROM users WHERE username = ? OR email = ?",
                    (admin_user, admin_mail),
                    one=True
                )
                if not existing_admin:
                    execute_db(
                        """INSERT INTO users (username, email, password_hash, role, full_name)
                           VALUES (?, ?, ?, 'admin', ?)""",
                        (admin_user, admin_mail, generate_password_hash(admin_pw), admin_name)
                    )

            # 3. Auto-seed Delivery Person account if DELIVERY_PASSWORD is set and account does not exist
            delivery_pw = os.environ.get("DELIVERY_PASSWORD")
            if delivery_pw:
                courier_user = os.environ.get("DELIVERY_USERNAME", "courier_agent1").strip()
                courier_mail = os.environ.get("DELIVERY_EMAIL", "courier1@shiptrack.local").strip().lower()
                courier_name = os.environ.get("DELIVERY_NAME", "Courier Agent One").strip()
                courier_phone = os.environ.get("DELIVERY_PHONE", "+91 9876543210").strip()
                existing_courier = query_db(
                    "SELECT id FROM users WHERE username = ? OR email = ?",
                    (courier_user, courier_mail),
                    one=True
                )
                if not existing_courier:
                    execute_db(
                        """INSERT INTO users (username, email, password_hash, role, full_name, phone)
                           VALUES (?, ?, ?, 'delivery_person', ?, ?)""",
                        (courier_user, courier_mail, generate_password_hash(delivery_pw), courier_name, courier_phone)
                    )

    # CLI Command to initialize database
    @app.cli.command("init-db")
    def init_db_command():
        """Clear existing data and create new tables."""
        init_db(app)
        print("Initialized the ShipTrack SQLite database successfully.")

    # Serve frontend single-page application
    @app.route("/", methods=["GET"])
    def serve_frontend_index():
        """Serve the frontend single-page dashboard."""
        from flask import send_from_directory
        return send_from_directory(frontend_dir, "index.html")

    # Base health & telemetry endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        """System health and database connectivity verification."""
        try:
            # Verify DB connectivity with parameterized query
            result = query_db("SELECT 1 AS status;", one=True)
            db_status = "healthy" if result and result["status"] == 1 else "unhealthy"
        except Exception as e:
            db_status = f"error: {str(e)}"

        return jsonify({
            "status": "online",
            "service": "ShipTrack Delivery & Shipment Management (PS-05)",
            "database": db_status
        }), 200

    return app


app = create_app()

if __name__ == "__main__":
    import sys
    if "--init-db" in sys.argv:
        with app.app_context():
            init_db(app)
            print("Database initialized successfully via --init-db.")
    else:
        app.run(host="0.0.0.0", port=5000, debug=True)
