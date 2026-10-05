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
| **Phase 3: Shipment Workflows** | 10h – 16h | Customer shipment creation, tracking lookup, courier dashboard, status update logging | BOLA/IDOR test, anti-probing 404 checks & ownership verification | `In Progress` |
| **Phase 4: Admin & UI Integration**| 16h – 20h | Admin management dashboard, frontend integration with Bootstrap CDN | Input escaping & cross-role access check | `Planned` |
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

---

## 6. Testing, Security Verification & Deployment Record

### 6.1 Testing & Security Verification Strategy
- **Unit & Schema Verification:** Schema parsed and validated in SQLite in-memory runner; all foreign keys, indexes, and constraints verified.
- **Security Check:** Zero hardcoded secrets; `.env.example` created and `.gitignore` updated to prevent committing database or credential files.

### 6.2 Deployment Verification
- **Target Platform:** Cloud Deployment (e.g. Render / Railway / PythonAnywhere)
- **Deployment URL:** *Pending deployment phase*
- **Health Check Endpoint:** `/api/health`
