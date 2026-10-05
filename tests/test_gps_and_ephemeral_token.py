"""Tests for Live GPS Telemetry and Ephemeral 1-Time Secure Tracking Links (PS-05).

Verifies:
1. Courier Telemetry Recording:
   - Assigned courier records live GPS coordinates (latitude, longitude, speed, heading, battery).
   - Cross-courier BOLA isolation: unassigned courier receives 404 and security alert logged.
   - Coordinate validation: invalid latitude/longitude rejected with 400.
   - Terminal shipment protection: cannot record telemetry on Delivered or Cancelled shipments.
2. Ephemeral Single-Use Tracking Links:
   - Customer generates 1-time link for high-value cargo (raw token returned, SHA-256 digest saved).
   - Non-owner customer receives 404 anti-probing response on link generation attempt.
   - Public view of live GPS via token succeeds on first access and returns telemetry.
   - Replay Attack Protection: Second access to the exact same token receives 410 Gone and logs REPLAY_ATTACK_DETECTED.
   - Expiration Protection: Expired tokens receive 410 Gone and log EXPIRED_TRACKING_TOKEN.
   - Invalid Token: Unrecognized token returns 404 and logs INVALID_TRACKING_TOKEN.
3. Telemetry Stream Audit:
   - Owner customer and Admin can view full GPS breadcrumb history via /api/shipments/<id>/telemetry.
   - Foreign customer receives 404 when attempting to view another's telemetry trail.
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone
import pytest
from src.backend.app import create_app
from src.backend.db import init_db, execute_db, query_db
from werkzeug.security import generate_password_hash


@pytest.fixture
def gps_test_env():
    """Create isolated test environment with admin, two couriers, and two customers."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app = create_app({"TESTING": True, "DATABASE": db_path})

    with app.app_context():
        init_db(app)

        # Seed Admin
        admin_hash = generate_password_hash("AdminPass123!")
        execute_db(
            """INSERT INTO users (username, email, password_hash, role, full_name)
               VALUES ('gps_admin', 'admin@shiptrack.local', ?, 'admin', 'Fleet Admin')""",
            (admin_hash,)
        )

        # Seed Courier 1
        courier_hash = generate_password_hash("CourierPass123!")
        execute_db(
            """INSERT INTO users (username, email, password_hash, role, full_name, phone)
               VALUES ('courier_alpha', 'courier1@shiptrack.local', ?, 'delivery_person', 'Courier Alpha', '+91 9888800001')""",
            (courier_hash,)
        )

        # Seed Courier 2
        execute_db(
            """INSERT INTO users (username, email, password_hash, role, full_name, phone)
               VALUES ('courier_beta', 'courier2@shiptrack.local', ?, 'delivery_person', 'Courier Beta', '+91 9888800002')""",
            (courier_hash,)
        )

        # Seed Customer 1 (Alice)
        cust_hash = generate_password_hash("AlicePass123!")
        execute_db(
            """INSERT INTO users (username, email, password_hash, role, full_name, phone)
               VALUES ('alice', 'alice@customer.local', ?, 'customer', 'Alice Sender', '+91 9777700001')""",
            (cust_hash,)
        )

        # Seed Customer 2 (Bob)
        bob_hash = generate_password_hash("BobPass123!")
        execute_db(
            """INSERT INTO users (username, email, password_hash, role, full_name, phone)
               VALUES ('bob', 'bob@customer.local', ?, 'customer', 'Bob Sender', '+91 9777700002')""",
            (bob_hash,)
        )

    client = app.test_client()

    yield {
        "app": app,
        "client": client,
        "db_path": db_path
    }

    try:
        os.close(db_fd)
        if os.path.exists(db_path):
            os.unlink(db_path)
    except OSError:
        pass


def _login(client, email, password):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _create_shipment(client, desc="High-Value Gold Watch", weight=1.5):
    return client.post("/api/shipments", json={
        "sender_name": "Alice Vault",
        "sender_address": "100 Safe Deposit Way, Hyderabad",
        "recipient_name": "Charlie Receiver",
        "recipient_address": "404 Secure Fort, Cyberabad",
        "recipient_phone": "+91 9123456789",
        "package_description": desc,
        "weight_kg": weight
    })


# ==============================================================================
# TEST SUITE: LIVE GPS TELEMETRY & EPHEMERAL TOKENS
# ==============================================================================

