"""Admin Management & Telemetry Blueprint for ShipTrack (PS-05).

Provides:
- GET /api/admin/dashboard: Platform-wide overview, shipment counts by status, and security alerts.
- GET /api/admin/shipments: All shipments across the platform with filtering and courier info.
- GET /api/admin/delivery-persons: Available courier agents for assignment.
- POST /api/admin/shipments/<id>/assign: Assign or re-assign a shipment to a delivery courier.
- POST /api/admin/shipments/<id>/cancel: Administrative cancellation with chain of custody logging.
- GET /api/admin/users: Registered users list with role filtering.
- GET /api/admin/security-events: Paginated intrusion telemetry and security events log.
"""

import math
from flask import Blueprint, request, jsonify, session

try:
    from .db import query_db, execute_db
    from .auth import login_required, role_required
    from .security import add_status_update, log_security_event, check_and_log_suspicious_input
except (ImportError, ValueError):
    from db import query_db, execute_db
    from auth import login_required, role_required
    from security import add_status_update, log_security_event, check_and_log_suspicious_input

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# ==============================================================================
# ADMIN DASHBOARD & METRICS
# ==============================================================================

@admin_bp.route("/dashboard", methods=["GET"])
@login_required
@role_required("admin")
def get_admin_dashboard():
    """Retrieve platform-wide operational metrics, shipments breakdown, and security alerts."""
    # 1. Total and status breakdown for shipments
    status_counts = query_db(
        "SELECT current_status, COUNT(*) as count FROM shipments GROUP BY current_status"
    )

    metrics = {
        "total_shipments": 0,
        "order_placed": 0,
        "picked_up": 0,
        "in_transit": 0,
        "out_for_delivery": 0,
        "delivered": 0,
        "cancelled": 0,
        "unassigned": 0
    }

    for row in status_counts:
        st = row["current_status"]
        cnt = row["count"]
        metrics["total_shipments"] += cnt
        if st == "Order Placed":
            metrics["order_placed"] = cnt
        elif st == "Picked Up":
            metrics["picked_up"] = cnt
        elif st == "In Transit":
            metrics["in_transit"] = cnt
        elif st == "Out for Delivery":
            metrics["out_for_delivery"] = cnt
        elif st == "Delivered":
            metrics["delivered"] = cnt
        elif st == "Cancelled":
            metrics["cancelled"] = cnt

    # Unassigned shipments
    unassigned_row = query_db(
        "SELECT COUNT(*) as count FROM shipments WHERE assigned_delivery_id IS NULL AND current_status != 'Cancelled'",
        one=True
    )
    metrics["unassigned"] = unassigned_row["count"] if unassigned_row else 0

    # 2. User metrics
    user_counts = query_db("SELECT role, COUNT(*) as count FROM users GROUP BY role")
    user_metrics = {"total_users": 0, "customers": 0, "delivery_persons": 0, "admins": 0}
    for row in user_counts:
        r = row["role"]
        c = row["count"]
        user_metrics["total_users"] += c
        if r == "customer":
            user_metrics["customers"] = c
        elif r == "delivery_person":
            user_metrics["delivery_persons"] = c
        elif r == "admin":
            user_metrics["admins"] = c

    # 3. Security events total
    sec_total_row = query_db("SELECT COUNT(*) as total FROM security_events", one=True)
    total_security_events = sec_total_row["total"] if sec_total_row else 0

    # 4. Recent 5 shipments
    recent_shipments = query_db(
        """SELECT s.id, s.tracking_number, s.current_status, s.sender_name, s.recipient_name,
                  s.created_at, u.username as customer_username
           FROM shipments s
           JOIN users u ON s.customer_id = u.id
           ORDER BY s.created_at DESC, s.id DESC
           LIMIT 5"""
    )

    # 5. Recent 5 security events
    recent_events = query_db(
        """SELECT id, event_type, ip, path, details, created_at
           FROM security_events
           ORDER BY created_at DESC, id DESC
           LIMIT 5"""
    )

    return jsonify({
        "metrics": metrics,
        "users": user_metrics,
        "total_security_events": total_security_events,
        "recent_shipments": [dict(s) for s in recent_shipments],
        "recent_security_events": [dict(e) for e in recent_events]
    }), 200


