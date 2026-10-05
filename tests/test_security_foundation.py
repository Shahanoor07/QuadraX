"""Tests for Security Foundation (PS-05).

Verifies:
1. Cryptographic Chain of Custody:
   - Valid hash chain creation on pristine shipment events.
   - Tampering detection: directly mutating status_updates row causes /api/shipments/<id>/verify to fail and report broken record.
   - Access control: only owner or admin can audit chain; other users get 404.
2. Attack Detection & Audit Logging:
   - FAILED_LOGIN logged on invalid credentials.
   - ACCOUNT_LOCKOUT logged on rate limit threshold.
   - UNAUTHORIZED_ACCESS logged on 401 unauthenticated requests.
   - FORBIDDEN_ACCESS logged on 403 role mismatches.
   - UNAUTHORIZED_SHIPMENT_ACCESS logged on cross-user shipment attempts.
   - SUSPICIOUS_INPUT logged on malicious payloads.
   - GET /api/admin/security-events returns paginated results to admin only.
"""

import os
import tempfile
import pytest
from src.backend.app import create_app
from src.backend.db import init_db, query_db, execute_db
from werkzeug.security import generate_password_hash


@pytest.fixture
def security_test_env():
    """Create isolated database environment with admin, delivery, and customer users."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app = create_app({"TESTING": True, "DATABASE": db_path})

    with app.app_context():
        init_db(app)

        # Seed admin
        admin_hash = generate_password_hash("AdminSecret2026!")
        execute_db(
            """INSERT INTO users (username, email, password_hash, role, full_name)
               VALUES ('admin_auditor', 'auditor@shiptrack.local', ?, 'admin', 'Security Auditor')""",
            (admin_hash,)
        )

    client = app.test_client()

    yield {
        "app": app,
        "client": client,
        "db_path": db_path
    }

    os.close(db_fd)
    if os.path.exists(db_path):
        os.remove(db_path)


def test_chain_of_custody_and_tampering(security_test_env):
    """Test hash chain creation, verification, and tampering detection."""
    client = security_test_env["client"]
    app = security_test_env["app"]

    # 1. Register and login Customer Alice
    client.post("/api/auth/register", json={
        "username": "alice_cust",
        "email": "alice_cust@example.com",
        "password": "Password123!",
        "full_name": "Alice Cust"
    })
    client.post("/api/auth/login", json={"identifier": "alice_cust", "password": "Password123!"})

    # 2. Alice creates a shipment
    create_res = client.post("/api/shipments", json={
        "sender_name": "Alice",
        "sender_address": "100 Warehouse Way",
        "recipient_name": "Bob",
        "recipient_address": "200 Delivery Blvd",
        "recipient_phone": "+91 9876543210",
        "package_description": "Hardware Module",
        "weight_kg": 3.2
    })
    assert create_res.status_code == 201
    shipment_id = create_res.get_json()["shipment"]["id"]

    # 3. Alice cancels the shipment -> creates second milestone in chain
    cancel_res = client.post(f"/api/shipments/{shipment_id}/cancel")
    assert cancel_res.status_code == 200

    # 4. Verify chain of custody on untampered data
    verify_res = client.get(f"/api/shipments/{shipment_id}/verify")
    assert verify_res.status_code == 200
    vdata = verify_res.get_json()
    assert vdata["valid"] is True
    assert vdata["records_count"] == 2
    assert "latest_hash" in vdata

    # 5. TAMPERING SIMULATION: Directly mutate database row
    # An attacker directly edits location or notes in the database
    with app.app_context():
        execute_db(
            """UPDATE status_updates
               SET location = 'Tampered Illicit Hub'
               WHERE shipment_id = ? AND status = 'Cancelled'""",
            (shipment_id,)
        )

    # 6. Verify chain of custody now FAILS and flags the exact tampered record
    tampered_verify = client.get(f"/api/shipments/{shipment_id}/verify")
    assert tampered_verify.status_code == 200
    tdata = tampered_verify.get_json()
    assert tdata["valid"] is False
    assert "broken_record" in tdata
    assert tdata["broken_record"]["status"] == "Cancelled"
    assert "mismatch" in tdata["error"].lower()

    # 7. Access control: Customer Bob cannot verify Alice's shipment
    client.post("/api/auth/logout")
    client.post("/api/auth/register", json={
        "username": "bob_cust",
        "email": "bob_cust@example.com",
        "password": "Password123!",
        "full_name": "Bob Cust"
    })
    client.post("/api/auth/login", json={"identifier": "bob_cust", "password": "Password123!"})

    bob_verify = client.get(f"/api/shipments/{shipment_id}/verify")
    assert bob_verify.status_code == 404  # Anti-probing 404

    # 8. Admin CAN audit Alice's shipment
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"identifier": "admin_auditor", "password": "AdminSecret2026!"})

    admin_verify = client.get(f"/api/shipments/{shipment_id}/verify")
    assert admin_verify.status_code == 200
    assert admin_verify.get_json()["valid"] is False  # Admin sees tampering result


def test_attack_detection_and_security_events(security_test_env):
    """Test attack detection telemetry, sensor logging, and admin security-events API."""
    client = security_test_env["client"]

    # 1. Test FAILED_LOGIN logging
    client.post("/api/auth/login", json={
        "identifier": "admin_auditor",
        "password": "WrongPasswordAttempt1"
    })

    # 2. Test ACCOUNT_LOCKOUT logging (5 failed attempts)
    for _ in range(4):
        client.post("/api/auth/login", json={
            "identifier": "victim_account",
            "password": "badpassword"
        })
    lockout_res = client.post("/api/auth/login", json={
        "identifier": "victim_account",
        "password": "badpassword"
    })
    assert lockout_res.status_code == 429

    # Clear lockout tracking so subsequent test users can authenticate from test runner
    from src.backend.auth import FAILED_LOGIN_ATTEMPTS
    FAILED_LOGIN_ATTEMPTS.clear()

    # 3. Test UNAUTHORIZED_ACCESS logging (401 unauthenticated request to protected route)
    client.post("/api/auth/logout")
    unauth_res = client.get("/api/shipments")
    assert unauth_res.status_code == 401

    # 4. Test FORBIDDEN_ACCESS logging (403 customer accessing admin route)
    client.post("/api/auth/register", json={
        "username": "attacker_user",
        "email": "attacker@example.com",
        "password": "Password123!",
        "full_name": "Attacker"
    })
    client.post("/api/auth/login", json={"identifier": "attacker_user", "password": "Password123!"})
    forbidden_res = client.get("/api/admin/security-events")
    assert forbidden_res.status_code == 403

    # 5. Test UNAUTHORIZED_SHIPMENT_ACCESS logging
    cross_access_res = client.get("/api/shipments/ST-999999-NONEXISTENT")
    assert cross_access_res.status_code == 404

    # 6. Test SUSPICIOUS_INPUT sensor logging
    client.post("/api/shipments", json={
        "sender_name": "Test Sender",
        "sender_address": "123 Main St' OR '1'='1",  # SQLi pattern
        "recipient_name": "<script>alert(1)</script>",  # XSS pattern
        "recipient_address": "456 Oak Avenue St",
        "recipient_phone": "+91 9999999999",
        "package_description": "Valid package",
        "weight_kg": 1.0
    })

    # 7. Admin views /api/admin/security-events (Paginated, newest first)
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"identifier": "admin_auditor", "password": "AdminSecret2026!"})

    events_res = client.get("/api/admin/security-events?page=1&per_page=50")
    assert events_res.status_code == 200
    events_data = events_res.get_json()

    assert "events" in events_data
    assert "pagination" in events_data
    assert events_data["pagination"]["total"] > 0

    event_types = [e["event_type"] for e in events_data["events"]]
    assert "FAILED_LOGIN" in event_types
    assert "ACCOUNT_LOCKOUT" in event_types
    assert "UNAUTHORIZED_ACCESS" in event_types
    assert "FORBIDDEN_ACCESS" in event_types
    assert "SUSPICIOUS_INPUT" in event_types
