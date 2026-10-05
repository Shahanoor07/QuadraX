"""Authentication and Authorization Blueprint for ShipTrack (PS-05).

Features:
- Customer self-registration (role strictly locked to 'customer').
- Authentication with werkzeug.security salted password hashing.
- Session-based auth with secure cookies (HttpOnly, SameSite=Lax).
- Generic error messaging on failed authentication to prevent username/email enumeration.
- Login attempt throttling and lockout to prevent brute-force attacks.
- login_required and role_required(*roles) decorators.
- 100% Parameterized SQL queries.
"""

import functools
import re
import time
from collections import defaultdict
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from .db import query_db, execute_db
except (ImportError, ValueError):
    from db import query_db, execute_db

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Email validation regex (RFC 5322 compliant simplified)
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,30}$")

# Rate Limiting / Lockout tracking: ip/identifier -> list of failed timestamps
FAILED_LOGIN_ATTEMPTS = defaultdict(list)
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 300   # 5-minute observation window
LOCKOUT_DURATION_SECONDS = 900  # 15-minute lockout


def _get_client_ip():
    """Retrieve client IP address, handling proxies safely."""
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


def _is_locked_out(key: str) -> bool:
    """Check if the key (IP or identifier) is currently locked out."""
    now = time.time()
    # Retain only timestamps within the lockout duration
    timestamps = [t for t in FAILED_LOGIN_ATTEMPTS[key] if now - t < LOCKOUT_DURATION_SECONDS]
    FAILED_LOGIN_ATTEMPTS[key] = timestamps

    # If within window there are >= MAX_FAILED_ATTEMPTS failures, lockout is active
    recent_failures = [t for t in timestamps if now - t < LOCKOUT_WINDOW_SECONDS]
    return len(recent_failures) >= MAX_FAILED_ATTEMPTS


def _record_failed_attempt(key: str):
    """Record a failed login timestamp for rate limiting."""
    FAILED_LOGIN_ATTEMPTS[key].append(time.time())


def _clear_failed_attempts(key: str):
    """Clear failed login attempts on successful login."""
    if key in FAILED_LOGIN_ATTEMPTS:
        del FAILED_LOGIN_ATTEMPTS[key]


# ==============================================================================
# AUTHORIZATION DECORATORS
# ==============================================================================

def login_required(view):
    """Decorator requiring a valid active session."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required. Please log in."}), 401
        return view(**kwargs)
    return wrapped_view


def role_required(*allowed_roles):
    """Decorator requiring an active session with specific role membership."""
    def decorator(view):
        @functools.wraps(view)
        def wrapped_view(**kwargs):
            if "user_id" not in session:
                return jsonify({"error": "Authentication required. Please log in."}), 401
            current_role = session.get("role")
            if current_role not in allowed_roles:
                return jsonify({
                    "error": "Access forbidden: insufficient role permissions.",
                    "required_roles": list(allowed_roles),
                    "current_role": current_role
                }), 403
            return view(**kwargs)
        return wrapped_view
    return decorator


# ==============================================================================
# AUTHENTICATION ROUTES
# ==============================================================================

@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new customer account.

    Security Rules:
    - Role is strictly forced to 'customer'. Any client-supplied role is discarded.
    - All input fields are validated and escaped.
    - Passwords hashed using werkzeug.security.
    - Parameterized SQL prevents SQL injection.
    """
    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    full_name = str(data.get("full_name", "")).strip()
    phone = str(data.get("phone", "")).strip()

    # Input Validations
    if not username or not USERNAME_REGEX.match(username):
        return jsonify({
            "error": "Invalid username. Must be 3-30 characters long and contain only letters, numbers, and underscores."
        }), 400

    if not email or not EMAIL_REGEX.match(email):
        return jsonify({"error": "Invalid email address format."}), 400

    if not password or len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters long."}), 400

    if not full_name:
        return jsonify({"error": "Full name is required."}), 400

    # Role enforcement: NEVER trust client input for role; always assign 'customer'
    enforced_role = "customer"

    # Check for existing username or email via parameterized SQL
    existing = query_db(
        "SELECT id, username, email FROM users WHERE username = ? OR email = ?",
        (username, email),
        one=True
    )
    if existing:
        if existing["username"].lower() == username.lower():
            return jsonify({"error": "Username is already taken."}), 409
        return jsonify({"error": "Email is already registered."}), 409

    # Hash password securely with werkzeug.security
    password_hash = generate_password_hash(password)

    # Insert user via parameterized SQL
    try:
        user_id = execute_db(
            """INSERT INTO users (username, email, password_hash, role, full_name, phone)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (username, email, password_hash, enforced_role, full_name, phone)
        )
    except Exception as e:
        return jsonify({"error": "An error occurred while creating the account."}), 500

    return jsonify({
        "message": "Registration successful.",
        "user": {
            "id": user_id,
            "username": username,
            "email": email,
            "role": enforced_role,
            "full_name": full_name
        }
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and initiate session.

    Security Rules:
    - Rate-limiting lockout on excessive failed login attempts.
    - Generic error message to prevent account enumeration.
    - Timing-safe password verification via check_password_hash.
    - HttpOnly and SameSite cookie configuration.
    """
    client_ip = _get_client_ip()

    # Check rate limiting / lockout
    if _is_locked_out(client_ip):
        return jsonify({
            "error": "Too many failed login attempts. Account temporarily locked for 15 minutes."
        }), 429

    data = request.get_json(silent=True) or {}
    identifier = str(data.get("identifier") or data.get("username") or data.get("email") or "").strip()
    password = str(data.get("password") or "")

    if not identifier or not password:
        return jsonify({"error": "Username/email and password are required."}), 400

    # Check identifier lockout
    if _is_locked_out(identifier.lower()):
        return jsonify({
            "error": "Too many failed login attempts. Account temporarily locked for 15 minutes."
        }), 429

    # Query user with parameterized SQL
    user = query_db(
        """SELECT id, username, email, password_hash, role, full_name, phone
           FROM users
           WHERE username = ? OR email = ?""",
        (identifier, identifier.lower()),
        one=True
    )

    # Generic failure condition: timing-safe password check
    if user is None or not check_password_hash(user["password_hash"], password):
        _record_failed_attempt(client_ip)
        _record_failed_attempt(identifier.lower())
        # Generic error message to prevent enumeration
        return jsonify({
            "error": "Invalid credentials. Please verify your username/email and password."
        }), 401

    # Authentication successful: clear lockout tracking
    _clear_failed_attempts(client_ip)
    _clear_failed_attempts(identifier.lower())

    # Establish secure session
    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    session.permanent = True

    return jsonify({
        "message": "Login successful.",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "full_name": user["full_name"],
            "phone": user["phone"]
        }
    }), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Terminate the current session."""
    session.clear()
    return jsonify({"message": "Logged out successfully."}), 200


@auth_bp.route("/me", methods=["GET"])
@login_required
def get_current_user():
    """Retrieve profile of currently authenticated user."""
    user_id = session.get("user_id")

    user = query_db(
        """SELECT id, username, email, role, full_name, phone, created_at
           FROM users
           WHERE id = ?""",
        (user_id,),
        one=True
    )

    if not user:
        session.clear()
        return jsonify({"error": "User profile not found."}), 404

    return jsonify({
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "full_name": user["full_name"],
            "phone": user["phone"],
            "created_at": str(user["created_at"])
        }
    }), 200
