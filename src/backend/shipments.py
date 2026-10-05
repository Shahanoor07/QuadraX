"""Customer Shipment Routes for ShipTrack (PS-05).

Delivery & Shipment Management.
Implements:
- POST /api/shipments: Create shipment with unique tracking number & initial status_update.
- GET /api/shipments: List only the authenticated customer's own shipments (newest first).
- GET /api/shipments/<tracking_number>: View shipment and tracking timeline with strict BOLA/ownership check.
- POST /api/shipments/<id>/cancel: Cancel customer's own shipment (only allowed in 'Order Placed' status).

Security:
- 100% Parameterized SQL queries.
- Strict input sanitization and length validation.
- Server-side customer_id and tracking number generation.
- Returns 404 (anti-probing) when unauthorized users try to access other users' shipments.
"""

import re
import secrets
import time
from flask import Blueprint, request, jsonify, session

try:
    from .db import query_db, execute_db
    from .auth import login_required, role_required
except (ImportError, ValueError):
    from db import query_db, execute_db
    from auth import login_required, role_required

shipments_bp = Blueprint("shipments", __name__, url_prefix="/api/shipments")

PHONE_REGEX = re.compile(r"^[+0-9\s\-()]{7,25}$")


def _generate_unique_tracking_number() -> str:
    """Generate a cryptographically secure, non-sequential tracking number.

    Format: ST-YYYYMMDD-XXXXXX (e.g., ST-20261005-A7B2C9)
    """
    date_prefix = time.strftime("%Y%m%d")
    random_suffix = secrets.token_hex(3).upper()
    return f"ST-{date_prefix}-{random_suffix}"


# ==============================================================================
# CUSTOMER SHIPMENT ENDPOINTS
# ==============================================================================

