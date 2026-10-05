"""Unit and Security Tests for Customer Shipment Workflows (PS-05).

Verifies:
- Creation of shipment with generated tracking number and initial status audit log.
- Customer shipment history listing (strictly isolated to owner).
- Detail and timeline retrieval.
- Anti-probing defense: Returns 404 (not 403) when another customer tries to view or cancel a shipment.
- Cancellation allowed only for owner and only in 'Order Placed' status.
- Admin and assigned delivery person authorized view.
"""

import os
import tempfile
import pytest
from src.backend.app import create_app
from src.backend.db import init_db, query_db, execute_db
from werkzeug.security import generate_password_hash


@pytest.fixture
def test_setup():
    """Create a temporary database and test client."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app = create_app({"TESTING": True, "DATABASE": db_path})

    with app.app_context():
        init_db(app)

        # Seed an admin and two couriers
        admin_hash = generate_password_hash("AdminPass123!")
        execute_db(
            """INSERT INTO users (username, email, password_hash, role, full_name)
               VALUES ('test_admin', 'admin@test.local', ?, 'admin', 'Admin User')""",
            (admin_hash,)
        )

        courier_hash = generate_password_hash("CourierPass123!")
        execute_db(
            """INSERT INTO users (username, email, password_hash, role, full_name, phone)
               VALUES ('assigned_courier', 'assigned@test.local', ?, 'delivery_person', 'Assigned Courier', '+919999999991')""",
            (courier_hash,)
        )
        execute_db(
            """INSERT INTO users (username, email, password_hash, role, full_name, phone)
               VALUES ('other_courier', 'other@test.local', ?, 'delivery_person', 'Other Courier', '+919999999992')""",
            (courier_hash,)
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


def test_shipment_creation_and_isolation(test_setup):
    """Test shipment creation, tracking generation, and object isolation."""
    client = test_setup["client"]

    # 1. Register Customer A
    client.post("/api/auth/register", json={
        "username": "customer_a",
        "email": "customer_a@example.com",
        "password": "Password123!",
        "full_name": "Customer Alice"
    })
    client.post("/api/auth/login", json={"identifier": "customer_a", "password": "Password123!"})

    # 2. Customer A creates a shipment
    create_payload = {
        "sender_name": "Alice Sender",
        "sender_address": "123 Maple Street, City Center",
        "recipient_name": "Bob Recipient",
        "recipient_address": "456 Oak Avenue, Uptown",
        "recipient_phone": "+91 9876543210",
        "package_description": "Electronics: Laptop and accessories",
        "weight_kg": 2.5,
        "customer_id": 9999,      # Attacker attempt to forge customer_id
        "current_status": "Delivered" # Attacker attempt to forge initial status
    }
    res = client.post("/api/shipments", json=create_payload)
    assert res.status_code == 201
    data = res.get_json()["shipment"]

    tracking_num = data["tracking_number"]
    shipment_id = data["id"]
    assert tracking_num.startswith("ST-")
    assert data["current_status"] == "Order Placed"  # Client status override was blocked!

    # 3. Customer A lists shipments
    list_res = client.post("/api/auth/login", json={"identifier": "customer_a", "password": "Password123!"})
    history_res = client.get("/api/shipments")
    assert history_res.status_code == 200
    shipments_list = history_res.get_json()["shipments"]
    assert len(shipments_list) == 1
    assert shipments_list[0]["id"] == shipment_id

    # 4. Customer A views their own shipment
    detail_res = client.get(f"/api/shipments/{tracking_num}")
    assert detail_res.status_code == 200
    detail_data = detail_res.get_json()
    assert detail_data["shipment"]["tracking_number"] == tracking_num
    assert len(detail_data["timeline"]) == 1
    assert detail_data["timeline"][0]["status"] == "Order Placed"

    # 5. Customer B registers
    client.post("/api/auth/logout")
    client.post("/api/auth/register", json={
        "username": "customer_b",
        "email": "customer_b@example.com",
        "password": "Password123!",
        "full_name": "Customer Bob"
    })
    client.post("/api/auth/login", json={"identifier": "customer_b", "password": "Password123!"})

    # 6. Customer B's list should be empty
    b_history = client.get("/api/shipments")
    assert b_history.status_code == 200
    assert len(b_history.get_json()["shipments"]) == 0

    # 7. SECURITY: Customer B attempts to read Customer A's shipment -> MUST RETURN 404 (not 403)
    b_read_attempt = client.get(f"/api/shipments/{tracking_num}")
    assert b_read_attempt.status_code == 404, f"Expected 404, got {b_read_attempt.status_code}"
    assert b_read_attempt.get_json()["error"] == "Shipment not found."

    # 8. SECURITY: Customer B attempts to cancel Customer A's shipment -> MUST RETURN 404
    b_cancel_attempt = client.post(f"/api/shipments/{shipment_id}/cancel")
    assert b_cancel_attempt.status_code == 404, f"Expected 404, got {b_cancel_attempt.status_code}"
    assert b_cancel_attempt.get_json()["error"] == "Shipment not found."

    # 9. Customer A cancels their own shipment
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"identifier": "customer_a", "password": "Password123!"})

    cancel_res = client.post(f"/api/shipments/{shipment_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.get_json()["current_status"] == "Cancelled"

    # Verify timeline updated
    detail_after_cancel = client.get(f"/api/shipments/{tracking_num}")
    assert detail_after_cancel.status_code == 200
    assert len(detail_after_cancel.get_json()["timeline"]) == 2
    assert detail_after_cancel.get_json()["timeline"][1]["status"] == "Cancelled"

    # 10. Customer A tries to cancel already cancelled shipment -> 400
    second_cancel = client.post(f"/api/shipments/{shipment_id}/cancel")
    assert second_cancel.status_code == 400

    # 11. Admin views shipment
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"identifier": "test_admin", "password": "AdminPass123!"})
    admin_view = client.get(f"/api/shipments/{tracking_num}")
    assert admin_view.status_code == 200


def test_shipment_assigned_delivery_view(test_setup):
    """Test assigned delivery person access vs unassigned delivery person access."""
    client = test_setup["client"]

    # Register customer and create shipment
    client.post("/api/auth/register", json={
        "username": "customer_c",
        "email": "customer_c@example.com",
        "password": "Password123!",
        "full_name": "Customer Charlie"
    })
    client.post("/api/auth/login", json={"identifier": "customer_c", "password": "Password123!"})
    res = client.post("/api/shipments", json={
        "sender_name": "Charlie Sender",
        "sender_address": "789 Pine Road, Suburb",
        "recipient_name": "David Recipient",
        "recipient_address": "101 Elm Boulevard, Metro",
        "recipient_phone": "+91 9123456789",
        "package_description": "Documents",
        "weight_kg": 0.5
    })
    shipment_id = res.get_json()["shipment"]["id"]
    tracking_num = res.get_json()["shipment"]["tracking_number"]

    # Assign shipment to 'assigned_courier' (ID 2) directly in DB
    with test_setup["app"].app_context():
        execute_db("UPDATE shipments SET assigned_delivery_id = 2 WHERE id = ?", (shipment_id,))

    # Assigned courier logs in and views shipment
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"identifier": "assigned_courier", "password": "CourierPass123!"})
    assigned_view = client.get(f"/api/shipments/{tracking_num}")
    assert assigned_view.status_code == 200

    # Other unassigned courier logs in and views shipment -> MUST RETURN 404
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"identifier": "other_courier", "password": "CourierPass123!"})
    unassigned_view = client.get(f"/api/shipments/{tracking_num}")
    assert unassigned_view.status_code == 404


def test_shipment_input_validation(test_setup):
    """Test validation boundaries and invalid inputs."""
    client = test_setup["client"]
    client.post("/api/auth/register", json={
        "username": "customer_val",
        "email": "val@example.com",
        "password": "Password123!",
        "full_name": "Validator User"
    })
    client.post("/api/auth/login", json={"identifier": "customer_val", "password": "Password123!"})

    # Invalid weight
    res = client.post("/api/shipments", json={
        "sender_name": "Valid Sender",
        "sender_address": "Valid Address 123",
        "recipient_name": "Valid Recipient",
        "recipient_address": "Valid Address 456",
        "recipient_phone": "+91 9999999999",
        "package_description": "Valid Item",
        "weight_kg": -5.0
    })
    assert res.status_code == 400

    # Invalid phone
    res_phone = client.post("/api/shipments", json={
        "sender_name": "Valid Sender",
        "sender_address": "Valid Address 123",
        "recipient_name": "Valid Recipient",
        "recipient_address": "Valid Address 456",
        "recipient_phone": "abc",
        "package_description": "Valid Item",
        "weight_kg": 1.0
    })
    assert res_phone.status_code == 400

    # Short address
    res_addr = client.post("/api/shipments", json={
        "sender_name": "Valid Sender",
        "sender_address": "ab",
        "recipient_name": "Valid Recipient",
        "recipient_address": "Valid Address 456",
        "recipient_phone": "+91 9999999999",
        "package_description": "Valid Item",
        "weight_kg": 1.0
    })
    assert res_addr.status_code == 400
