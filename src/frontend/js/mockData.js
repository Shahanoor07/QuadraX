/**
 * ShipTrack: Delivery & Shipment Management (PS-05)
 * Rich Mock Data & Pre-populated State
 */

const MOCK_DATA = {
  // Current logged in demo accounts
  demoUsers: {
    customer: {
      id: 1,
      username: "alice",
      email: "alice@customer.local",
      role: "customer",
      full_name: "Alice Vance",
      phone: "+91 97777 00001",
      avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop&q=80"
    },
    delivery: {
      id: 2,
      username: "courier_alpha",
      email: "courier1@shiptrack.local",
      role: "delivery_person",
      full_name: "Rajesh Kumar (Courier Alpha)",
      phone: "+91 98888 00001",
      vehicle: "Electric Cargo Van (TS-09-EQ-4421)",
      rating: 4.9,
      total_deliveries: 1240,
      avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80"
    },
    admin: {
      id: 3,
      username: "head_admin",
      email: "admin@shiptrack.local",
      role: "admin",
      full_name: "Sarah Chen (Fleet Ops Director)",
      phone: "+91 99999 00001",
      avatar: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80"
    }
  },

  // Courier Portrait Asset
  courierPortrait: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300&auto=format&fit=crop&q=80",

  // Driver Roster for Admin & Tracking Views
  drivers: [
    {
      id: 2,
      name: "Rajesh Kumar",
      callsign: "Courier Alpha",
      phone: "+91 98888 00001",
      vehicle: "Electric Cargo Van",
      plate: "TS-09-EQ-4421",
      status: "Online",
      rating: 4.9,
      proximity: "1.2 km away",
      completed_today: 5,
      active_tasks: 2,
      avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80"
    },
    {
      id: 4,
      name: "Vikram Malhotra",
      callsign: "Courier Beta",
      phone: "+91 98888 00002",
      vehicle: "Refrigerated Transit Van",
      plate: "TS-07-EX-8890",
      status: "Online",
      rating: 4.8,
      proximity: "3.4 km away",
      completed_today: 7,
      active_tasks: 1,
      avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80"
    },
    {
      id: 5,
      name: "Ananya Sharma",
      callsign: "Courier Gamma",
      phone: "+91 98888 00003",
      vehicle: "Rapid Two-Wheeler (EV)",
      plate: "TS-10-TW-1144",
      status: "Offline",
      rating: 4.95,
      proximity: "5.8 km away",
      completed_today: 9,
      active_tasks: 0,
      avatar: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&auto=format&fit=crop&q=80"
    }
  ],

  // Pre-populated Shipments
  shipments: [
    {
      id: 101,
      tracking_number: "ST-20261005-481920",
      customer_id: 1,
      customer_name: "Alice Vance",
      assigned_delivery_id: 2,
      driver_name: "Rajesh Kumar",
      driver_phone: "+91 98888 00001",
      driver_avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
      sender_name: "Precision Labs Tech",
      sender_address: "100 Safe Deposit Way, HITEC City, Hyderabad",
      recipient_name: "Charlie Jenkins",
      recipient_address: "Flat 402, Cyber Tower Heights, Madhapur, Hyderabad",
      recipient_phone: "+91 91234 56789",
      postal_code: "500081",
      package_description: "High-Value Titanium Swiss Watch",
      weight_kg: 1.2,
      tier: "Same-Day Priority",
      declared_value: 3500,
      cost: 45.00,
      current_status: "Out for Delivery",
      created_at: "2026-10-05 09:15:00",
      updated_at: "2026-10-05 14:40:00",
      is_fragile: true,
      otp: "849201",
      telemetry: {
        latitude: 17.4485,
        longitude: 78.3752,
        speed_kmh: 38.5,
        heading_degrees: 145,
        battery_pct: 84,
        timestamp: "2026-10-05 14:40:00"
      },
      timeline: [
        {
          status: "Order Placed",
          location: "HITEC City Booking Hub",
          notes: "Shipment request verified and packaged with tamper-proof security seal.",
          timestamp: "2026-10-05 09:15:00",
          updater: "Alice Vance",
          prev_hash: "0000000000000000000000000000000000000000000000000000000000000000",
          record_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        },
        {
          status: "Picked Up",
          location: "Sender Facility, HITEC City",
          notes: "Courier Alpha picked up cargo with identity verification.",
          timestamp: "2026-10-05 10:30:00",
          updater: "Rajesh Kumar (Courier Alpha)",
          prev_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          record_hash: "a4f89d3080e4b7b2576b5c328b9813f36a5818987b229712a4454b5df5164cf3"
        },
        {
          status: "In Transit",
          location: "Central Logistics Gateway 04",
          notes: "Dispatched towards destination zone; telemetry telemetry sensor activated.",
          timestamp: "2026-10-05 12:15:00",
          updater: "Rajesh Kumar (Courier Alpha)",
          prev_hash: "a4f89d3080e4b7b2576b5c328b9813f36a5818987b229712a4454b5df5164cf3",
          record_hash: "7f4c3b99912048aa79bc08c2a3843e9b109b821430ec9df438902bebc77441a0"
        },
        {
          status: "Out for Delivery",
          location: "Madhapur Delivery Sector 12",
          notes: "Courier is on final delivery approach; recipient notified via secure channel.",
          timestamp: "2026-10-05 14:40:00",
          updater: "Rajesh Kumar (Courier Alpha)",
          prev_hash: "7f4c3b99912048aa79bc08c2a3843e9b109b821430ec9df438902bebc77441a0",
          record_hash: "2e9a8f4c22b918a99d45ef81938590bc98374850918b9183749021a837264819"
        }
      ]
    },
    {
      id: 102,
      tracking_number: "ST-20261005-784912",
      customer_id: 1,
      customer_name: "Alice Vance",
      assigned_delivery_id: 2,
      driver_name: "Rajesh Kumar",
      driver_phone: "+91 98888 00001",
      driver_avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
      sender_name: "MedLife Pharmaceuticals",
      sender_address: "Sector 5, Genome Valley, Shamirpet",
      recipient_name: "Dr. Evelyn Reed",
      recipient_address: "Apollo Health Institute, Jubilee Hills, Hyderabad",
      recipient_phone: "+91 98765 43211",
      postal_code: "500033",
      package_description: "Cold-Chain Diagnostic Vaccines",
      weight_kg: 3.5,
      tier: "Express 1-2 Days",
      declared_value: 1200,
      cost: 28.50,
      current_status: "In Transit",
      created_at: "2026-10-05 08:30:00",
      updated_at: "2026-10-05 11:50:00",
      is_fragile: true,
      otp: "918234",
      telemetry: {
        latitude: 17.4320,
        longitude: 78.4070,
        speed_kmh: 46.0,
        heading_degrees: 210,
        battery_pct: 91,
        timestamp: "2026-10-05 11:50:00"
      },
      timeline: [
        {
          status: "Order Placed",
          location: "Genome Valley Hub",
          notes: "Booking confirmed with thermal insulation packaging.",
          timestamp: "2026-10-05 08:30:00",
          updater: "Alice Vance",
          prev_hash: "0000000000000000000000000000000000000000000000000000000000000000",
          record_hash: "11a8b9e02c918374a89d71829304857182930491829384758192837465718293"
        },
        {
          status: "Picked Up",
          location: "Genome Valley Cold Storage",
          notes: "Temperature logged at 4.2°C; custody transferred to Courier Alpha.",
          timestamp: "2026-10-05 09:45:00",
          updater: "Rajesh Kumar (Courier Alpha)",
          prev_hash: "11a8b9e02c918374a89d71829304857182930491829384758192837465718293",
          record_hash: "33b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7"
        },
        {
          status: "In Transit",
          location: "Outer Ring Road Transit Way",
          notes: "In transit towards Jubilee Hills regional medical depot.",
          timestamp: "2026-10-05 11:50:00",
          updater: "Rajesh Kumar (Courier Alpha)",
          prev_hash: "33b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7",
          record_hash: "55c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9"
        }
      ]
    },
    {
      id: 103,
      tracking_number: "ST-20261005-192843",
      customer_id: 1,
      customer_name: "Alice Vance",
      assigned_delivery_id: 4,
      driver_name: "Vikram Malhotra",
      driver_phone: "+91 98888 00002",
      driver_avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80",
      sender_name: "Apex Legal Partners",
      sender_address: "88 Banjara Hills Road No. 12, Hyderabad",
      recipient_name: "Global Ventures Inc.",
      recipient_address: "Financial District, Nanakramguda, Hyderabad",
      recipient_phone: "+91 98765 11223",
      postal_code: "500032",
      package_description: "Confidential M&A Contracts & Deeds",
      weight_kg: 0.8,
      tier: "Standard 3-5 Days",
      declared_value: 500,
      cost: 16.50,
      current_status: "Picked Up",
      created_at: "2026-10-05 11:00:00",
      updated_at: "2026-10-05 13:20:00",
      is_fragile: false,
      otp: "331904",
      telemetry: {
        latitude: 17.4165,
        longitude: 78.4480,
        speed_kmh: 22.0,
        heading_degrees: 270,
        battery_pct: 95,
        timestamp: "2026-10-05 13:20:00"
      },
      timeline: [
        {
          status: "Order Placed",
          location: "Banjara Hills Booking Counter",
          notes: "Legal documents sealed in tamper-evident envelope.",
          timestamp: "2026-10-05 11:00:00",
          updater: "Alice Vance",
          prev_hash: "0000000000000000000000000000000000000000000000000000000000000000",
          record_hash: "77a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8"
        },
        {
          status: "Picked Up",
          location: "Banjara Hills Hub",
          notes: "Courier Beta accepted parcel custody.",
          timestamp: "2026-10-05 13:20:00",
          updater: "Vikram Malhotra (Courier Beta)",
          prev_hash: "77a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8",
          record_hash: "99b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
        }
      ]
    },
    {
      id: 104,
      tracking_number: "ST-20261004-918234",
      customer_id: 1,
      customer_name: "Alice Vance",
      assigned_delivery_id: 2,
      driver_name: "Rajesh Kumar",
      driver_phone: "+91 98888 00001",
      driver_avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
      sender_name: "Silicon Microcircuits",
      sender_address: "Hardware Park, Shamshabad",
      recipient_name: "Kiran Rao",
      recipient_address: "Begumpet Airport Colony, Secunderabad",
      recipient_phone: "+91 98480 22334",
      postal_code: "500016",
      package_description: "Industrial IoT Edge Gateways (x4)",
      weight_kg: 5.4,
      tier: "Express 1-2 Days",
      declared_value: 2100,
      cost: 38.00,
      current_status: "Delivered",
      created_at: "2026-10-04 10:00:00",
      updated_at: "2026-10-04 16:30:00",
      is_fragile: true,
      otp: "552190",
      delivered_at: "2026-10-04 16:30:00",
      timeline: [
        {
          status: "Order Placed",
          location: "Shamshabad Logistics Hub",
          notes: "Electronic parts packaged in anti-static foam.",
          timestamp: "2026-10-04 10:00:00",
          updater: "Alice Vance",
          prev_hash: "0000000000000000000000000000000000000000000000000000000000000000",
          record_hash: "aa11bb22cc33dd44ee55ff6600112233445566778899aabbccddeeff00112233"
        },
        {
          status: "Picked Up",
          location: "Shamshabad Hardware Depot",
          notes: "Cargo loaded onto secure vehicle.",
          timestamp: "2026-10-04 11:30:00",
          updater: "Rajesh Kumar (Courier Alpha)",
          prev_hash: "aa11bb22cc33dd44ee55ff6600112233445566778899aabbccddeeff00112233",
          record_hash: "bb22cc33dd44ee55ff6600112233445566778899aabbccddeeff001122334455"
        },
        {
          status: "In Transit",
          location: "PVNR Expressway corridor",
          notes: "Transit across central corridor on schedule.",
          timestamp: "2026-10-04 13:45:00",
          updater: "Rajesh Kumar (Courier Alpha)",
          prev_hash: "bb22cc33dd44ee55ff6600112233445566778899aabbccddeeff001122334455",
          record_hash: "cc33dd44ee55ff6600112233445566778899aabbccddeeff0011223344556677"
        },
        {
          status: "Out for Delivery",
          location: "Secunderabad Local Dispatch Hub",
          notes: "Driver dispatched for final drop-off.",
          timestamp: "2026-10-04 15:10:00",
          updater: "Rajesh Kumar (Courier Alpha)",
          prev_hash: "cc33dd44ee55ff6600112233445566778899aabbccddeeff0011223344556677",
          record_hash: "dd44ee55ff6600112233445566778899aabbccddeeff00112233445566778899"
        },
        {
          status: "Delivered",
          location: "Begumpet Recipient Gate",
          notes: "Delivered successfully. Recipient signature verified via OTP 552190.",
          timestamp: "2026-10-04 16:30:00",
          updater: "Rajesh Kumar (Courier Alpha)",
          prev_hash: "dd44ee55ff6600112233445566778899aabbccddeeff00112233445566778899",
          record_hash: "ee55ff6600112233445566778899aabbccddeeff001122334455667788990011"
        }
      ]
    },
    {
      id: 105,
      tracking_number: "ST-20261005-551928",
      customer_id: 1,
      customer_name: "Alice Vance",
      assigned_delivery_id: null,
      driver_name: null,
      driver_phone: null,
      driver_avatar: null,
      sender_name: "CloudData Systems",
      sender_address: "Mindspace Cyberabad, Building 9",
      recipient_name: "TechOps Datacenter",
      recipient_address: "Fab City, Raviryal, Ranga Reddy District",
      recipient_phone: "+91 99001 99002",
      postal_code: "501510",
      package_description: "Encrypted Hardware Security Modules (HSM)",
      weight_kg: 4.8,
      tier: "Same-Day Priority",
      declared_value: 5000,
      cost: 52.00,
      current_status: "Order Placed",
      created_at: "2026-10-05 13:00:00",
      updated_at: "2026-10-05 13:00:00",
      is_fragile: true,
      otp: "712893",
      timeline: [
        {
          status: "Order Placed",
          location: "Mindspace Logistics Desk",
          notes: "Order placed. Awaiting admin dispatch assignment to courier.",
          timestamp: "2026-10-05 13:00:00",
          updater: "Alice Vance",
          prev_hash: "0000000000000000000000000000000000000000000000000000000000000000",
          record_hash: "ff6600112233445566778899aabbccddeeff0011223344556677889900112233"
        }
      ]
    },
    {
      id: 106,
      tracking_number: "ST-20261005-662914",
      customer_id: 6,
      customer_name: "Dr. Arvind Swamy",
      assigned_delivery_id: null,
      driver_name: null,
      driver_phone: null,
      driver_avatar: null,
      sender_name: "BioGen Research Labs",
      sender_address: "T-Hub Phase 2, Knowledge City, Hyderabad",
      recipient_name: "Clinical Testing Facility",
      recipient_address: "Sanath Nagar Industrial Area, Hyderabad",
      recipient_phone: "+91 91234 00998",
      postal_code: "500018",
      package_description: "Sterile Bio-Samples (Cryo Sealed)",
      weight_kg: 2.1,
      tier: "Express 1-2 Days",
      declared_value: 1800,
      cost: 26.00,
      current_status: "Order Placed",
      created_at: "2026-10-05 13:45:00",
      updated_at: "2026-10-05 13:45:00",
      is_fragile: true,
      otp: "449102",
      timeline: [
        {
          status: "Order Placed",
          location: "Knowledge City Intake Station",
          notes: "Priority cryo-specimen registered. Requires temperature-controlled dispatch.",
          timestamp: "2026-10-05 13:45:00",
          updater: "Dr. Arvind Swamy",
          prev_hash: "0000000000000000000000000000000000000000000000000000000000000000",
          record_hash: "00112233445566778899aabbccddeeff00112233445566778899001122334455"
        }
      ]
    }
  ],

  // Platform Security Events for Admin Telemetry
  securityEvents: [
    {
      id: 901,
      event_type: "REPLAY_ATTACK_DETECTED",
      user_id: null,
      ip: "198.51.100.44",
      path: "/api/tracking/live/tok_991823ab",
      details: "Replay attempt on burned 1-time tracking token for shipment 101. Token already consumed.",
      created_at: "2026-10-05 14:48:12"
    },
    {
      id: 902,
      event_type: "UNAUTHORIZED_SHIPMENT_ACCESS",
      user_id: 8,
      ip: "203.0.113.19",
      path: "/api/shipments/ST-20261005-481920",
      details: "Unauthorized inquiry by user 8 (customer) probing foreign tracking ST-20261005-481920 (BOLA blocked with 404).",
      created_at: "2026-10-05 14:12:05"
    },
    {
      id: 903,
      event_type: "ACCOUNT_LOCKOUT",
      user_id: null,
      ip: "192.0.2.88",
      path: "/api/auth/login",
      details: "Blocked login flood from IP 192.0.2.88 after 5 consecutive password failures (HTTP 429 lockout enforced).",
      created_at: "2026-10-05 13:58:30"
    },
    {
      id: 904,
      event_type: "SUSPICIOUS_INPUT",
      user_id: null,
      ip: "198.51.100.102",
      path: "/api/auth/register",
      details: "SQL meta-character pattern detected in username parameter: 'admin' OR '1'='1' (Sanitized and blocked).",
      created_at: "2026-10-05 12:20:19"
    },
    {
      id: 905,
      event_type: "FORBIDDEN_ACCESS",
      user_id: 1,
      ip: "127.0.0.1",
      path: "/api/admin/dashboard",
      details: "Role violation: user 1 with role 'customer' attempted access to admin endpoint.",
      created_at: "2026-10-05 11:05:40"
    }
  ],

  // AI Shipment Assistant Knowledge Base
  assistantQA: [
    {
      triggers: ["trk-1042", "where is", "track", "package", "status", "location", "st-20261005-481920"],
      answer: "I looked up your active package **ST-20261005-481920** (High-Value Titanium Swiss Watch). It is currently **Out for Delivery** in Madhapur Sector 12 with driver **Rajesh Kumar** (Courier Alpha). Estimated delivery is within the next 25 minutes! Would you like me to open the live GPS map?",
      packageChip: {
        tracking_number: "ST-20261005-481920",
        status: "Out for Delivery",
        driver: "Rajesh Kumar",
        eta: "25 mins"
      }
    },
    {
      triggers: ["how much", "cost", "price", "calculate", "5kg", "weight", "rate"],
      answer: "Shipping costs in ShipTrack are calculated dynamically based on weight and service tier:\n• **Standard (3-5 days):** Base $12.00 + $2.50/kg → ~$24.50 for 5kg\n• **Express (1-2 days):** Base $24.50 + $4.00/kg → ~$44.50 for 5kg\n• **Same-Day Priority:** Base $45.00 + $6.00/kg → ~$75.00 for 5kg\nYou can configure and preview this directly in the **Create Shipment** wizard!",
      packageChip: null
    },
    {
      triggers: ["update address", "change address", "delivery address", "wrong address"],
      answer: "Delivery addresses can be updated by the shipment creator as long as the status is **'Order Placed'** or **'Picked Up'**. Once a shipment is 'Out for Delivery', rerouting requires contacting dispatch or your assigned driver directly via the Driver Contact button.",
      packageChip: null
    },
    {
      triggers: ["1-time", "one time", "secure link", "token", "ephemeral", "hacker", "share link"],
      answer: "Our **Single-Use Ephemeral Tracking Link** allows you to securely share live GPS tracking for high-value cargo with your recipient. The link is cryptographically hashed with SHA-256 and **burns immediately upon the first view** (`is_used = 1`), preventing replay attacks and eavesdropping!",
      packageChip: null
    },
    {
      triggers: ["chain of custody", "cryptographic", "tamper", "verify", "blockchain", "hash"],
      answer: "ShipTrack maintains a mathematical **SHA-256 Chain of Custody** across all milestone status updates (`prev_hash` & `record_hash`). You can click the **'Verify Custody Chain'** button on any shipment to verify that zero tampering has occurred since genesis!",
      packageChip: null
    }
  ]
};
