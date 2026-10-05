"""Security Foundation Module for ShipTrack (PS-05).

Features:
1. Cryptographic Chain of Custody:
   - SHA-256 hash chaining on status_updates (prev_hash and record_hash).
   - Fixed genesis value for the initial shipment milestone.
   - add_status_update() centralized helper.
   - verify_shipment_chain() integrity audit tool.

2. Attack Detection & Audit Logging:
   - security_events table tracking failed logins, lockouts, 401/403 denials,
     unauthorized shipment access attempts, and suspicious inputs.
   - log_security_event() centralized logger.
   - check_and_log_suspicious_input() passive telemetry helper.
"""

import hashlib
import re
import time
from flask import request, session, has_request_context

try:
    from .db import query_db, execute_db
except (ImportError, ValueError):
    from db import query_db, execute_db

# Genesis hash for the initial block in a shipment's chain of custody
GENESIS_PREV_HASH = "0" * 64

# Regex patterns for passive intrusion detection (logging only)
SUSPICIOUS_PATTERNS = [
    (re.compile(r"(\bUNION\b\s+\bSELECT\b|'\s*OR\s*['\d]=|--|;\s*DROP\b)", re.IGNORECASE), "SQLi Pattern"),
    (re.compile(r"(<script\b|javascript:|onerror\s*=|onload\s*=)", re.IGNORECASE), "XSS Pattern"),
    (re.compile(r"(\.\./\.\./|\.\.\\\.\.\\)", re.IGNORECASE), "Path Traversal"),
]


# ==============================================================================
# 1. CRYPTOGRAPHIC CHAIN OF CUSTODY
# ==============================================================================

def compute_status_hash(shipment_id: int, status: str, location: str, updated_by_id: int, timestamp: str, prev_hash: str) -> str:
    """Compute canonical SHA-256 digest over status update fields.

    Payload format: {shipment_id}|{status}|{location}|{updated_by}|{timestamp}|{prev_hash}
    """
    payload = f"{shipment_id}|{status}|{location}|{updated_by_id}|{timestamp}|{prev_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def add_status_update(shipment_id: int, updated_by_id: int, status: str, location: str, notes: str = None) -> int:
    """Add a new status update to a shipment with SHA-256 chain of custody hashing.

    Retrieves the previous record_hash for the shipment (or uses GENESIS_PREV_HASH),
    computes record_hash over the new milestone, and persists the record.
    """
    # Fetch last record for this shipment
    last_record = query_db(
        "SELECT record_hash FROM status_updates WHERE shipment_id = ? ORDER BY id DESC LIMIT 1",
        (shipment_id,),
        one=True
    )

    if last_record and last_record["record_hash"]:
        prev_hash = last_record["record_hash"]
    else:
        prev_hash = GENESIS_PREV_HASH

    # ISO-like UTC timestamp ensures consistent string representation
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

    # Compute SHA-256 record hash
    record_hash = compute_status_hash(shipment_id, status, location, updated_by_id, timestamp, prev_hash)

    # Parameterized insert into status_updates
    update_id = execute_db(
        """INSERT INTO status_updates
           (shipment_id, updated_by_id, status, location, notes, timestamp, prev_hash, record_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (shipment_id, updated_by_id, status, location, notes, timestamp, prev_hash, record_hash)
    )

    return update_id


def verify_shipment_chain(shipment_id: int) -> dict:
    """Recompute the hash chain for a shipment and return validity or the first broken record.

    Returns:
        dict: {"valid": bool, "records_count": int, "broken_record": dict (if invalid)}
    """
    records = query_db(
        """SELECT id, shipment_id, updated_by_id, status, location, notes, timestamp, prev_hash, record_hash
           FROM status_updates
           WHERE shipment_id = ?
           ORDER BY id ASC""",
        (shipment_id,)
    )

    if not records:
        return {
            "valid": True,
            "message": "No status updates recorded for this shipment.",
            "records_count": 0
        }

    expected_prev_hash = GENESIS_PREV_HASH

    for idx, rec in enumerate(records):
        rec_id = rec["id"]
        rec_status = rec["status"]
        rec_location = rec["location"]
        rec_updated_by = rec["updated_by_id"]
        rec_timestamp = str(rec["timestamp"])
        actual_prev_hash = rec["prev_hash"]
        actual_record_hash = rec["record_hash"]

        # Check 1: Previous hash link
        if actual_prev_hash != expected_prev_hash:
            return {
                "valid": False,
                "error": "Chain of custody broken: previous hash pointer mismatch.",
                "broken_record": {
                    "id": rec_id,
                    "sequence_index": idx,
                    "status": rec_status,
                    "recorded_prev_hash": actual_prev_hash,
                    "expected_prev_hash": expected_prev_hash,
                    "recorded_hash": actual_record_hash
                }
            }

        # Check 2: Content integrity hash
        recomputed_hash = compute_status_hash(
            rec["shipment_id"], rec_status, rec_location, rec_updated_by, rec_timestamp, actual_prev_hash
        )

        if actual_record_hash != recomputed_hash:
            return {
                "valid": False,
                "error": "Chain of custody broken: record content hash mismatch (tampered record data).",
                "broken_record": {
                    "id": rec_id,
                    "sequence_index": idx,
                    "status": rec_status,
                    "recorded_hash": actual_record_hash,
                    "expected_hash": recomputed_hash,
                    "recorded_prev_hash": actual_prev_hash
                }
            }

        expected_prev_hash = actual_record_hash

    return {
        "valid": True,
        "message": "Chain of custody integrity verified successfully.",
        "records_count": len(records),
        "latest_hash": records[-1]["record_hash"]
    }


# ==============================================================================
# 2. ATTACK DETECTION & AUDIT LOGGING
# ==============================================================================

def log_security_event(event_type: str, details: str = "", user_id: int = None, ip: str = None, path: str = None):
    """Log a security event into the security_events table for telemetry and intrusion analysis."""
    if has_request_context():
        if ip is None:
            if request.headers.get("X-Forwarded-For"):
                ip = request.headers.get("X-Forwarded-For").split(",")[0].strip()
            else:
                ip = request.remote_addr or "127.0.0.1"
        if path is None:
            path = request.path
        if user_id is None:
            user_id = session.get("user_id")
    else:
        ip = ip or "127.0.0.1"
        path = path or "/"

    try:
        execute_db(
            """INSERT INTO security_events (event_type, user_id, ip, path, details)
               VALUES (?, ?, ?, ?, ?)""",
            (event_type, user_id, ip, path, str(details))
        )
    except Exception as e:
        print(f"[SECURITY_LOG_WARNING] Could not write security event ({event_type}): {e}")


def check_and_log_suspicious_input(data: dict):
    """Scan request input dictionary for suspicious injection signatures and log telemetry.

    Note: This is an audit/detection sensor only; actual defense is provided by parameterized SQL.
    """
    if not isinstance(data, dict):
        return

    for key, val in data.items():
        if isinstance(val, str):
            for pattern, pattern_name in SUSPICIOUS_PATTERNS:
                if pattern.search(val):
                    log_security_event(
                        "SUSPICIOUS_INPUT",
                        f"{pattern_name} detected in field '{key}': {val[:100]}"
                    )
                    break