@shipments_bp.route("", methods=["POST"])
@login_required
@role_required("customer")
def create_shipment():
    """Create a new shipment request.

    Security Rules:
    - Only authenticated customers can create shipments.
    - customer_id is strictly derived from server session.
    - tracking_number is generated server-side.
    - Initial status is hardcoded to 'Order Placed'.
    - All input fields are validated and length-bounded.
    """
    data = request.get_json(silent=True) or {}

    sender_name = str(data.get("sender_name", "")).strip()
    sender_address = str(data.get("sender_address") or data.get("pickup_address", "")).strip()
    recipient_name = str(data.get("recipient_name", "")).strip()
    recipient_address = str(data.get("recipient_address") or data.get("delivery_address", "")).strip()
    recipient_phone = str(data.get("recipient_phone", "")).strip()
    package_description = str(data.get("package_description", "")).strip()

    # Weight validation
    raw_weight = data.get("weight_kg", 1.0)
    try:
        weight_kg = float(raw_weight)
        if weight_kg <= 0.0 or weight_kg > 1000.0:
            return jsonify({"error": "Weight must be between 0.01 kg and 1000 kg."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid weight value."}), 400

    # Input length & format validations
    if not sender_name or len(sender_name) > 100:
        return jsonify({"error": "Sender name is required and must not exceed 100 characters."}), 400

    if not sender_address or len(sender_address) < 5 or len(sender_address) > 300:
        return jsonify({"error": "Pickup address is required (5-300 characters)."}), 400

    if not recipient_name or len(recipient_name) > 100:
        return jsonify({"error": "Recipient name is required and must not exceed 100 characters."}), 400

    if not recipient_address or len(recipient_address) < 5 or len(recipient_address) > 300:
        return jsonify({"error": "Delivery address is required (5-300 characters)."}), 400

    if not recipient_phone or not PHONE_REGEX.match(recipient_phone):
        return jsonify({"error": "Valid recipient phone number is required (7-25 digits/symbols)."}), 400

    if not package_description or len(package_description) > 500:
        return jsonify({"error": "Package description is required and must not exceed 500 characters."}), 400

    # Derive customer_id from authenticated session
    customer_id = session["user_id"]

    # Generate unique tracking number
    tracking_number = _generate_unique_tracking_number()
    # Ensure tracking number uniqueness in DB
    while query_db("SELECT id FROM shipments WHERE tracking_number = ?", (tracking_number,), one=True):
        tracking_number = _generate_unique_tracking_number()

    # Insert shipment via parameterized SQL
    initial_status = "Order Placed"
    shipment_id = execute_db(
        """INSERT INTO shipments (
            tracking_number, customer_id, sender_name, sender_address,
            recipient_name, recipient_address, recipient_phone,
            package_description, weight_kg, current_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            tracking_number, customer_id, sender_name, sender_address,
            recipient_name, recipient_address, recipient_phone,
            package_description, round(weight_kg, 2), initial_status
        )
    )

    # Insert initial status_updates audit record
    execute_db(
        """INSERT INTO status_updates (
            shipment_id, updated_by_id, status, location, notes
        ) VALUES (?, ?, ?, ?, ?)""",
        (
            shipment_id, customer_id, initial_status,
            sender_address, "Shipment order registered in system."
        )
    )

    return jsonify({
        "message": "Shipment created successfully.",
        "shipment": {
            "id": shipment_id,
            "tracking_number": tracking_number,
            "current_status": initial_status,
            "sender_name": sender_name,
            "sender_address": sender_address,
            "recipient_name": recipient_name,
            "recipient_address": recipient_address,
            "recipient_phone": recipient_phone,
            "package_description": package_description,
            "weight_kg": round(weight_kg, 2)
        }
    }), 201


@shipments_bp.route("", methods=["GET"])
@login_required
@role_required("customer")
def list_my_shipments():
    """List only the authenticated customer's own shipments (history, newest first).

    Security Rules:
    - Parameterized filter on customer_id guarantees object isolation.
    """
    customer_id = session["user_id"]

    shipments = query_db(
        """SELECT id, tracking_number, customer_id, assigned_delivery_id,
                  sender_name, sender_address, recipient_name, recipient_address,
                  recipient_phone, package_description, weight_kg, current_status,
                  created_at, updated_at
           FROM shipments
           WHERE customer_id = ?
           ORDER BY created_at DESC, id DESC""",
        (customer_id,)
    )

    result = [dict(s) for s in shipments]
    return jsonify({"shipments": result, "count": len(result)}), 200


@shipments_bp.route("/<tracking_number>", methods=["GET"])
@login_required
def get_shipment_details(tracking_number: str):
    """Retrieve shipment details and status timeline by tracking number.

    Security Rules:
    - A customer can only view their own shipments.
    - To prevent object enumeration (BOLA / IDOR), return 404 (not 403) for other customers' shipments.
    - Admin users and the assigned delivery person may also view the shipment.
    """
    tracking_number = str(tracking_number).strip()

    shipment = query_db(
        """SELECT id, tracking_number, customer_id, assigned_delivery_id,
                  sender_name, sender_address, recipient_name, recipient_address,
                  recipient_phone, package_description, weight_kg, current_status,
                  created_at, updated_at
           FROM shipments
           WHERE tracking_number = ?""",
        (tracking_number,),
        one=True
    )

    if not shipment:
        return jsonify({"error": "Shipment not found."}), 404

    current_user_id = session["user_id"]
    current_role = session.get("role")

    # Authorization Check:
    # 1. Admin can view any shipment
    # 2. Customer can only view if customer_id matches
    # 3. Delivery person can only view if assigned_delivery_id matches
    is_authorized = (
        current_role == "admin" or
        (current_role == "customer" and shipment["customer_id"] == current_user_id) or
        (current_role == "delivery_person" and shipment["assigned_delivery_id"] == current_user_id)
    )

    if not is_authorized:
        # Return 404 (not 403) to prevent tracking number enumeration/probing
        return jsonify({"error": "Shipment not found."}), 404

    # Fetch status timeline audit trail
    updates = query_db(
        """SELECT su.id, su.shipment_id, su.updated_by_id, su.status,
                  su.location, su.notes, su.timestamp,
                  u.username AS updater_username, u.role AS updater_role
           FROM status_updates su
           JOIN users u ON su.updated_by_id = u.id
           WHERE su.shipment_id = ?
           ORDER BY su.timestamp ASC, su.id ASC""",
        (shipment["id"],)
    )

    return jsonify({
        "shipment": dict(shipment),
        "timeline": [dict(u) for u in updates]
    }), 200


@shipments_bp.route("/<int:shipment_id>/cancel", methods=["POST"])
@login_required
@role_required("customer")
def cancel_shipment(shipment_id: int):
    """Cancel a customer's own shipment.

    Security Rules:
    - Customer can only cancel their own shipment (ownership check).
    - If the shipment belongs to someone else or does not exist, return 404 to prevent ID probing.
    - Only shipments in 'Order Placed' status can be cancelled.
    """
    customer_id = session["user_id"]

    # Parameterized lookup
    shipment = query_db(
        "SELECT id, customer_id, current_status FROM shipments WHERE id = ?",
        (shipment_id,),
        one=True
    )

    # Ownership check: return 404 if not found or owned by another user
    if not shipment or shipment["customer_id"] != customer_id:
        return jsonify({"error": "Shipment not found."}), 404

    # Status check: only 'Order Placed' can be cancelled
    if shipment["current_status"] != "Order Placed":
        return jsonify({
            "error": f"Cannot cancel shipment. Current status is '{shipment['current_status']}'. Only 'Order Placed' shipments can be cancelled."
        }), 400

    # Update shipment status
    new_status = "Cancelled"
    execute_db(
        """UPDATE shipments
           SET current_status = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ? AND customer_id = ?""",
        (new_status, shipment_id, customer_id)
    )

    # Record cancellation event in status_updates audit trail
    execute_db(
        """INSERT INTO status_updates (
            shipment_id, updated_by_id, status, location, notes
        ) VALUES (?, ?, ?, ?, ?)""",
        (shipment_id, customer_id, new_status, "Customer Portal", "Shipment cancelled by customer.")
    )

    return jsonify({
        "message": "Shipment cancelled successfully.",
        "shipment_id": shipment_id,
        "current_status": new_status
    }), 200
