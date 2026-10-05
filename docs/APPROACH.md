# Project Approach & Architecture — Build Secure 24

**Team ID:** 29
**Project Name:** ShipTrack (PS-05) — Delivery & Shipment Management
**Team Size:** 4 Members
**Primary Track / Domain:** Logistics & Supply Chain Cybersecurity / Secure Web Engineering

---

## 1. Problem Understanding, Scope & Threat Model

### 1.1 Problem Statement & Real-World Motivation
Logistics and shipment tracking systems operate across distributed actors (customers, couriers, administrators) handling sensitive personal identifiable information (PII) and physical goods. Common vulnerabilities in logistics platforms include:
- **Broken Object-Level Authorization (BOLA / IDOR):** Unauthenticated or unauthorized users accessing details of packages they do not own.
- **SQL Injection (SQLi):** Malicious inputs in search or tracking fields compromising the backend database.
- **Privilege Escalation:** Delivery personnel or regular customers modifying shipment assignments or accessing administrative functions.
- **Data Tampering:** Unauthorized modification of shipment tracking stages and status logs.

ShipTrack addresses these challenges with strict defense-in-depth security: 100% parameterized SQL queries, mandatory role-based access control (RBAC), object-level ownership verification on every shipment endpoint, and secure cryptographic password hashing.

### 1.2 Target Users & Personas
- **Customer:** Registers account, creates new shipment requests, tracks shipments via tracking number, and views personal shipment history.
- **Delivery Person:** Accesses a dedicated courier portal, views assigned parcels, and logs validated delivery status milestones (`Picked Up`, `In Transit`, `Out for Delivery`, `Delivered`).
- **Administrator:** Manages system users, assigns unassigned shipments to delivery personnel, cancels problematic shipments, and oversees platform health.

### 1.3 Threat Model & Attack Surface
- **Critical Assets:** User credentials (passwords, sessions), Customer PII (sender/recipient addresses, phone numbers), Shipment tracking lifecycle, Delivery audit logs.
- **Potential Attack Vectors:**
  - SQL Injection via tracking search bars or filter query parameters.
  - BOLA / IDOR via guessing or iterating sequential shipment IDs.
  - Role bypass or session manipulation to access admin or delivery functions.
  - Cross-Site Scripting (XSS) via package descriptions or delivery notes.
- **OWASP Top 10 Considerations:**
  - **A01: Broken Access Control:** Enforce server-side role checks and ownership validations (`customer_id == session.user_id`) on all requests.
  - **A02: Cryptographic Failures:** Passwords hashed with salted PBKDF2/scrypt via `werkzeug.security`.
  - **A03: Injection:** Zero string concatenation in database operations; 100% parameterized queries.
  - **A07: Identification and Authentication Failures:** Secure session cookies, password complexity, and timing-safe hash comparison.

---

## 2. Technical Architecture & Secure System Design