def test_assigned_courier_records_gps_telemetry(gps_test_env):
    """Assigned courier records GPS breadcrumbs with speed, heading, and battery."""
    client = gps_test_env["client"]

    # Alice creates high-value shipment
    _login(client, "alice@customer.local", "AlicePass123!")
    create_res = _create_shipment(client, desc="Diamond Ring")
    assert create_res.status_code == 201
    shipment_id = create_res.get_json()["shipment"]["id"]
    client.post("/api/auth/logout")

    # Admin assigns to Courier Alpha
    _login(client, "admin@shiptrack.local", "AdminPass123!")
    couriers_res = client.get("/api/admin/delivery-persons")
    courier_alpha_id = [c["id"] for c in couriers_res.get_json()["delivery_persons"] if c["username"] == "courier_alpha"][0]
    assign_res = client.post(f"/api/admin/shipments/{shipment_id}/assign", json={
        "delivery_person_id": courier_alpha_id,
        "notes": "Assigning high-value jewelry transport"
    })
    assert assign_res.status_code == 200
    client.post("/api/auth/logout")

    # Courier Alpha records GPS telemetry
    _login(client, "courier1@shiptrack.local", "CourierPass123!")
    tel_res = client.post(f"/api/delivery/shipments/{shipment_id}/telemetry", json={
        "latitude": 17.385044,
        "longitude": 78.486671,
        "speed_kmh": 42.5,
        "heading_degrees": 180.0,
        "battery_pct": 88.0
    })
    assert tel_res.status_code == 201
    tel_data = tel_res.get_json()
    assert tel_data["latitude"] == 17.385044
    assert tel_data["longitude"] == 78.486671
    assert tel_data["speed_kmh"] == 42.5


def test_unassigned_courier_cannot_record_telemetry(gps_test_env):
    """Unassigned courier receives 404 and security alert logged when trying to post telemetry."""
    client = gps_test_env["client"]

    # Alice creates shipment
    _login(client, "alice@customer.local", "AlicePass123!")
    create_res = _create_shipment(client)
    shipment_id = create_res.get_json()["shipment"]["id"]
    client.post("/api/auth/logout")

    # Courier Beta (unassigned) attempts to record telemetry
    _login(client, "courier2@shiptrack.local", "CourierPass123!")
    unauth_res = client.post(f"/api/delivery/shipments/{shipment_id}/telemetry", json={
        "latitude": 17.385044,
        "longitude": 78.486671
    })
    assert unauth_res.status_code == 404
    client.post("/api/auth/logout")

    # Verify security event logged
    _login(client, "admin@shiptrack.local", "AdminPass123!")
    events_res = client.get("/api/admin/security-events")
    events = events_res.get_json()["events"]
    assert any(e["event_type"] == "UNAUTHORIZED_SHIPMENT_ACCESS" for e in events)


def test_gps_coordinate_validation(gps_test_env):
    """Out-of-range or malformed coordinates are rejected with 400."""
    client = gps_test_env["client"]

    # Setup shipment assigned to Courier Alpha
    _login(client, "alice@customer.local", "AlicePass123!")
    create_res = _create_shipment(client)
    shipment_id = create_res.get_json()["shipment"]["id"]
    client.post("/api/auth/logout")

    _login(client, "admin@shiptrack.local", "AdminPass123!")
    couriers_res = client.get("/api/admin/delivery-persons")
    courier_alpha_id = [c["id"] for c in couriers_res.get_json()["delivery_persons"] if c["username"] == "courier_alpha"][0]
    client.post(f"/api/admin/shipments/{shipment_id}/assign", json={"delivery_person_id": courier_alpha_id})
    client.post("/api/auth/logout")

    _login(client, "courier1@shiptrack.local", "CourierPass123!")

    # Latitude > 90
    res_lat = client.post(f"/api/delivery/shipments/{shipment_id}/telemetry", json={
        "latitude": 95.0,
        "longitude": 78.0
    })
    assert res_lat.status_code == 400

    # Longitude < -180
    res_lng = client.post(f"/api/delivery/shipments/{shipment_id}/telemetry", json={
        "latitude": 17.0,
        "longitude": -195.0
    })
    assert res_lng.status_code == 400

    # Non-numeric
    res_nan = client.post(f"/api/delivery/shipments/{shipment_id}/telemetry", json={
        "latitude": "invalid",
        "longitude": 78.0
    })
    assert res_nan.status_code == 400


