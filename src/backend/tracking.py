"""Public Ephemeral Live GPS Tracking Blueprint for ShipTrack (PS-05).

Provides:
- GET /api/tracking/live/<token>: Single-use, time-bound ephemeral tracking link for high-value cargo.
  - Token verified against SHA-256 hash.
  - Automatically burned upon first access (anti-replay guarantee).
  - Expiration checked against UTC timestamp.
  - Full telemetry and GPS coordinates returned securely.
"""

import hashlib
import time
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify

try:
    from .db import query_db, execute_db
    from .security import log_security_event
except (ImportError, ValueError):
    from db import query_db, execute_db
    from security import log_security_event

tracking_bp = Blueprint("tracking", __name__, url_prefix="/api/tracking")


def _get_client_ip():
    """Retrieve client IP address safely."""
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


@tracking_bp.route("/live/<token>", methods=["GET"])
def access_live_tracking(token: str):
    """Access live GPS location and status using an ephemeral single-use token.

    Security Rules:
    - Never stores raw tokens; matches incoming token via SHA-256 digest.
    - Single-Use Burn: Marks is_used = 1 immediately on access.
    - Anti-Replay: Subsequent requests with the same token are rejected (HTTP 410) and logged.
    - Expiration Check: Expired tokens rejected with HTTP 410.
    """
    token = str(token).strip()
    if not token or len(token) < 20:
        return jsonify({"error": "Invalid tracking link format."}), 400

    client_ip = _get_client_ip()

    # Compute SHA-256 digest of incoming token
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    # Query token record joined with shipment data
    record = query_db(
        """SELECT tt.token_hash, tt.shipment_id, tt.expires_at, tt.is_used, tt.used_at,
                  s.tracking_number, s.current_status, s.package_description,
                  s.recipient_name, s.recipient_address
           FROM tracking_tokens tt
           JOIN shipments s ON tt.shipment_id = s.id
           WHERE tt.token_hash = ?""",
        (token_hash,),
        one=True
    )

    if not record:
        log_security_event(
            "INVALID_TRACKING_TOKEN",
            f"Invalid/unknown token attempt from IP {client_ip} (token prefix: {token[:8]}...)",
            ip=client_ip
        )
        return jsonify({"error": "Invalid or expired tracking link."}), 404

    shipment_id = record["shipment_id"]

    # Check 1: Anti-Replay (has token already been burned?)
    if record["is_used"] == 1:
        log_security_event(
            "REPLAY_ATTACK_DETECTED",
            f"Replay attempt on burned 1-time tracking token for shipment {shipment_id} (used at {record['used_at']})",
            ip=client_ip
        )
        return jsonify({
            "error": "This single-use tracking link has already been used and permanently invalidated.",
            "code": "TOKEN_ALREADY_USED"
        }), 410

    # Check 2: Expiration check
    expires_str = str(record["expires_at"])
    now_utc = datetime.now(timezone.utc)
    try:
        # SQLite stores "YYYY-MM-DD HH:MM:SS"
        exp_dt = datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        if now_utc > exp_dt:
            log_security_event(
                "EXPIRED_TRACKING_TOKEN",
                f"Access attempt with expired tracking token for shipment {shipment_id} (expired at {expires_str})",
                ip=client_ip
            )
            return jsonify({
                "error": "This single-use tracking link has expired.",
                "code": "TOKEN_EXPIRED"
            }), 410
    except ValueError:
        pass

    # Burn token immediately to ensure strict 1-time single-use access
    execute_db(
        """UPDATE tracking_tokens
           SET is_used = 1, used_at = CURRENT_TIMESTAMP, used_ip = ?
           WHERE token_hash = ?""",
        (client_ip, token_hash)
    )

    # Fetch latest live GPS telemetry
    telemetry = query_db(
        """SELECT latitude, longitude, speed_kmh, heading_degrees, battery_pct, timestamp
           FROM shipment_telemetry
           WHERE shipment_id = ?
           ORDER BY id DESC LIMIT 1""",
        (shipment_id,),
        one=True
    )

    # Fetch milestone audit summary
    milestones = query_db(
        """SELECT status, location, timestamp
           FROM status_updates
           WHERE shipment_id = ?
           ORDER BY id ASC""",
        (shipment_id,)
    )

    return jsonify({
        "success": True,
        "security_policy": "SINGLE_USE_EPHEMERAL_ACCESS",
        "notice": "This link has been accessed and permanently burned. It cannot be used again.",
        "shipment": {
            "tracking_number": record["tracking_number"],
            "current_status": record["current_status"],
            "package_description": record["package_description"],
            "recipient_name": record["recipient_name"],
            "destination": record["recipient_address"]
        },
        "live_gps": dict(telemetry) if telemetry else None,
        "milestones": [dict(m) for m in milestones]
    }), 200
