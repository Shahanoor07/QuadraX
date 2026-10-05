"""Delivery Person Routes for ShipTrack (PS-05).

Delivery & Shipment Management System.
Implements:
- GET /api/delivery/dashboard: Courier dashboard metrics and active tasks.
- GET /api/delivery/shipments: List all assigned shipments with status filtering.
- GET /api/delivery/shipments/<tracking_number>: View assigned shipment details & timeline.
- POST /api/delivery/shipments/<int:shipment_id>/status: Update delivery lifecycle milestones.

Security Rules:
- Restricted to role 'delivery_person' via @role_required('delivery_person').
- Parameterized SQL for all queries.
- Strict ownership verification: couriers can ONLY access and update shipments assigned to them.
- Attempts to access unassigned shipments log UNAUTHORIZED_SHIPMENT_ACCESS and return 404 (anti-probing).
- All status updates are cryptographically chained via add_status_update().
"""

from flask import Blueprint, request, jsonify, session

try:
    from .db import query_db, execute_db
    from .auth import login_required, role_required
    from .security import add_status_update, log_security_event, check_and_log_suspicious_input
except (ImportError, ValueError):
    from db import query_db, execute_db
    from auth import login_required, role_required
    from security import add_status_update, log_security_event, check_and_log_suspicious_input

delivery_bp = Blueprint("delivery", __name__, url_prefix="/api/delivery")

ALLOWED_COURIER_STATUSES = ["Picked Up", "In Transit", "Out for Delivery", "Delivered"]


@delivery_bp.route("/dashboard", methods=["GET"])
@login_required
@role_required("delivery_person")
def courier_dashboard():
    """Retrieve courier summary metrics and assigned active tasks."""
    courier_id = session["user_id"]

    # Parameterized status aggregation
    counts = query_db(
        """SELECT current_status, COUNT(*) as count
           FROM shipments
           WHERE assigned_delivery_id = ?
           GROUP BY current_status""",
        (courier_id,)
    )

    metrics = {
        "total_assigned": 0,
        "active": 0,
        "picked_up": 0,
        "in_transit": 0,
        "out_for_delivery": 0,
        "delivered": 0
    }

    for row in counts:
        st = row["current_status"]
        cnt = row["count"]
        metrics["total_assigned"] += cnt
        if st in ["Order Placed", "Picked Up", "In Transit", "Out for Delivery"]:
            metrics["active"] += cnt
        if st == "Picked Up":
            metrics["picked_up"] = cnt
        elif st == "In Transit":
            metrics["in_transit"] = cnt
        elif st == "Out for Delivery":
            metrics["out_for_delivery"] = cnt
        elif st == "Delivered":
            metrics["delivered"] = cnt

    # Fetch active assigned shipments
    active_shipments = query_db(
        """SELECT id, tracking_number, customer_id, sender_name, sender_address,
                  recipient_name, recipient_address, recipient_phone,
                  package_description, weight_kg, current_status, updated_at
           FROM shipments
           WHERE assigned_delivery_id = ? AND current_status != 'Delivered' AND current_status != 'Cancelled'
           ORDER BY updated_at DESC, id DESC""",
        (courier_id,)
    )

    return jsonify({
        "metrics": metrics,
        "active_shipments": [dict(s) for s in active_shipments]
    }), 200


@delivery_bp.route("/shipments", methods=["GET"])
@login_required
@role_required("delivery_person")
def list_assigned_shipments():
    """List all shipments assigned to the authenticated delivery courier."""
    courier_id = session["user_id"]
    status_filter = request.args.get("status", "").strip()

    if status_filter:
        shipments = query_db(
            """SELECT id, tracking_number, customer_id, sender_name, sender_address,
                      recipient_name, recipient_address, recipient_phone,
                      package_description, weight_kg, current_status, created_at, updated_at
               FROM shipments
               WHERE assigned_delivery_id = ? AND current_status = ?
               ORDER BY updated_at DESC, id DESC""",
            (courier_id, status_filter)
        )
    else:
        shipments = query_db(
            """SELECT id, tracking_number, customer_id, sender_name, sender_address,
                      recipient_name, recipient_address, recipient_phone,
                      package_description, weight_kg, current_status, created_at, updated_at
               FROM shipments
               WHERE assigned_delivery_id = ?
               ORDER BY updated_at DESC, id DESC""",
            (courier_id,)
        )

    result = [dict(s) for s in shipments]
    return jsonify({"shipments": result, "count": len(result)}), 200


@delivery_bp.route("/shipments/<tracking_number>", methods=["GET"])
@login_required
@role_required("delivery_person")
def get_assigned_shipment(tracking_number: str):
    """Retrieve details and audit timeline for an assigned shipment.

    Security:
    - BOLA Check: Only the assigned courier can access this record.
    - Non-assigned inquiries return 404 and log UNAUTHORIZED_SHIPMENT_ACCESS.
    """
    courier_id = session["user_id"]
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

    if not shipment or shipment["assigned_delivery_id"] != courier_id:
        log_security_event(
            "UNAUTHORIZED_SHIPMENT_ACCESS",
            f"Courier {courier_id} attempted unauthorized access to tracking '{tracking_number}'"
        )
        return jsonify({"error": "Shipment not found."}), 404

    # Fetch status timeline
    updates = query_db(
        """SELECT su.id, su.shipment_id, su.updated_by_id, su.status,
                  su.location, su.notes, su.timestamp, su.prev_hash, su.record_hash,
                  u.username AS updater_username, u.role AS updater_role
           FROM status_updates su
           JOIN users u ON su.updated_by_id = u.id
           WHERE su.shipment_id = ?
           ORDER BY su.id ASC""",
        (shipment["id"],)
    )

    return jsonify({
        "shipment": dict(shipment),
        "timeline": [dict(u) for u in updates]
    }), 200


