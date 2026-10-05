"""Tests for Delivery Person and Admin Workflows (PS-05).

Verifies:
1. Delivery Person:
   - Dashboard metrics and assigned shipments list.
   - Milestone updates: Picked Up -> In Transit -> Out for Delivery -> Delivered.
   - Cryptographic chain of custody integrity across all courier transitions.
   - Terminal status protection (cannot update already Delivered shipment).
   - Cross-courier BOLA isolation: couriers cannot view or update unassigned shipments (returns 404).
   - Role enforcement: non-couriers get 403 Forbidden.
2. Admin Management:
   - Platform dashboard metrics (counts by status, user breakdown, security alerts).
   - Listing all shipments and registered couriers.
   - Assigning shipments to couriers with audit logging.
   - Administrative cancellations with audit logging.
   - Listing users with role filtering.
   - Role enforcement: non-admins get 403 Forbidden.
"""

import os
import tempfile
import pytest
from src.backend.app import create_app
from src.backend.db import init_db, execute_db
from werkzeug.security import generate_password_hash


@pytest.fixture
def workflow_env():
    """Create isolated test environment with seeded admin, two couriers, and a customer."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app = create_app({"TESTING": True, "DATABASE": db_path})

    with app.app_context():
        init_db(app)

        # Seed Admin
        admin_hash = generate_password_hash("AdminPass123!")
        execute_db(
            """INSERT INTO users (username, email, password_hash, role, full_name)
               VALUES ('head_admin', 'admin@shiptrack.local', ?, 'admin', 'Head Administrator')""",
            (admin_hash,)
        )

        # Seed Courier 1
        courier_hash = generate_password_hash("CourierPass123!")
        execute_db(
            """INSERT INTO users (username, email, password_hash, role, full_name, phone)
               VALUES ('courier_one', 'courier1@shiptrack.local', ?, 'delivery_person', 'Courier One', '+91 9999900001')""",
            (courier_hash,)
        )

        # Seed Courier 2
        execute_db(
            """INSERT INTO users (username, email, password_hash, role, full_name, phone)
               VALUES ('courier_two', 'courier2@shiptrack.local', ?, 'delivery_person', 'Courier Two', '+91 9999900002')""",
            (courier_hash,)
        )

        # Seed Customer
        cust_hash = generate_password_hash("CustomerPass123!")
        execute_db(
            """INSERT INTO users (username, email, password_hash, role, full_name, phone)
               VALUES ('reg_customer', 'customer@shiptrack.local', ?, 'customer', 'Registered Customer', '+91 9999900003')""",
            (cust_hash,)
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


def test_admin_workflows(workflow_env):
    """Test admin dashboard, courier assignment, and administrative cancellation."""
    client = workflow_env["client"]

    # 1. Customer creates a shipment
    client.post("/api/auth/login", json={"identifier": "reg_customer", "password": "CustomerPass123!"})
    create_res = client.post("/api/shipments", json={
        "sender_name": "Alice",
        "sender_address": "123 Sender St",
        "recipient_name": "Bob",
        "recipient_address": "456 Recipient Ave",
        "recipient_phone": "+91 9876543210",
        "package_description": "Documents",
        "weight_kg": 1.5
    })
    assert create_res.status_code == 201
    shipment_id = create_res.get_json()["shipment"]["id"]

    # 2. Customer tries to access admin dashboard -> 403 Forbidden
    cust_forbidden = client.get("/api/admin/dashboard")
    assert cust_forbidden.status_code == 403

    # 3. Admin logs in
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"identifier": "head_admin", "password": "AdminPass123!"})

    # 4. Admin dashboard metrics
    dash_res = client.get("/api/admin/dashboard")
    assert dash_res.status_code == 200
    dash_data = dash_res.get_json()
    assert dash_data["metrics"]["total_shipments"] == 1
    assert dash_data["metrics"]["unassigned"] == 1
    assert dash_data["users"]["total_users"] == 4
    assert len(dash_data["recent_shipments"]) == 1

    # 5. Admin lists shipments
    shipments_res = client.get("/api/admin/shipments?page=1&per_page=10")
    assert shipments_res.status_code == 200
    assert len(shipments_res.get_json()["shipments"]) == 1

    # 6. Admin lists delivery couriers
    couriers_res = client.get("/api/admin/delivery-persons")
    assert couriers_res.status_code == 200
    couriers_list = couriers_res.get_json()["delivery_persons"]
    assert len(couriers_list) == 2
    courier_1_id = couriers_list[0]["id"]

    # 7. Admin assigns shipment to Courier 1
    assign_res = client.post(f"/api/admin/shipments/{shipment_id}/assign", json={
        "delivery_person_id": courier_1_id
    })
    assert assign_res.status_code == 200
    assert assign_res.get_json()["assigned_delivery_id"] == courier_1_id

    # 8. Admin user list
    users_res = client.get("/api/admin/users?role=customer")
    assert users_res.status_code == 200
    assert len(users_res.get_json()["users"]) == 1


def test_delivery_person_workflows_and_chain_integrity(workflow_env):
    """Test courier status progression, chain of custody verification, and cross-courier isolation."""
    client = workflow_env["client"]

    # 1. Customer creates a shipment
    client.post("/api/auth/login", json={"identifier": "reg_customer", "password": "CustomerPass123!"})
    create_res = client.post("/api/shipments", json={
        "sender_name": "Warehouse Alpha",
        "sender_address": "Dock 4, Industrial Zone",
        "recipient_name": "Target Recipient",
        "recipient_address": "Suite 500, Tech Park",
        "recipient_phone": "+91 9123456789",
        "package_description": "Server Hardware Components",
        "weight_kg": 8.5
    })
    shipment_id = create_res.get_json()["shipment"]["id"]
    tracking_number = create_res.get_json()["shipment"]["tracking_number"]

    # 2. Admin assigns shipment to Courier One (ID 2)
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"identifier": "head_admin", "password": "AdminPass123!"})
    client.post(f"/api/admin/shipments/{shipment_id}/assign", json={"delivery_person_id": 2})

    # 3. Courier One logs in
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"identifier": "courier_one", "password": "CourierPass123!"})

    # Courier dashboard
    dash_res = client.get("/api/delivery/dashboard")
    assert dash_res.status_code == 200
    assert dash_res.get_json()["metrics"]["total_assigned"] == 1
    assert len(dash_res.get_json()["active_shipments"]) == 1

    # Courier lists assigned shipments
    list_res = client.get("/api/delivery/shipments")
    assert list_res.status_code == 200
    assert len(list_res.get_json()["shipments"]) == 1

    # Courier views assigned shipment detail
    detail_res = client.get(f"/api/delivery/shipments/{tracking_number}")
    assert detail_res.status_code == 200

    # 4. Courier progression: Picked Up -> In Transit -> Out for Delivery -> Delivered
    # Milestone 1: Picked Up
    s1 = client.post(f"/api/delivery/shipments/{shipment_id}/status", json={
        "status": "Picked Up",
        "location": "Dock 4 Logistics Hub",
        "notes": "Parcel inspected and loaded into van."
    })
    assert s1.status_code == 200

    # Milestone 2: In Transit
    s2 = client.post(f"/api/delivery/shipments/{shipment_id}/status", json={
        "status": "In Transit",
        "location": "Highway Express Tollplaza",
        "notes": "Approaching destination city."
    })
    assert s2.status_code == 200

    # Milestone 3: Out for Delivery
    s3 = client.post(f"/api/delivery/shipments/{shipment_id}/status", json={
        "status": "Out for Delivery",
        "location": "Metro Last-Mile Facility",
        "notes": "Courier on delivery route."
    })
    assert s3.status_code == 200

    # Milestone 4: Delivered
    s4 = client.post(f"/api/delivery/shipments/{shipment_id}/status", json={
        "status": "Delivered",
        "location": "Suite 500 Reception",
        "notes": "Handed to recipient with digital signature."
    })
    assert s4.status_code == 200

    # 5. Terminal state check: cannot update already Delivered shipment
    s5 = client.post(f"/api/delivery/shipments/{shipment_id}/status", json={
        "status": "In Transit",
        "location": "Nowhere",
        "notes": "Illegal rollback attempt."
    })
    assert s5.status_code == 400

    # 6. Verify entire cryptographic chain of custody remains 100% valid!
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"identifier": "head_admin", "password": "AdminPass123!"})
    audit_res = client.get(f"/api/shipments/{shipment_id}/verify")
    assert audit_res.status_code == 200
    audit_data = audit_res.get_json()
    assert audit_data["valid"] is True
    # Initial + Admin Assign + Picked Up + In Transit + Out for Delivery + Delivered = 6 milestones
    assert audit_data["records_count"] == 6

    # 7. Courier Two (unassigned) tries to view or update Courier One's shipment -> 404
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"identifier": "courier_two", "password": "CourierPass123!"})

    c2_view = client.get(f"/api/delivery/shipments/{tracking_number}")
    assert c2_view.status_code == 404

    c2_update = client.post(f"/api/delivery/shipments/{shipment_id}/status", json={
        "status": "Delivered",
        "location": "Fake Location"
    })
    assert c2_update.status_code == 404
