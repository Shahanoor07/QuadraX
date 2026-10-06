# Deployment Documentation — Build Secure 24

## Overview

This directory contains the production deployment configuration, runner commands, and operational runtime reference for **PS-05 ShipTrack: Delivery & Shipment Management (Logistics)**.

---

## Live Deployment Reference

- **Application Name:** ShipTrack Logistics Management Platform
- **Hosting Platform:** Python WSGI (Gunicorn) / Flask
- **Primary Repository:** [https://github.com/Shahanoor07/QuadraX](https://github.com/Shahanoor07/QuadraX)
- **Default Seed Accounts:**
  - Admin: `admin@shiptrack.com` (password configured via `ADMIN_PASSWORD`)
  - Delivery Courier: `courier@shiptrack.com` (password configured via `DELIVERY_PASSWORD`)
  - Customer: Register directly via public sign-up at `/` or test with existing seeded accounts.

---

## Required Environment Variables

| Variable Name | Description | Required | Default |
|---------------|-------------|----------|---------|
| `SECRET_KEY` | Cryptographic key used to sign secure session cookies (`HttpOnly`, `SameSite=Lax`). | Recommended | Auto-generated random 32-byte hex if omitted |
| `ADMIN_PASSWORD` | Password for initializing the default `admin@shiptrack.com` user on startup. | Optional | `AdminSecurePass123!` |
| `DELIVERY_PASSWORD` | Password for initializing the default `courier@shiptrack.com` user on startup. | Optional | `CourierSecurePass123!` |
| `FLASK_DATABASE_PATH` | Path to the SQLite database file. | Optional | `src/backend/shiptrack.db` |
| `PORT` | Listening port for web server. | Optional | `5000` |

---

## Build & Deployment Instructions

### 1. Environment Setup
```bash
# Clone the repository
git clone https://github.com/Shahanoor07/QuadraX.git
cd QuadraX

# Create and activate Python virtual environment
python -m venv .venv
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r src/backend/requirements.txt
```

### 2. Run Test Suite
```bash
python -m pytest tests/ -v
```

### 3. Launch with Gunicorn (Production)
```bash
export SECRET_KEY="your-strong-production-secret-key"
export ADMIN_PASSWORD="YourStrongAdminPassword123!"
export DELIVERY_PASSWORD="YourStrongCourierPassword123!"

gunicorn -w 4 -b 0.0.0.0:5000 src.backend.app:app
```

On Windows / Development:
```bash
python src/backend/app.py
```
The database and tables are created automatically on startup, and seed accounts are initialized safely. Access the application in any modern web browser at `http://localhost:5000`.
