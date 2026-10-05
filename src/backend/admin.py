"""Admin Management & Telemetry Blueprint for ShipTrack (PS-05).

Provides:
- GET /api/admin/security-events: Paginated intrusion telemetry and security events log (admin only).
"""

import math
from flask import Blueprint, request, jsonify

try:
    from .db import query_db
    from .auth import login_required, role_required
except (ImportError, ValueError):
    from db import query_db
    from auth import login_required, role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/security-events", methods=["GET"])
@login_required
@role_required("admin")
def get_security_events():
    """Retrieve security and intrusion telemetry events (paginated, newest first).

    Security Rules:
    - Restricted to 'admin' role only via @role_required('admin').
    - Parameterized SQL for pagination limit and offset.
    """
    # Parse pagination parameters safely
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    except (ValueError, TypeError):
        per_page = 20

    offset = (page - 1) * per_page

    # Query total event count via parameterized SQL
    total_row = query_db("SELECT COUNT(*) AS total FROM security_events", one=True)
    total = total_row["total"] if total_row else 0
    total_pages = math.ceil(total / per_page) if total > 0 else 1

    # Query paginated events, newest first
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
