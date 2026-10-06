"""Test auto-creation of admin and courier accounts at application startup from environment variables."""

import os
import tempfile
import pytest
from src.backend.app import create_app


def test_startup_auto_seed_accounts_from_env(monkeypatch):
    """Verify that when ADMIN_PASSWORD and DELIVERY_PASSWORD env vars are set,
    the app automatically creates both accounts at startup in SQLite without shell commands.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db_path = tf.name

    try:
        # Configure environment variables
        monkeypatch.setenv("ADMIN_PASSWORD", "TestEnvAdminPass2026!")
        monkeypatch.setenv("DELIVERY_PASSWORD", "TestEnvCourierPass2026!")
        monkeypatch.setenv("COURIER2_PASSWORD", "TestEnvCourier2Pass2026!")
        monkeypatch.setenv("ADMIN_USERNAME", "admin")
        monkeypatch.setenv("ADMIN_EMAIL", "admin@shiptrack.local")
        monkeypatch.setenv("DELIVERY_USERNAME", "courier_agent1")
        monkeypatch.setenv("DELIVERY_EMAIL", "courier1@shiptrack.local")
        monkeypatch.setenv("COURIER2_USERNAME", "courier_agent2")
        monkeypatch.setenv("COURIER2_EMAIL", "courier2@shiptrack.local")

        # Create app pointing to the temp database
        app = create_app(test_config={
            "TESTING": True,
            "DATABASE": temp_db_path,
            "SECRET_KEY": "startup-test-secret-key"
        })
        client = app.test_client()

        # 1. Admin login via username
        res_admin_user = client.post("/api/auth/login", json={
            "identifier": "admin",
            "password": "TestEnvAdminPass2026!"
        })
        assert res_admin_user.status_code == 200, res_admin_user.get_json()
        assert res_admin_user.get_json()["user"]["role"] == "admin"

        # Admin me check
        me_admin = client.get("/api/auth/me")
        assert me_admin.status_code == 200
        assert me_admin.get_json()["user"]["username"] == "admin"
        assert me_admin.get_json()["user"]["email"] == "admin@shiptrack.local"

        client.post("/api/auth/logout")

        # 2. Admin login via email
        res_admin_email = client.post("/api/auth/login", json={
            "identifier": "admin@shiptrack.local",
            "password": "TestEnvAdminPass2026!"
        })
        assert res_admin_email.status_code == 200
        client.post("/api/auth/logout")

        # 3. Courier 1 login via username
        res_courier_user = client.post("/api/auth/login", json={
            "identifier": "courier_agent1",
            "password": "TestEnvCourierPass2026!"
        })
        assert res_courier_user.status_code == 200, res_courier_user.get_json()
        assert res_courier_user.get_json()["user"]["role"] == "delivery_person"

        # Courier 1 me check
        me_courier = client.get("/api/auth/me")
        assert me_courier.status_code == 200
        assert me_courier.get_json()["user"]["username"] == "courier_agent1"
        assert me_courier.get_json()["user"]["email"] == "courier1@shiptrack.local"

        client.post("/api/auth/logout")

        # 4. Courier 1 login via email
        res_courier_email = client.post("/api/auth/login", json={
            "identifier": "courier1@shiptrack.local",
            "password": "TestEnvCourierPass2026!"
        })
        assert res_courier_email.status_code == 200
        client.post("/api/auth/logout")

        # 5. Courier 2 login via username
        res_c2_user = client.post("/api/auth/login", json={
            "identifier": "courier_agent2",
            "password": "TestEnvCourier2Pass2026!"
        })
        assert res_c2_user.status_code == 200, res_c2_user.get_json()
        assert res_c2_user.get_json()["user"]["role"] == "delivery_person"

        # Courier 2 me check
        me_c2 = client.get("/api/auth/me")
        assert me_c2.status_code == 200
        assert me_c2.get_json()["user"]["username"] == "courier_agent2"
        assert me_c2.get_json()["user"]["email"] == "courier2@shiptrack.local"

        client.post("/api/auth/logout")

        # 6. Courier 2 login via email
        res_c2_email = client.post("/api/auth/login", json={
            "identifier": "courier2@shiptrack.local",
            "password": "TestEnvCourier2Pass2026!"
        })
        assert res_c2_email.status_code == 200
        client.post("/api/auth/logout")

    finally:
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except OSError:
                pass