@delivery_bp.route("/shipments/<int:shipment_id>/status", methods=["POST"])
@login_required
@role_required("delivery_person")
def update_shipment_status(shipment_id: int):
    """Update delivery milestone stage and record in cryptographic chain of custody.

    Security Rules:
    - Only the courier assigned to this shipment can update its status.
    - Couriers can only transition to 'Picked Up', 'In Transit', 'Out for Delivery', or 'Delivered'.
    - Terminal states ('Delivered', 'Cancelled') cannot be modified further.
    - Logs status into cryptographic hash chain via add_status_update().
    """
    courier_id = session["user_id"]
    data = request.get_json(silent=True) or {}

    # Passive intrusion sensor: scan for suspicious inputs
    check_and_log_suspicious_input(data)

    status = str(data.get("status", "")).strip()
    location = str(data.get("location", "")).strip()
    notes = str(data.get("notes", "")).strip()

    # Validate status choice
    if status not in ALLOWED_COURIER_STATUSES:
        return jsonify({
            "error": f"Invalid status '{status}'. Allowed courier statuses: {ALLOWED_COURIER_STATUSES}"
        }), 400

    if not location or len(location) < 2 or len(location) > 200:
        return jsonify({"error": "Location is required (2-200 characters)."}), 400

    if notes and len(notes) > 500:
        return jsonify({"error": "Notes must not exceed 500 characters."}), 400

    # Fetch shipment and verify courier assignment (BOLA check)
    shipment = query_db(
        "SELECT id, current_status, assigned_delivery_id FROM shipments WHERE id = ?",
        (shipment_id,),
        one=True
    )

    if not shipment or shipment["assigned_delivery_id"] != courier_id:
        log_security_event(
            "UNAUTHORIZED_SHIPMENT_ACCESS",
            f"Courier {courier_id} attempted unauthorized status modification on shipment ID {shipment_id}"
        )
        return jsonify({"error": "Shipment not found."}), 404

    # Terminal state check
    current_status = shipment["current_status"]
    if current_status in ["Delivered", "Cancelled"]:
        return jsonify({
            "error": f"Cannot update shipment. It is already in terminal state '{current_status}'."
        }), 400

    # Parameterized update of shipment status
    execute_db(
        """UPDATE shipments
           SET current_status = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ? AND assigned_delivery_id = ?""",
        (status, shipment_id, courier_id)
    )

    # Cryptographically chain status update into immutable audit trail
    update_id = add_status_update(
        shipment_id=shipment_id,
        updated_by_id=courier_id,
        status=status,
        location=location,
        notes=notes or f"Status updated to '{status}' by courier."
    )

    return jsonify({
        "message": f"Shipment status updated to '{status}'.",
        "shipment_id": shipment_id,
        "new_status": status,
        "status_update_id": update_id
    }), 200


@delivery_bp.route("/shipments/<int:shipment_id>/telemetry", methods=["POST"])
@login_required
@role_required("delivery_person")
def record_shipment_telemetry(shipment_id: int):
    """Record live GPS coordinate telemetry for an assigned shipment.

    Security Rules:
    - Only the assigned courier can record GPS location data.
    - Validates latitude (-90 to 90) and longitude (-180 to 180).
    - Cannot record telemetry on Delivered or Cancelled shipments.
    """
    courier_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    check_and_log_suspicious_input(data)

    shipment = query_db(
        "SELECT id, current_status, assigned_delivery_id FROM shipments WHERE id = ?",
        (shipment_id,),
        one=True
    )

    if not shipment or shipment["assigned_delivery_id"] != courier_id:
        log_security_event(
            "UNAUTHORIZED_SHIPMENT_ACCESS",
            f"Courier {courier_id} attempted unauthorized telemetry post on shipment {shipment_id}"
        )
        return jsonify({"error": "Shipment not found."}), 404

    if shipment["current_status"] in ["Delivered", "Cancelled"]:
        return jsonify({
            "error": f"Cannot submit telemetry for shipment in terminal state '{shipment['current_status']}'."
        }), 400

    try:
        latitude = float(data.get("latitude"))
        longitude = float(data.get("longitude"))
        if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
            return jsonify({"error": "Latitude must be between -90 and 90, longitude between -180 and 180."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Valid numeric latitude and longitude are required."}), 400

    try:
        speed_kmh = max(0.0, float(data.get("speed_kmh", 0.0)))
    except (ValueError, TypeError):
        speed_kmh = 0.0

    try:
        heading_degrees = float(data.get("heading_degrees")) if data.get("heading_degrees") is not None else None
    except (ValueError, TypeError):
        heading_degrees = None

    try:
        battery_pct = float(data.get("battery_pct")) if data.get("battery_pct") is not None else None
    except (ValueError, TypeError):
        battery_pct = None

    telemetry_id = execute_db(
        """INSERT INTO shipment_telemetry (
            shipment_id, recorded_by_id, latitude, longitude,
            speed_kmh, heading_degrees, battery_pct
        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (shipment_id, courier_id, latitude, longitude, speed_kmh, heading_degrees, battery_pct)
    )

    return jsonify({
        "message": "GPS telemetry recorded successfully.",
        "telemetry_id": telemetry_id,
        "latitude": latitude,
        "longitude": longitude,
        "speed_kmh": speed_kmh
    }), 201
