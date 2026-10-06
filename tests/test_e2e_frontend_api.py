"""End-to-End Integration Tests for Production Front-to-Back Flow (PS-05).

Verifies the exact requirements:
1. Register customer account -> Login -> GET /api/auth/me returns customer role.
2. Create shipment -> My shipments -> Track -> Generate 1-time token -> Public view burn -> Verify chain -> Cancel.
3. Delivery courier login -> View assigned -> Advance milestone status.
4. Admin login -> Dashboard -> List users -> Assign courier -> Security events audit.
5. Deployment & Assets: GET / serves real index.html, static css/js return 200, mockData.js is 404 deleted.
"""

import os
import tempfile
import pytest
from src.backend.app import create_app
from src.backend.db import init_db, execute_db
from werkzeug.security import generate_password_hash


@pytest.fixture
def e2e_env():
    """Create isolated test environment."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app = create_app({"TESTING": True, "DATABASE": db_path})

    with app.app_context():
        init_db(app)

        # Seed Admin
        admin_hash = generate_password_hash("AdminPass123!")
        execute_db(
            """INSERT INTO users (username, email, password_hash, role, full_name)
               VALUES ('head_admin', 'admin@shiptrack.local', ?, 'admin', 'Head Admin')""",
            (admin_hash,)
        )

        # Seed Courier
        courier_hash = generate_password_hash("CourierPass123!")
        execute_db(
            """INSERT INTO users (username, email, password_hash, role, full_name, phone)
               VALUES ('courier_bob', 'bob@shiptrack.local', ?, 'delivery_person', 'Courier Bob', '+91 9888800001')""",
            (courier_hash,)
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


def test_e2e_register_login_create_shipment(e2e_env):
    """Test full customer lifecycle: register, login, me, create shipment, history, track, verify, token, cancel."""
    client = e2e_env["client"]

    # 1. Unauthenticated /api/auth/me returns 401
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 401

    # 2. Register customer account
    reg_res = client.post("/api/auth/register", json={
        "username": "customer_alice",
        "email": "alice@customer.local",
        "password": "AliceSecurePass123!",
        "full_name": "Alice Vance",
        "phone": "+91 9777700001"
    })
    assert reg_res.status_code == 201
    reg_data = reg_res.get_json()
    assert reg_data["user"]["role"] == "customer"

    # 3. Login
    login_res = client.post("/api/auth/login", json={
        "identifier": "alice@customer.local",
        "password": "AliceSecurePass123!"
    })
    assert login_res.status_code == 200

    # 4. GET /api/auth/me returns customer role
    auth_me = client.get("/api/auth/me")
    assert auth_me.status_code == 200
    assert auth_me.get_json()["user"]["role"] == "customer"
    assert auth_me.get_json()["user"]["username"] == "customer_alice"

    # 5. Create shipment
    create_res = client.post("/api/shipments", json={
        "sender_name": "Alice Vance",
        "sender_address": "100 Safe Deposit Way, HITEC City",
        "recipient_name": "Charlie Jenkins",
        "recipient_address": "Flat 402, Cyber Tower Heights, Madhapur",
        "recipient_phone": "+91 9123456789",
        "package_description": "High-Value Titanium Swiss Watch",
        "weight_kg": 1.2
    })
    assert create_res.status_code == 201
    shipment = create_res.get_json()["shipment"]
    shipment_id = shipment["id"]
    tracking_number = shipment["tracking_number"]
    assert tracking_number.startswith("ST-")
    assert shipment["current_status"] == "Order Placed"

    # 6. Customer History (GET /api/shipments)
    history_res = client.get("/api/shipments")
    assert history_res.status_code == 200
    history = history_res.get_json()["shipments"]
    assert len(history) == 1
    assert history[0]["tracking_number"] == tracking_number

    # 7. Track Shipment (GET /api/shipments/<tracking_number>)
    track_res = client.get(f"/api/shipments/{tracking_number}")
    assert track_res.status_code == 200
    track_data = track_res.get_json()
    assert track_data["shipment"]["tracking_number"] == tracking_number
    assert len(track_data["timeline"]) >= 1

    # 8. Verify Cryptographic Custody Chain (GET /api/shipments/<id>/verify)
    verify_res = client.get(f"/api/shipments/{shipment_id}/verify")
    assert verify_res.status_code == 200
    assert verify_res.get_json()["valid"] is True

    # 9. Generate 1-Time Secure Tracking Link (POST /api/shipments/<id>/generate-tracking-link)
    gen_res = client.post(f"/api/shipments/{shipment_id}/generate-tracking-link", json={"ttl_minutes": 15})
    assert gen_res.status_code == 201
    token = gen_res.get_json()["token"]

    # 10. Public Access: burns token on first view
    pub_res1 = client.get(f"/api/tracking/live/{token}")
    assert pub_res1.status_code == 200
    # Replay attempt fails with 410 Gone
    pub_res2 = client.get(f"/api/tracking/live/{token}")
    assert pub_res2.status_code == 410

    # 11. Cancel shipment while in 'Order Placed'
    cancel_res = client.post(f"/api/shipments/{shipment_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.get_json()["current_status"] == "Cancelled"

    # Logout
    client.post("/api/auth/logout")


def test_e2e_delivery_and_admin_flows(e2e_env):
    """Test delivery partner and admin workflows connected to backend endpoints."""
    client = e2e_env["client"]

    # Customer creates shipment
    client.post("/api/auth/register", json={
        "username": "customer_cathy",
        "email": "cathy@customer.local",
        "password": "CathySecurePass123!",
        "full_name": "Cathy Vance",
        "phone": "+91 9777700002"
    })
    client.post("/api/auth/login", json={"identifier": "cathy@customer.local", "password": "CathySecurePass123!"})
    create_res = client.post("/api/shipments", json={
        "sender_name": "Cathy Vance",
        "sender_address": "500 High Street, Secunderabad",
        "recipient_name": "David Miller",
        "recipient_address": "800 Lake View, Begumpet",
        "recipient_phone": "+91 9876543210",
        "package_description": "Hardware Kit",
        "weight_kg": 2.5
    })
    shipment_id = create_res.get_json()["shipment"]["id"]
    client.post("/api/auth/logout")

    # Admin login & assignment
    client.post("/api/auth/login", json={"identifier": "head_admin", "password": "AdminPass123!"})
    admin_dash = client.get("/api/admin/dashboard")
    assert admin_dash.status_code == 200

    admin_couriers = client.get("/api/admin/delivery-persons")
    assert admin_couriers.status_code == 200
    courier_id = admin_couriers.get_json()["delivery_persons"][0]["id"]

    assign_res = client.post(f"/api/admin/shipments/{shipment_id}/assign", json={
        "delivery_person_id": courier_id,
        "notes": "Assigned to Courier Bob"
    })
    assert assign_res.status_code == 200

    admin_users = client.get("/api/admin/users")
    assert admin_users.status_code == 200

    admin_sec = client.get("/api/admin/security-events")
    assert admin_sec.status_code == 200
    client.post("/api/auth/logout")

    # Courier Bob login & update status
    client.post("/api/auth/login", json={"identifier": "bob@shiptrack.local", "password": "CourierPass123!"})
    deliv_dash = client.get("/api/delivery/dashboard")
    assert deliv_dash.status_code == 200
    assert len(deliv_dash.get_json()["active_shipments"]) >= 1

    status_res = client.post(f"/api/delivery/shipments/{shipment_id}/status", json={
        "status": "Picked Up",
        "location": "Secunderabad Depot",
        "notes": "Cargo inspected and loaded"
    })
    assert status_res.status_code == 200
    assert status_res.get_json()["new_status"] == "Picked Up"
    client.post("/api/auth/logout")


def test_frontend_assets_and_no_mock_data(e2e_env):
    """Verify frontend assets are served correctly and mockData.js is removed."""
    client = e2e_env["client"]

    # Root route serves index.html
    r_index = client.get("/")
    assert r_index.status_code == 200
    assert b"ShipTrack" in r_index.data

    # Static CSS and JS return 200
    r_css = client.get("/css/styles.css")
    assert r_css.status_code == 200

    r_app = client.get("/js/app.js")
    assert r_app.status_code == 200
    assert b"mockData" not in r_app.data

    # mockData.js must be 404 (deleted)
    r_mock = client.get("/js/mockData.js")
    assert r_mock.status_code == 404