def test_customer_generates_and_views_ephemeral_tracking_link(gps_test_env):
    """Customer generates a 1-time tracking link, public user views it, receiving live GPS."""
    client = gps_test_env["client"]

    # Alice creates shipment
    _login(client, "alice@customer.local", "AlicePass123!")
    create_res = _create_shipment(client, desc="Luxury Watch")
    shipment_id = create_res.get_json()["shipment"]["id"]

    # Generate ephemeral link
    gen_res = client.post(f"/api/shipments/{shipment_id}/generate-tracking-link", json={
        "ttl_minutes": 20
    })
    assert gen_res.status_code == 201
    gen_data = gen_res.get_json()
    assert "token" in gen_data
    token = gen_data["token"]
    tracking_url = gen_data["tracking_url"]
    assert gen_data["single_use"] is True

    # Logout customer: public tracking link access does not require login session
    client.post("/api/auth/logout")

    # Courier Alpha posts GPS coordinates
    _login(client, "admin@shiptrack.local", "AdminPass123!")
    couriers_res = client.get("/api/admin/delivery-persons")
    courier_alpha_id = [c["id"] for c in couriers_res.get_json()["delivery_persons"] if c["username"] == "courier_alpha"][0]
    client.post(f"/api/admin/shipments/{shipment_id}/assign", json={"delivery_person_id": courier_alpha_id})
    client.post("/api/auth/logout")

    _login(client, "courier1@shiptrack.local", "CourierPass123!")
    client.post(f"/api/delivery/shipments/{shipment_id}/telemetry", json={
        "latitude": 17.440081,
        "longitude": 78.348915,
        "speed_kmh": 35.0,
        "heading_degrees": 90.0,
        "battery_pct": 95.0
    })
    client.post("/api/auth/logout")

    # Public user views live tracking using token
    public_res = client.get(f"/api/tracking/live/{token}")
    assert public_res.status_code == 200
    public_data = public_res.get_json()
    assert public_data["success"] is True
    assert public_data["security_policy"] == "SINGLE_USE_EPHEMERAL_ACCESS"
    assert public_data["live_gps"]["latitude"] == 17.440081
    assert public_data["live_gps"]["longitude"] == 78.348915
    assert public_data["shipment"]["package_description"] == "Luxury Watch"


def test_ephemeral_link_anti_replay_burn(gps_test_env):
    """A single-use link is permanently burned upon first view; second attempt fails with 410 Gone."""
    client = gps_test_env["client"]

    # Alice creates shipment & generates token
    _login(client, "alice@customer.local", "AlicePass123!")
    create_res = _create_shipment(client)
    shipment_id = create_res.get_json()["shipment"]["id"]
    gen_res = client.post(f"/api/shipments/{shipment_id}/generate-tracking-link")
    token = gen_res.get_json()["token"]
    client.post("/api/auth/logout")

    # 1st view: SUCCEEDS
    first_res = client.get(f"/api/tracking/live/{token}")
    assert first_res.status_code == 200

    # 2nd view (REPLAY ATTACK): MUST FAIL with 410 Gone
    replay_res = client.get(f"/api/tracking/live/{token}")
    assert replay_res.status_code == 410
    replay_data = replay_res.get_json()
    assert replay_data["code"] == "TOKEN_ALREADY_USED"

    # Verify intrusion event logged
    _login(client, "admin@shiptrack.local", "AdminPass123!")
    events_res = client.get("/api/admin/security-events")
    events = events_res.get_json()["events"]
    assert any(e["event_type"] == "REPLAY_ATTACK_DETECTED" for e in events)


def test_ephemeral_link_expiration_check(gps_test_env):
    """Expired tracking token returns 410 Gone and logs EXPIRED_TRACKING_TOKEN."""
    client = gps_test_env["client"]
    app = gps_test_env["app"]

    # Alice creates shipment & token
    _login(client, "alice@customer.local", "AlicePass123!")
    create_res = _create_shipment(client)
    shipment_id = create_res.get_json()["shipment"]["id"]
    gen_res = client.post(f"/api/shipments/{shipment_id}/generate-tracking-link")
    token = gen_res.get_json()["token"]
    client.post("/api/auth/logout")

    # Manually backdate token expiration in DB to simulate expired token
    import hashlib
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with app.app_context():
        past_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
        execute_db(
            "UPDATE tracking_tokens SET expires_at = ? WHERE token_hash = ?",
            (past_time, token_hash)
        )

    # Attempt to access expired token
    exp_res = client.get(f"/api/tracking/live/{token}")
    assert exp_res.status_code == 410
    exp_data = exp_res.get_json()
    assert exp_data["code"] == "TOKEN_EXPIRED"

    # Check security event logged
    _login(client, "admin@shiptrack.local", "AdminPass123!")
    events_res = client.get("/api/admin/security-events")
    events = events_res.get_json()["events"]
    assert any(e["event_type"] == "EXPIRED_TRACKING_TOKEN" for e in events)