# ==============================================================================
# SHIPMENTS MANAGEMENT
# ==============================================================================

@admin_bp.route("/shipments", methods=["GET"])
@login_required
@role_required("admin")
def list_all_shipments():
    """List all shipments across the platform with filtering and courier details."""
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    except (ValueError, TypeError):
        per_page = 20

    offset = (page - 1) * per_page
    status_filter = request.args.get("status", "").strip()

    if status_filter:
        total_row = query_db(
            "SELECT COUNT(*) AS total FROM shipments WHERE current_status = ?",
            (status_filter,),
            one=True
        )
        total = total_row["total"] if total_row else 0

        shipments = query_db(
            """SELECT s.id, s.tracking_number, s.customer_id, s.assigned_delivery_id,
                      s.sender_name, s.sender_address, s.recipient_name, s.recipient_address,
                      s.recipient_phone, s.package_description, s.weight_kg, s.current_status,
                      s.created_at, s.updated_at,
                      cust.username AS customer_username, cust.email AS customer_email,
                      courier.username AS courier_username, courier.full_name AS courier_name
               FROM shipments s
               JOIN users cust ON s.customer_id = cust.id
               LEFT JOIN users courier ON s.assigned_delivery_id = courier.id
               WHERE s.current_status = ?
               ORDER BY s.created_at DESC, s.id DESC
               LIMIT ? OFFSET ?""",
            (status_filter, per_page, offset)
        )
    else:
        total_row = query_db("SELECT COUNT(*) AS total FROM shipments", one=True)
        total = total_row["total"] if total_row else 0

        shipments = query_db(
            """SELECT s.id, s.tracking_number, s.customer_id, s.assigned_delivery_id,
                      s.sender_name, s.sender_address, s.recipient_name, s.recipient_address,
                      s.recipient_phone, s.package_description, s.weight_kg, s.current_status,
                      s.created_at, s.updated_at,
                      cust.username AS customer_username, cust.email AS customer_email,
                      courier.username AS courier_username, courier.full_name AS courier_name
               FROM shipments s
               JOIN users cust ON s.customer_id = cust.id
               LEFT JOIN users courier ON s.assigned_delivery_id = courier.id
               ORDER BY s.created_at DESC, s.id DESC
               LIMIT ? OFFSET ?""",
            (per_page, offset)
        )

    total_pages = math.ceil(total / per_page) if total > 0 else 1

    return jsonify({
        "shipments": [dict(s) for s in shipments],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages
        }
    }), 200


@admin_bp.route("/delivery-persons", methods=["GET"])
@login_required
@role_required("admin")
def list_delivery_persons():
    """Retrieve list of registered couriers for assignment dropdowns."""
    couriers = query_db(
        """SELECT id, username, full_name, email, phone, created_at
           FROM users
           WHERE role = 'delivery_person'
           ORDER BY full_name ASC, username ASC"""
    )
    return jsonify({"delivery_persons": [dict(c) for c in couriers]}), 200


