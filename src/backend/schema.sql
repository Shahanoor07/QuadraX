-- SQLite Schema for ShipTrack (PS-05)
-- Delivery & Shipment Management
PRAGMA foreign_keys = ON;

-- 1. Users Table
-- Supports roles: customer, delivery_person, admin
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('customer', 'delivery_person', 'admin')),
    full_name TEXT NOT NULL,
    phone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- 2. Shipments Table
-- Links to customer (creator/owner) and assigned delivery person
CREATE TABLE IF NOT EXISTS shipments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tracking_number TEXT UNIQUE NOT NULL,
    customer_id INTEGER NOT NULL,
    assigned_delivery_id INTEGER,
    sender_name TEXT NOT NULL,
    sender_address TEXT NOT NULL,
    recipient_name TEXT NOT NULL,
    recipient_address TEXT NOT NULL,
    recipient_phone TEXT NOT NULL,
    package_description TEXT NOT NULL,
    weight_kg REAL NOT NULL DEFAULT 1.0,
    current_status TEXT NOT NULL DEFAULT 'Order Placed' CHECK(
        current_status IN (
            'Order Placed',
            'Picked Up',
            'In Transit',
            'Out for Delivery',
            'Delivered',
            'Cancelled'
        )
    ),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_delivery_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_shipments_tracking ON shipments(tracking_number);
CREATE INDEX IF NOT EXISTS idx_shipments_customer ON shipments(customer_id);
CREATE INDEX IF NOT EXISTS idx_shipments_assigned ON shipments(assigned_delivery_id);
CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(current_status);

-- 3. Status Updates Table
-- Audit trail and tracking timeline for each shipment update
CREATE TABLE IF NOT EXISTS status_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id INTEGER NOT NULL,
    updated_by_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(
        status IN (
            'Order Placed',
            'Picked Up',
            'In Transit',
            'Out for Delivery',
            'Delivered',
            'Cancelled'
        )
    ),
    location TEXT NOT NULL,
    notes TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE,
    FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_updates_shipment ON status_updates(shipment_id);
CREATE INDEX IF NOT EXISTS idx_updates_timestamp ON status_updates(timestamp);