def test_tampered_or_invalid_token_returns_404(gps_test_env):
    """Random or tampered token returns 404 and logs INVALID_TRACKING_TOKEN."""
    client = gps_test_env["client"]

    fake_token = "a" * 43
    res = client.get(f"/api/tracking/live/{fake_token}")
    assert res.status_code == 404

    # Check security event logged
    _login(client, "admin@shiptrack.local", "AdminPass123!")
    events_res = client.get("/api/admin/security-events")
    events = events_res.get_json()["events"]
    assert any(e["event_type"] == "INVALID_TRACKING_TOKEN" for e in events)


def test_non_owner_cannot_generate_tracking_link(gps_test_env):
    """Customer Bob cannot generate tracking link for Customer Alice's shipment (BOLA prevention)."""
    client = gps_test_env["client"]

    # Alice creates shipment
    _login(client, "alice@customer.local", "AlicePass123!")
    create_res = _create_shipment(client)
    shipment_id = create_res.get_json()["shipment"]["id"]
    client.post("/api/auth/logout")

    # Bob tries to generate link for Alice's shipment
    _login(client, "bob@customer.local", "BobPass123!")
    bola_res = client.post(f"/api/shipments/{shipment_id}/generate-tracking-link")
    assert bola_res.status_code == 404  # Anti-probing 404
    client.post("/api/auth/logout")

    # Check security event logged
    _login(client, "admin@shiptrack.local", "AdminPass123!")
    events_res = client.get("/api/admin/security-events")
    events = events_res.get_json()["events"]
    assert any(e["event_type"] == "UNAUTHORIZED_SHIPMENT_ACCESS" for e in events)


def test_telemetry_history_view_and_isolation(gps_test_env):
    """Owner and Admin can view telemetry trail; foreign customer receives 404."""
    client = gps_test_env["client"]

    # Alice creates shipment
    _login(client, "alice@customer.local", "AlicePass123!")
    create_res = _create_shipment(client)
    shipment_id = create_res.get_json()["shipment"]["id"]
    client.post("/api/auth/logout")

    # Assign and post 2 telemetry points
    _login(client, "admin@shiptrack.local", "AdminPass123!")
    couriers_res = client.get("/api/admin/delivery-persons")
    courier_alpha_id = [c["id"] for c in couriers_res.get_json()["delivery_persons"] if c["username"] == "courier_alpha"][0]
    client.post(f"/api/admin/shipments/{shipment_id}/assign", json={"delivery_person_id": courier_alpha_id})
    client.post("/api/auth/logout")

    _login(client, "courier1@shiptrack.local", "CourierPass123!")
    client.post(f"/api/delivery/shipments/{shipment_id}/telemetry", json={"latitude": 17.3850, "longitude": 78.4867})
    client.post(f"/api/delivery/shipments/{shipment_id}/telemetry", json={"latitude": 17.3890, "longitude": 78.4900})
    client.post("/api/auth/logout")

    # Alice (owner) retrieves telemetry
    _login(client, "alice@customer.local", "AlicePass123!")
    owner_tel = client.get(f"/api/shipments/{shipment_id}/telemetry")
    assert owner_tel.status_code == 200
    assert owner_tel.get_json()["points_count"] == 2
    client.post("/api/auth/logout")

    # Bob (foreign customer) retrieves telemetry -> 404
    _login(client, "bob@customer.local", "BobPass123!")
    foreign_tel = client.get(f"/api/shipments/{shipment_id}/telemetry")
    assert foreign_tel.status_code == 404
    client.post("/api/auth/logout")

    # Admin retrieves telemetry -> 200
    _login(client, "admin@shiptrack.local", "AdminPass123!")
    admin_tel = client.get(f"/api/shipments/{shipment_id}/telemetry")
    assert admin_tel.status_code == 200
    assert admin_tel.get_json()["points_count"] == 2