@admin_bp.route("/shipments/<int:shipment_id>/assign", methods=["POST"])
@login_required
@role_required("admin")
def assign_shipment(shipment_id: int):
    """Assign a shipment to a delivery courier.

    Security Rules:
    - Admin only.
    - Parameterized SQL validates courier role ('delivery_person').
    - Chain of custody update logged via add_status_update().
    """
    admin_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    check_and_log_suspicious_input(data)

    try:
        courier_id = int(data.get("delivery_person_id"))
    except (ValueError, TypeError):
        return jsonify({"error": "Valid delivery_person_id is required."}), 400

    # Verify courier exists and has role 'delivery_person'
    courier = query_db(
        "SELECT id, username, full_name, role FROM users WHERE id = ? AND role = 'delivery_person'",
        (courier_id,),
        one=True
    )
    if not courier:
        return jsonify({"error": "Delivery person not found or user is not a courier."}), 404

    # Verify shipment exists
    shipment = query_db(
        "SELECT id, tracking_number, current_status FROM shipments WHERE id = ?",
        (shipment_id,),
        one=True
    )
    if not shipment:
        return jsonify({"error": "Shipment not found."}), 404

    if shipment["current_status"] in ["Delivered", "Cancelled"]:
        return jsonify({
            "error": f"Cannot assign shipment in terminal state '{shipment['current_status']}'."
        }), 400

    # Update assigned courier
    execute_db(
        """UPDATE shipments
           SET assigned_delivery_id = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (courier_id, shipment_id)
    )

    # Log into cryptographic chain of custody
    courier_display = courier["full_name"] or courier["username"]
    add_status_update(
        shipment_id=shipment_id,
        updated_by_id=admin_id,
        status=shipment["current_status"],
        location="Admin Dispatch Center",
        notes=f"Shipment assigned to courier {courier_display} (ID: {courier_id})."
    )

    return jsonify({
        "message": f"Shipment successfully assigned to courier '{courier_display}'.",
        "shipment_id": shipment_id,
        "assigned_delivery_id": courier_id
    }), 200


@admin_bp.route("/shipments/<int:shipment_id>/cancel", methods=["POST"])
@login_required
@role_required("admin")
def admin_cancel_shipment(shipment_id: int):
    """Administratively cancel a shipment."""
    admin_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    reason = str(data.get("reason", "Administrative cancellation.")).strip()

    shipment = query_db(
        "SELECT id, current_status FROM shipments WHERE id = ?",
        (shipment_id,),
        one=True
    )
    if not shipment:
        return jsonify({"error": "Shipment not found."}), 404

    if shipment["current_status"] in ["Delivered", "Cancelled"]:
        return jsonify({
            "error": f"Shipment is already '{shipment['current_status']}'."
        }), 400

    new_status = "Cancelled"
    execute_db(
        """UPDATE shipments
           SET current_status = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (new_status, shipment_id)
    )

    add_status_update(
        shipment_id=shipment_id,
        updated_by_id=admin_id,
        status=new_status,
        location="Admin Operations",
        notes=f"Admin cancellation: {reason[:300]}"
    )

    return jsonify({
        "message": "Shipment cancelled by administrator.",
        "shipment_id": shipment_id,
        "current_status": new_status
    }), 200


# ==============================================================================
# USER MANAGEMENT & SECURITY TELEMETRY
# ==============================================================================

@admin_bp.route("/users", methods=["GET"])
@login_required
@role_required("admin")
def list_users():
    """List registered users with optional role filtering."""
    role_filter = request.args.get("role", "").strip()

    if role_filter:
        users = query_db(
            """SELECT id, username, email, role, full_name, phone, created_at
               FROM users
               WHERE role = ?
               ORDER BY created_at DESC, id DESC""",
            (role_filter,)
        )
    else:
        users = query_db(
            """SELECT id, username, email, role, full_name, phone, created_at
               FROM users
               ORDER BY created_at DESC, id DESC"""
        )

    return jsonify({"users": [dict(u) for u in users]}), 200


@admin_bp.route("/security-events", methods=["GET"])
@login_required
@role_required("admin")
def get_security_events():
    """Retrieve security and intrusion telemetry events (paginated, newest first)."""
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    except (ValueError, TypeError):
        per_page = 20

    offset = (page - 1) * per_page

    total_row = query_db("SELECT COUNT(*) AS total FROM security_events", one=True)
    total = total_row["total"] if total_row else 0
    total_pages = math.ceil(total / per_page) if total > 0 else 1

    events = query_db(
        """SELECT se.id, se.event_type, se.user_id, se.ip, se.path,
                  se.details, se.created_at,
                  u.username, u.role
           FROM security_events se
           LEFT JOIN users u ON se.user_id = u.id
           ORDER BY se.created_at DESC, se.id DESC
           LIMIT ? OFFSET ?""",
        (per_page, offset)
    )

    result = [dict(e) for e in events]

    return jsonify({
        "events": result,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages
        }
    }), 200
