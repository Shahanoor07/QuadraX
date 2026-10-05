"""ShipTrack Backend Application Entrypoint (PS-05).

Delivery & Shipment Management System.
Configured with SQLite, parameterized query helpers, and secure defaults.
"""

import os
from datetime import timedelta
from flask import Flask, jsonify
from dotenv import load_dotenv

try:
    from .db import close_db, init_db, query_db
    from .auth import auth_bp
    from .shipments import shipments_bp
except (ImportError, ValueError):
    from db import close_db, init_db, query_db
    from auth import auth_bp
    from shipments import shipments_bp

# Load environment variables if .env is present
load_dotenv()


def create_app(test_config=None):
    """Application factory for ShipTrack."""
    app = Flask(__name__, instance_relative_config=True)

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

    # CLI Command to initialize database
    @app.cli.command("init-db")
    def init_db_command():
        """Clear existing data and create new tables."""
        init_db(app)
        print("Initialized the ShipTrack SQLite database successfully.")

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