### 2.1 High-Level Architecture Overview
ShipTrack adopts a clean two-tier decoupled architecture:
```
┌────────────────────────────────────────────────────────┐
│               Frontend Presentation Layer              │
│       src/frontend/ (Hand-written HTML/CSS/JS)         │
│          Bootstrap 5 CDN + Responsive UI               │
└───────────────────────────▲────────────────────────────┘
                            │ REST / JSON (Fetch API)
┌───────────────────────────▼────────────────────────────┐
│                  Backend Service Layer                 │
│               src/backend/ (Python Flask)              │
│   ├── Auth & Session Management (werkzeug.security)    │
│   ├── RBAC & Ownership Verification Middleware         │
│   └── Parameterized SQL Query Engine (db.py)           │
└───────────────────────────▲────────────────────────────┘
                            │ Parameterized queries (sqlite3)
┌───────────────────────────▼────────────────────────────┐
│                 Data Persistence Layer                 │
│         SQLite with Foreign Keys Enforced (PRAGMA)     │
│   ├── users (customer, delivery_person, admin)         │
│   ├── shipments (tracking, sender, recipient, status)  │
│   └── status_updates (audit log & delivery timeline)   │
└────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow & Component Interaction
1. **User Authentication:** User submits credentials -> Flask hashes & checks via `werkzeug.security` -> Secure session established with role tag.
2. **Shipment Ingress:** Customer submits shipment form -> Flask validates input fields -> Parameterized `INSERT` creates shipment with unique tracking code.
3. **Tracking & Ownership:** Customer requests shipment details -> Server validates `customer_id == current_user.id` (or user is admin/assigned courier) -> Returns filtered record.
4. **Delivery Update:** Delivery courier submits status change -> Server verifies role and courier assignment -> Parameterized `UPDATE` modifies shipment and creates audit record in `status_updates`.

### 2.3 Technology Stack Rationale
- **Backend Framework:** Python Flask — lightweight, flexible, and allows fine-grained security control over every route and middleware layer.
- **Frontend / Client:** Hand-written HTML/CSS/JS with Bootstrap 5 CDN — fast, zero-dependency build pipeline, responsive, and easy to audit for security.
- **Database:** SQLite with `PRAGMA foreign_keys = ON;` — self-contained, transactional, zero network exposure, ideal for hackathon agility with full ACID compliance.
- **Cryptography:** `werkzeug.security` (`generate_password_hash`, `check_password_hash`) — robust, salted, collision-resistant password storage.

### 2.4 Defense-in-Depth Security Controls
1. **100% Parameterized SQL:** All SQL operations use parameter placeholders (`?`). String formatting/f-strings in SQL are strictly prohibited.
2. **Role-Based Access Control (RBAC):** Decorators on every route enforce required roles (`customer`, `delivery_person`, `admin`).
3. **Object-Level Authorization:** Users can only view or manipulate shipments they own or are assigned to.
4. **Input Sanitization & Output Escaping:** All user-supplied inputs (descriptions, notes, addresses) are validated and escaped before display.
5. **Audit Trail Logging:** All delivery status transitions are recorded in `status_updates` with updater ID, location, notes, and timestamps.

---

## 3. Implementation Milestones & 24-Hour Timeline

| Milestone / Phase | Time Window | Key Objectives & Deliverables | Security Verification | Status |
|---|---|---|---|---|
| **Phase 1: Foundation & Setup** | 0h – 4h | Onboarding, repo structure, SQLite schema (`users`, `shipments`, `status_updates`), `requirements.txt` | Schema constraint test & foreign key validation | `Completed` |
| **Phase 2: Core Domain & Auth** | 4h – 10h | User registration/login (`werkzeug.security`), session auth, role decorators, seeding script | Auth test suite, rate limit check & password hash verification | `Completed` |
| **Phase 3: Shipment Workflows** | 10h – 16h | Customer shipment creation, tracking lookup, courier dashboard, status update logging | BOLA/IDOR test, anti-probing 404 checks & ownership verification | `Completed` |
| **Phase 4: Admin & UI Integration**| 16h – 20h | Admin management dashboard, shipment assignment, user management, frontend UI integration | Input escaping, cross-role access check & courier assignment audit | `In Progress` |
| **Phase 5: Polish & Deployment**| 20h – 24h | End-to-end testing, live deployment, submission commit freeze | SAST scan & live health check | `Planned` |

---

## 4. Architecture Decision Records (ADRs)

### ADR-001: SQLite Database Engine with Parameterized SQL Helper
- **Status:** Accepted
- **Context:** ShipTrack requires reliable transactional storage without complex database servers, while strictly preventing SQL injection.
- **Options Considered:**
  1. Full ORM (SQLAlchemy)
  2. Raw SQLite with custom parameterized helpers (`query_db`, `execute_db`)
- **Decision & Rationale:** Chose raw SQLite with explicit parameterized helper functions. This ensures complete transparency over every query, guarantees zero ORM abstraction leakage, and enforces `PRAGMA foreign_keys = ON;`.
- **Security & Performance Trade-offs:** Zero external database attack surface, instantaneous setup, microsecond query speeds, and verifiable parameterization across all queries.

### ADR-002: werkzeug.security Salted Password Hashing
- **Status:** Accepted
- **Context:** User passwords must never be stored in plaintext or with reversible algorithms.
- **Options Considered:**
  1. Plain SHA256 / MD5 (Insecure, vulnerable to rainbow tables)
  2. `werkzeug.security` (`scrypt` / `pbkdf2:sha256`)
- **Decision & Rationale:** `werkzeug.security` is bundled with Flask, implements industry-standard salted hashing, and provides timing-attack resistant verification (`check_password_hash`).
- **Security & Performance Trade-offs:** Excellent resistance against offline brute-force and rainbow table attacks.

### ADR-003: Rate Limiting and Anti-Enumeration for Authentication
- **Status:** Accepted
- **Context:** Protect the application against brute-force password guessing and username enumeration attacks.
- **Options Considered:**
  1. Distinct error messages ("User not found" vs "Wrong password")
  2. Uniform generic error responses combined with IP/Identifier failure window throttling
- **Decision & Rationale:** Used identical generic error messages for all failed login attempts, preventing username harvesting. Enforced a lockout threshold of 5 failures per 5-minute window with a 15-minute cooldown.
- **Security & Performance Trade-offs:** Drastically improves attack resistance with negligible overhead.

### ADR-004: Anti-Probing (HTTP 404) Response Strategy for BOLA / IDOR Mitigation
- **Status:** Accepted
- **Context:** If unauthorized requests to access another customer's shipment return HTTP 403 Forbidden, attackers can enumerate existing valid tracking numbers and IDs by distinguishing between 404 (non-existent) and 403 (exists, but belongs to someone else).
- **Options Considered:**
  1. Return HTTP 403 Forbidden on foreign shipments (Leads to object enumeration / ID probing)
  2. Return HTTP 404 Not Found on unauthorized foreign shipments
- **Decision & Rationale:** Return HTTP 404 whenever a customer or unassigned courier attempts to access or cancel a shipment they do not own. This completely obscures the existence of shipments belonging to other users.
- **Security & Performance Trade-offs:** Eliminates tracking ID enumeration vulnerabilities at zero runtime cost.

### ADR-005: Cryptographic Chain of Custody for Shipment Milestones
- **Status:** Accepted
- **Context:** Shipment status updates and tracking milestones in delivery systems are subject to retroactive tampering or database alterations.
- **Options Considered:**
  1. Plain mutable database rows (Vulnerable to silent modifications)
  2. Cryptographic hash-chained immutable ledger using SHA-256 (`prev_hash`, `record_hash`)
- **Decision & Rationale:** Each status update links to its predecessor via SHA-256 hash chaining initialized by a 64-zero genesis hash. The `/api/shipments/<id>/verify` endpoint enables owners and admins to independently recompute and mathematically verify chain integrity or isolate the exact modified record.
- **Security & Performance Trade-offs:** Provides mathematical non-repudiation and tamper-evidence with trivial hashing overhead.

### ADR-006: Passive Attack Detection Sensors and Intrusion Audit Telemetry
- **Status:** Accepted
- **Context:** Proactively identifying scanning, brute-force, BOLA probing, and unauthorized access attempts without disrupting legitimate traffic or relying solely on heuristic blocking.
- **Options Considered:**
  1. No logging or plain file logs (Difficult to query, no audit API)
  2. Structured `security_events` table populated by security middleware and sensors, accessible via paginated admin API
- **Decision & Rationale:** Added `security_events` table and `log_security_event()` helper. Logs failed authentications, lockouts, 401/403 denials, cross-customer probing, and suspicious payload patterns. An admin-only paginated endpoint (`/api/admin/security-events`) provides live observability.
- **Security & Performance Trade-offs:** Minimal DB write overhead; provides essential forensics and incident detection.

### ADR-007: Ephemeral Single-Use Hashed Tracking Links & GPS Telemetry Stream
- **Status:** Accepted
- **Context:** Protecting high-value shipments from link eavesdropping, unauthorized tracking scraping, and replay attacks while enabling recipient live tracking without full platform registration.
- **Options Considered:**
  1. Static permanent tracking URLs (Vulnerable to shoulder surfing, unauthorized distribution, scraping)
  2. Cryptographically hashed single-use ephemeral links with live GPS ingestion
- **Decision & Rationale:** Generated 32-byte cryptographically secure random tokens (`secrets.token_urlsafe(32)`). Stored exclusively as SHA-256 digests in `tracking_tokens`. The endpoint `GET /api/tracking/live/<token>` burns the token on the very first access (`is_used = 1`), rendering replay attempts invalid (HTTP 410 Gone) and logging security alerts. Couriers stream live GPS coordinates into `shipment_telemetry` with coordinate boundary validation and assignment isolation.
- **Security & Performance Trade-offs:** Complete mitigation of replay attacks and URL interception; raw tokens cannot be recovered even if the database is compromised.

---

## 5. Engineering Journal & Real-Time Decision Log

### 2026-10-05 13:15 IST — Entry 1: Problem Scope Lock & Baseline Scaffold
- **Focus:** Initialized PS-05 ShipTrack project architecture. Created SQLite schema defining `users`, `shipments`, and `status_updates` tables with comprehensive indexes and foreign keys.
- **Key Challenges:** Ensuring foreign key constraints are honored in SQLite (SQLite disables them by default).
- **Resolution:** Explicitly configured `PRAGMA foreign_keys = ON;` in `schema.sql` and `db.py` connection factory.

### 2026-10-05 13:25 IST — Entry 2: Secure Authentication & Role Authorization Scaffolding
- **Focus:** Implemented customer registration with enforced role restriction, login, session management, logout, and `/api/auth/me`. Implemented `login_required` and `role_required` decorators. Created test seeding script (`seed.py`) with zero hardcoded passwords.
- **Key Challenges:** Ensuring cookies are tamper-proof and resilient against client-side script hijacking while allowing standard browsers to handle CSRF.
- **Resolution:** Configured `HttpOnly=True` and `SameSite=Lax` on Flask session cookies with environment-derived `SECRET_KEY`. Verified via unit tests with 100% pass rate.

### 2026-10-05 14:10 IST — Entry 3: Customer Shipment Workflows & Anti-Probing Defenses
- **Focus:** Implemented customer shipment creation (`POST /api/shipments`), customer history (`GET /api/shipments`), detail tracking (`GET /api/shipments/<tracking_number>`), and order cancellation (`POST /api/shipments/<id>/cancel`).
- **Key Challenges:** Preventing ID probing and BOLA attacks when users query tracking numbers or IDs.
- **Resolution:** Implemented server-side tracking number generation (`ST-YYYYMMDD-XXXXXX`), forced `customer_id` from session, and enforced HTTP 404 on foreign shipment accesses. Wrote automated pytest suite in `tests/test_customer_shipments.py`.

### 2026-10-05 15:00 IST — Entry 4: Security Foundation — Hash Chaining & Attack Telemetry
- **Focus:** Implemented SHA-256 chain of custody across status updates (`prev_hash`, `record_hash`), centralized `add_status_update()` helper, and `/api/shipments/<id>/verify` validation endpoint. Built intrusion telemetry system (`security_events`, `log_security_event()`, `check_and_log_suspicious_input()`) and paginated admin endpoint `GET /api/admin/security-events`.
- **Key Challenges:** Guaranteeing that direct database mutation is immediately detected upon audit.
- **Resolution:** Validated tamper detection in `tests/test_security_foundation.py` by mutating database rows and verifying that `/api/shipments/<id>/verify` flags `valid: false` with the exact tampered record metadata.

### 2026-10-05 15:15 IST — Entry 5: Delivery & Admin Role Operations Completed
- **Focus:** Implemented complete delivery person module (`src/backend/delivery.py`) with courier dashboard, assigned tasks, and milestone progression (`Picked Up` -> `In Transit` -> `Out for Delivery` -> `Delivered`) chained into cryptographic custody ledger. Implemented admin management module (`src/backend/admin.py`) with system metrics, all shipments listing, courier assignment (`/api/admin/shipments/<id>/assign`), and user management.
- **Key Challenges:** Ensuring couriers cannot tamper with unassigned shipments or modify packages once marked Delivered.
- **Resolution:** Enforced BOLA assignment check (`assigned_delivery_id == session["user_id"]`), terminal status freeze on Delivered shipments, and verified all 7 automated test suites passing.

### 2026-10-05 15:25 IST — Entry 6: Live GPS Telemetry & Single-Use Ephemeral Tracking Links
- **Focus:** Implemented high-value cargo live GPS tracking and anti-interception ephemeral links. Added `shipment_telemetry` and `tracking_tokens` tables. Authored public burn-on-first-view tracking blueprint (`src/backend/tracking.py`), customer token generator (`/api/shipments/<id>/generate-tracking-link`), and courier live GPS ingestion (`/api/delivery/shipments/<id>/telemetry`).
- **Key Challenges:** Protecting against replay attacks and token interception while maintaining zero-knowledge token storage.
- **Resolution:** Raw tokens are never persisted to the database; incoming tokens are checked via SHA-256 digests and immediately burned (`is_used = 1`). Replays return HTTP 410 Gone and log `REPLAY_ATTACK_DETECTED`. Created 9 comprehensive automated tests in `tests/test_gps_and_ephemeral_token.py`, achieving 16/16 test passes across the entire test suite.

---

## 6. Testing, Security Verification & Deployment Record

### 6.1 Testing & Security Verification Strategy
- **Unit & Security Test Suite:** 100% passing automated test suite (16 tests across 4 test modules, 0 failures):
  - Customer shipment isolation, input validation, and BOLA prevention (`tests/test_customer_shipments.py`)
  - Cryptographic chain of custody, database tampering detection, security event logging, and admin telemetry (`tests/test_security_foundation.py`)
  - Delivery person lifecycle transitions, terminal state protection, courier assignment, and admin operations (`tests/test_delivery_and_admin.py`)
  - Live GPS coordinate ingestion, single-use token burn, replay attack prevention, and expiration controls (`tests/test_gps_and_ephemeral_token.py`)
- **Security Check:** Zero hardcoded credentials, parameterized queries on all endpoints, anti-enumeration generic auth responses, rate limit lockouts, and HttpOnly/SameSite cookies.

### 6.2 Deployment Verification
- **Target Platform:** Cloud Deployment (e.g. Render / Railway / PythonAnywhere)
- **Deployment URL:** *Pending deployment phase*
- **Health Check Endpoint:** `/api/health`
