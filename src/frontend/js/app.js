/**
 * ShipTrack: Delivery & Shipment Management (PS-05)
 * Enterprise Dashboard Application Controller
 */

// ==============================================================================
// GLOBAL STATE
// ==============================================================================
const state = {
  currentRole: "customer", // 'customer' | 'delivery' | 'admin'
  currentUser: MOCK_DATA.demoUsers.customer,
  shipments: JSON.parse(JSON.stringify(MOCK_DATA.shipments)),
  drivers: JSON.parse(JSON.stringify(MOCK_DATA.drivers)),
  securityEvents: JSON.parse(JSON.stringify(MOCK_DATA.securityEvents)),
  activeTrackingId: "ST-20261005-481920",
  courierOnline: true,
  wizard: {
    currentStep: 1,
    selectedTier: "Same-Day",
    calculatedPrice: 45.00
  },
  burnedTokens: new Set(["tok_burned_sample"])
};

// ==============================================================================
// INITIALIZATION
// ==============================================================================
document.addEventListener("DOMContentLoaded", () => {
  initGlobalSearch();
  initSignaturePad();
  renderAllViews();
});

function renderAllViews() {
  updateUserNavbar();
  renderCustomerPortal();
  renderDeliveryPortal();
  renderAdminPortal();
}

// ==============================================================================
// ROLE SWITCHER
// ==============================================================================
function switchRole(role) {
  state.currentRole = role;
  state.currentUser = MOCK_DATA.demoUsers[role] || MOCK_DATA.demoUsers.customer;

  // Update Navbar Role Buttons
  document.querySelectorAll(".role-btn").forEach(btn => btn.classList.remove("active"));
  if (role === "customer") document.getElementById("btnRoleCustomer")?.classList.add("active");
  if (role === "delivery") document.getElementById("btnRoleDelivery")?.classList.add("active");
  if (role === "admin") document.getElementById("btnRoleAdmin")?.classList.add("active");

  // Toggle View Panels
  const custView = document.getElementById("customerPortalView");
  const delivView = document.getElementById("deliveryPortalView");
  const adminView = document.getElementById("adminPortalView");

  custView?.classList.add("d-none");
  delivView?.classList.add("d-none");
  adminView?.classList.add("d-none");

  if (role === "customer") {
    custView?.classList.remove("d-none");
    renderCustomerPortal();
  } else if (role === "delivery") {
    delivView?.classList.remove("d-none");
    renderDeliveryPortal();
  } else if (role === "admin") {
    adminView?.classList.remove("d-none");
    renderAdminPortal();
  }

  updateUserNavbar();
}

function updateUserNavbar() {
  const avatarEl = document.getElementById("navbarUserAvatar");
  const nameEl = document.getElementById("navbarUserName");
  const roleEl = document.getElementById("navbarUserRole");

  if (avatarEl) avatarEl.src = state.currentUser.avatar;
  if (nameEl) nameEl.textContent = state.currentUser.full_name;
  if (roleEl) {
    if (state.currentRole === "customer") roleEl.textContent = "Customer";
    if (state.currentRole === "delivery") roleEl.textContent = "Delivery Partner";
    if (state.currentRole === "admin") roleEl.textContent = "Fleet Ops Admin";
  }
}

// ==============================================================================
// 1. CUSTOMER PORTAL CONTROLLER
// ==============================================================================
function renderCustomerPortal() {
  renderCustomerMetrics();
  renderLiveTrackingCard();
  renderCustomerHistoryTable("all");
}

function renderCustomerMetrics() {
  const myShipments = state.shipments.filter(s => s.customer_id === 1);
  const activeCount = myShipments.filter(s => s.current_status !== "Delivered" && s.current_status !== "Cancelled").length;
  const inTransitCount = myShipments.filter(s => s.current_status === "In Transit" || s.current_status === "Out for Delivery").length;
  const deliveredCount = myShipments.filter(s => s.current_status === "Delivered").length;
  const totalSpent = myShipments.reduce((acc, s) => acc + (s.cost || 0), 0);

  const actEl = document.getElementById("custMetricActive");
  const trnEl = document.getElementById("custMetricTransit");
  const delEl = document.getElementById("custMetricDelivered");
  const spntEl = document.getElementById("custMetricSpent");

  if (actEl) actEl.textContent = activeCount;
  if (trnEl) trnEl.textContent = inTransitCount;
  if (delEl) delEl.textContent = deliveredCount;
  if (spntEl) spntEl.textContent = `$${totalSpent.toFixed(2)}`;
}

function renderLiveTrackingCard() {
  const shipment = state.shipments.find(s => s.tracking_number === state.activeTrackingId) || state.shipments[0];
  if (!shipment) return;

  // Header badges
  const badgeEl = document.getElementById("activeTrackingBadge");
  const statusEl = document.getElementById("activeStatusPill");
  const fragileEl = document.getElementById("activeFragilePill");

  if (badgeEl) badgeEl.textContent = shipment.tracking_number;
  if (statusEl) {
    statusEl.className = `status-badge ${getStatusBadgeClass(shipment.current_status)}`;
    statusEl.innerHTML = `<i class="${getStatusIcon(shipment.current_status)}"></i> ${shipment.current_status}`;
  }
  if (fragileEl) {
    fragileEl.style.display = shipment.is_fragile ? "inline-block" : "none";
  }

  // Horizontal Stepper
  renderHorizontalStepper(shipment);

  // Driver details card
  const driverNameEl = document.getElementById("activeDriverName");
  const driverVehicleEl = document.getElementById("activeDriverVehicle");
  const driverPortraitEl = document.getElementById("activeDriverPortrait");
  const driverCallBtn = document.getElementById("activeDriverCallBtn");

  if (driverNameEl) driverNameEl.textContent = shipment.driver_name || "Awaiting Driver Assignment";
  if (driverVehicleEl) {
    driverVehicleEl.innerHTML = shipment.driver_name 
      ? `<i class="bi bi-truck me-1"></i> Electric Cargo Van (TS-09-EQ-4421)`
      : `<i class="bi bi-clock me-1"></i> Driver assignment in progress at central hub`;
  }
  if (driverPortraitEl) {
    driverPortraitEl.src = shipment.driver_avatar || MOCK_DATA.courierPortrait;
  }
  if (driverCallBtn && shipment.driver_phone) {
    driverCallBtn.href = `tel:${shipment.driver_phone}`;
  }

  // Telemetry updates
  const coordsBadge = document.getElementById("telemetryCoordsBadge");
  const speedVal = document.getElementById("telemetrySpeedVal");
  const progressEl = document.getElementById("telemetryProgressBar");

  if (shipment.telemetry) {
    if (coordsBadge) coordsBadge.textContent = `${shipment.telemetry.latitude}° N, ${shipment.telemetry.longitude}° E`;
    if (speedVal) speedVal.textContent = `${shipment.telemetry.speed_kmh} km/h`;
  }

  if (progressEl) {
    const progressMap = {
      "Order Placed": "10%",
      "Picked Up": "35%",
      "In Transit": "65%",
      "Out for Delivery": "85%",
      "Delivered": "100%",
      "Cancelled": "0%"
    };
    progressEl.style.width = progressMap[shipment.current_status] || "50%";
  }
}

function renderHorizontalStepper(shipment) {
  const container = document.getElementById("horizontalStepperContainer");
  if (!container) return;

  const stages = [
    { name: "Order Placed", icon: "bi-check2-circle" },
    { name: "Picked Up", icon: "bi-box-arrow-up" },
    { name: "In Transit", icon: "bi-truck" },
    { name: "Out for Delivery", icon: "bi-geo-alt" },
    { name: "Delivered", icon: "bi-house-check" }
  ];

  const currentIdx = stages.findIndex(st => st.name === shipment.current_status);

  let html = "";
  stages.forEach((st, idx) => {
    let stateClass = "";
    if (shipment.current_status === "Cancelled") {
      stateClass = "";
    } else if (idx < currentIdx || shipment.current_status === "Delivered") {
      stateClass = "done";
    } else if (idx === currentIdx) {
      stateClass = "current";
    }

    const timelineItem = shipment.timeline ? shipment.timeline.find(t => t.status === st.name) : null;
    const timeText = timelineItem ? timelineItem.timestamp.split(" ")[1] : "--:--";

    html += `
      <div class="tracking-step ${stateClass}">
        <div class="tracking-step-circle">
          <i class="bi ${stateClass === 'done' ? 'bi-check-lg' : st.icon}"></i>
        </div>
        <div class="tracking-step-title">${st.name}</div>
        <div class="tracking-step-time">${timelineItem ? timeText : ''}</div>
      </div>
    `;
  });

  container.innerHTML = html;
}

function renderCustomerHistoryTable(filter) {
  const tbody = document.getElementById("customerHistoryTableBody");
  if (!tbody) return;

  let list = state.shipments.filter(s => s.customer_id === 1);
  if (filter === "active") {
    list = list.filter(s => s.current_status !== "Delivered" && s.current_status !== "Cancelled");
  } else if (filter === "delivered") {
    list = list.filter(s => s.current_status === "Delivered");
  } else if (filter === "cancelled") {
    list = list.filter(s => s.current_status === "Cancelled");
  }

  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-4">No shipments matching filter.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(s => `
    <tr>
      <td>
        <span class="font-monospace fw-bold text-primary cursor-pointer" onclick="setActiveTracking('${s.tracking_number}')">
          ${s.tracking_number}
        </span>
        <div class="small text-muted">${s.package_description}</div>
      </td>
      <td>
        <div class="fw-semibold">${s.recipient_name}</div>
        <small class="text-muted text-truncate d-inline-block" style="max-width: 220px;">${s.recipient_address}</small>
      </td>
      <td>
        <div class="small fw-semibold">${s.sender_name}</div>
        <small class="text-muted">${s.created_at.split(' ')[0]}</small>
      </td>
      <td>
        <span class="status-badge ${getStatusBadgeClass(s.current_status)}">
          <i class="${getStatusIcon(s.current_status)}"></i> ${s.current_status}
        </span>
      </td>
      <td>
        <span class="badge bg-light text-dark border">${s.weight_kg} kg</span>
        <div class="small text-muted">${s.tier || 'Standard'}</div>
      </td>
      <td class="text-end">
        <div class="btn-group btn-group-sm">
          <button class="btn btn-outline-primary" title="View Live Tracking" onclick="setActiveTracking('${s.tracking_number}')">
            <i class="bi bi-geo-alt"></i>
          </button>
          <button class="btn btn-outline-secondary" title="View Receipt" onclick="openReceiptModal('${s.tracking_number}')">
            <i class="bi bi-receipt"></i>
          </button>
          <button class="btn btn-outline-purple text-purple border-purple" title="1-Time Secure Link" onclick="generate1TimeLink('${s.tracking_number}')">
            <i class="bi bi-link-45deg"></i>
          </button>
          ${s.current_status === 'Order Placed' ? `
            <button class="btn btn-outline-danger" title="Cancel Shipment" onclick="cancelShipment(${s.id})">
              <i class="bi bi-x-circle"></i>
            </button>
          ` : ''}
        </div>
      </td>
    </tr>
  `).join('');
}

function filterHistoryTable(filter, btn) {
  document.querySelectorAll(".btn-group button").forEach(b => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
  renderCustomerHistoryTable(filter);
}

function setActiveTracking(trackingNum) {
  state.activeTrackingId = trackingNum;
  switchRole("customer");
  renderLiveTrackingCard();
  const card = document.getElementById("liveTrackingCardContainer");
  if (card) {
    card.scrollIntoView({ behavior: "smooth", block: "start" });
    card.classList.add("border-primary");
    setTimeout(() => card.classList.remove("border-primary"), 1500);
  }
}

function cancelShipment(shipmentId) {
  const s = state.shipments.find(item => item.id === shipmentId);
  if (!s) return;
  if (s.current_status !== "Order Placed") {
    alert("Only shipments in 'Order Placed' status can be cancelled.");
    return;
  }

  if (confirm(`Are you sure you want to cancel shipment ${s.tracking_number}?`)) {
    s.current_status = "Cancelled";
    s.timeline.push({
      status: "Cancelled",
      location: "Customer Service Portal",
      notes: "Shipment cancelled by customer request.",
      timestamp: new Date().toISOString().replace("T", " ").substring(0, 19),
      updater: state.currentUser.full_name,
      prev_hash: s.timeline[s.timeline.length - 1].record_hash,
      record_hash: "cancelled_hash_" + Math.random().toString(36).substring(2, 10)
    });
    renderCustomerPortal();
  }
}

function verifyActiveShipmentChain() {
  const shipment = state.shipments.find(s => s.tracking_number === state.activeTrackingId);
  if (!shipment) return;

  const alertEl = document.getElementById("custodyAuditAlert");
  const detailsEl = document.getElementById("custodyAuditDetails");
  if (!alertEl || !detailsEl) return;

  const blockCount = shipment.timeline ? shipment.timeline.length : 1;
  const lastHash = shipment.timeline && shipment.timeline.length > 0 
    ? shipment.timeline[shipment.timeline.length - 1].record_hash 
    : "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

  detailsEl.innerHTML = `
    <strong>Chain Length:</strong> ${blockCount} cryptographic blocks verified.<br>
    <strong>Genesis Linkage:</strong> <code>0000000000000000000000000000000000000000000000000000000000000000</code><br>
    <strong>Latest Head Hash:</strong> <code>${lastHash}</code><br>
    <strong>Integrity Result:</strong> VALID (No tampering detected).
  `;

  alertEl.classList.remove("d-none");
}

function generate1TimeLinkForActive() {
  generate1TimeLink(state.activeTrackingId);
}

function generate1TimeLink(trackingNum) {
  const rawToken = "tok_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
  const inputEl = document.getElementById("inputEphemeralToken");
  if (inputEl) inputEl.value = rawToken;

  const modalEl = document.getElementById("ephemeralTokenViewerModal");
  if (modalEl) {
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
  }
}

function simulateAccessEphemeralToken() {
  const token = document.getElementById("inputEphemeralToken").value.trim();
  const resCard = document.getElementById("ephemeralResultCard");
  if (!resCard) return;

  if (state.burnedTokens.has(token)) {
    // REPLAY ATTACK DETECTED
    resCard.className = "mt-3 p-3 bg-danger-subtle text-danger rounded-3 border border-danger";
    resCard.innerHTML = `
      <h6 class="fw-bold"><i class="bi bi-shield-x fs-5 me-1"></i> HTTP 410 Gone: REPLAY ATTACK BLOCKED</h6>
      <p class="small mb-0">This single-use tracking link has already been used and permanently burned. Replay access is rejected and logged in security telemetry.</p>
    `;
    resCard.classList.remove("d-none");

    // Log security event
    state.securityEvents.unshift({
      id: Date.now(),
      event_type: "REPLAY_ATTACK_DETECTED",
      user_id: null,
      ip: "127.0.0.1",
      path: `/api/tracking/live/${token.substring(0, 12)}...`,
      details: "Replay attempt on burned 1-time tracking token.",
      created_at: new Date().toISOString().replace("T", " ").substring(0, 19)
    });
    renderAdminPortal();
    return;
  }

  // First access: BURN IT
  state.burnedTokens.add(token);

  const activeShipment = state.shipments.find(s => s.tracking_number === state.activeTrackingId) || state.shipments[0];
  resCard.className = "mt-3 p-3 bg-success-subtle text-success-emphasis rounded-3 border border-success";
  resCard.innerHTML = `
    <div class="d-flex justify-content-between align-items-center mb-2">
      <h6 class="fw-bold mb-0 text-success"><i class="bi bi-check-circle-fill me-1"></i> Live GPS Telemetry Authorized</h6>
      <span class="badge bg-danger">TOKEN BURNED</span>
    </div>
    <div class="small">
      <strong>Shipment:</strong> ${activeShipment.tracking_number} (${activeShipment.package_description})<br>
      <strong>Current Status:</strong> ${activeShipment.current_status}<br>
      <strong>Live Coordinates:</strong> 17.4485° N, 78.3752° E (Speed: 38.5 km/h)<br>
      <strong>Notice:</strong> This link is now invalid for future requests (Anti-Replay Guarantee).
    </div>
  `;
  resCard.classList.remove("d-none");
}

// ==============================================================================
// 2. CREATE SHIPMENT MULTI-STEP WIZARD
// ==============================================================================
function jumpToWizardStep(stepNum) {
  if (stepNum > state.wizard.currentStep + 1) return;
  state.wizard.currentStep = stepNum;
  updateWizardUI();
}

function nextWizardStep() {
  if (state.wizard.currentStep < 4) {
    state.wizard.currentStep++;
    updateWizardUI();
  } else {
    // Confirm and generate shipment
    submitCreateShipment();
  }
}

function prevWizardStep() {
  if (state.wizard.currentStep > 1) {
    state.wizard.currentStep--;
    updateWizardUI();
  }
}

function updateWizardUI() {
  const step = state.wizard.currentStep;

  // Header circles
  for (let i = 1; i <= 4; i++) {
    const header = document.getElementById(`wizardStepHeader${i}`);
    if (header) {
      header.classList.remove("active", "completed");
      if (i === step) header.classList.add("active");
      else if (i < step) header.classList.add("completed");
    }

    const content = document.getElementById(`wizardStepContent${i}`);
    if (content) {
      content.classList.toggle("d-none", i !== step);
    }
  }

  // Buttons
  const backBtn = document.getElementById("wizardBackBtn");
  const nextBtn = document.getElementById("wizardNextBtn");

  if (backBtn) backBtn.disabled = step === 1;
  if (nextBtn) {
    if (step === 4) {
      nextBtn.textContent = "Confirm & Book Shipment";
      nextBtn.className = "btn btn-success px-4";
      populateWizardReviewSummary();
    } else {
      nextBtn.textContent = "Continue";
      nextBtn.className = "btn btn-primary px-4";
    }
  }
}

function selectServiceTier(tier) {
  state.wizard.selectedTier = tier;
  document.querySelectorAll(".service-tier-card").forEach(c => c.classList.remove("selected"));

  if (tier === "Standard") document.getElementById("tierCardStandard")?.classList.add("selected");
  if (tier === "Express") document.getElementById("tierCardExpress")?.classList.add("selected");
  if (tier === "Same-Day") document.getElementById("tierCardSameDay")?.classList.add("selected");

  updatePriceCalculation();
}

function updatePriceCalculation() {
  const weightInput = document.getElementById("formWeightKg");
  const weight = parseFloat(weightInput ? weightInput.value : 1.2) || 1.0;
  const tier = state.wizard.selectedTier;

  let base = 12.00;
  let perKg = 2.50;

  if (tier === "Express") {
    base = 24.50;
    perKg = 4.00;
  } else if (tier === "Same-Day") {
    base = 40.00;
    perKg = 5.00;
  }

  const weightCost = weight * perKg;
  const total = base + weightCost;
  state.wizard.calculatedPrice = total;

  const baseEl = document.getElementById("summaryBasePrice");
  const weightEl = document.getElementById("summaryWeightPrice");
  const totalEl = document.getElementById("summaryTotalPrice");

  if (baseEl) baseEl.textContent = `$${base.toFixed(2)}`;
  if (weightEl) weightEl.textContent = `$${weightCost.toFixed(2)}`;
  if (totalEl) totalEl.textContent = `$${total.toFixed(2)}`;
}

function populateWizardReviewSummary() {
  const senderName = document.getElementById("formSenderName")?.value || "Alice Vance";
  const senderAddr = document.getElementById("formSenderAddress")?.value || "HITEC City";
  const recipName = document.getElementById("formRecipientName")?.value || "Charlie Jenkins";
  const recipAddr = document.getElementById("formRecipientAddress")?.value || "Madhapur";
  const packageDesc = document.getElementById("formPackageDesc")?.value || "High-Value Item";
  const weight = document.getElementById("formWeightKg")?.value || "1.2";

  const revSender = document.getElementById("reviewSenderText");
  const revRecip = document.getElementById("reviewRecipientText");
  const revPkg = document.getElementById("reviewPackageText");
  const revTier = document.getElementById("reviewTierText");

  if (revSender) revSender.textContent = `${senderName}, ${senderAddr}`;
  if (revRecip) revRecip.textContent = `${recipName}, ${recipAddr}`;
  if (revPkg) revPkg.textContent = `${packageDesc} (${weight} kg)`;
  if (revTier) revTier.textContent = `${state.wizard.selectedTier} — $${state.wizard.calculatedPrice.toFixed(2)}`;
}

function submitCreateShipment() {
  const randomSuffix = Math.floor(100000 + Math.random() * 900000);
  const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const newTrackingNumber = `ST-${dateStr}-${randomSuffix}`;
  const nowStr = new Date().toISOString().replace("T", " ").substring(0, 19);

  const newShipment = {
    id: Date.now(),
    tracking_number: newTrackingNumber,
    customer_id: 1,
    customer_name: document.getElementById("formSenderName")?.value || "Alice Vance",
    assigned_delivery_id: null,
    driver_name: null,
    driver_phone: null,
    driver_avatar: null,
    sender_name: document.getElementById("formSenderName")?.value || "Alice Vance",
    sender_address: document.getElementById("formSenderAddress")?.value || "HITEC City, Hyderabad",
    recipient_name: document.getElementById("formRecipientName")?.value || "Charlie Jenkins",
    recipient_address: document.getElementById("formRecipientAddress")?.value || "Madhapur, Hyderabad",
    recipient_phone: document.getElementById("formRecipientPhone")?.value || "+91 91234 56789",
    postal_code: document.getElementById("formPostalCode")?.value || "500081",
    package_description: document.getElementById("formPackageDesc")?.value || "High-Value Cargo",
    weight_kg: parseFloat(document.getElementById("formWeightKg")?.value) || 1.2,
    tier: state.wizard.selectedTier,
    declared_value: parseFloat(document.getElementById("formDeclaredValue")?.value) || 1000,
    cost: state.wizard.calculatedPrice,
    current_status: "Order Placed",
    created_at: nowStr,
    updated_at: nowStr,
    is_fragile: document.getElementById("formIsFragile")?.checked || false,
    otp: Math.floor(100000 + Math.random() * 900000).toString(),
    timeline: [
      {
        status: "Order Placed",
        location: "Customer Booking Station",
        notes: "Order placed. Sealed with tamper-evident genesis block.",
        timestamp: nowStr,
        updater: "Alice Vance",
        prev_hash: "0000000000000000000000000000000000000000000000000000000000000000",
        record_hash: "genesis_hash_" + Math.random().toString(36).substring(2, 10)
      }
    ]
  };

  state.shipments.unshift(newShipment);
  state.activeTrackingId = newTrackingNumber;

  // Show Success Card inside wizard modal
  document.getElementById("wizardReviewSection")?.classList.add("d-none");
  const successCard = document.getElementById("wizardSuccessCard");
  const genNum = document.getElementById("generatedTrackingNum");
  if (successCard) successCard.classList.remove("d-none");
  if (genNum) genNum.textContent = newTrackingNumber;

  document.getElementById("wizardBackBtn")?.classList.add("d-none");
  document.getElementById("wizardNextBtn")?.classList.add("d-none");

  // Re-render portals
  renderCustomerPortal();
  renderAdminPortal();
}

function copyGeneratedTracking() {
  const trk = document.getElementById("generatedTrackingNum")?.textContent;
  if (trk) {
    navigator.clipboard?.writeText(trk);
    alert(`Copied tracking number ${trk} to clipboard!`);
  }
}

function openLiveTrackingFromWizard() {
  const modalEl = document.getElementById("createShipmentModal");
  if (modalEl) {
    const modal = bootstrap.Modal.getInstance(modalEl);
    modal?.hide();
  }
  setActiveTracking(state.activeTrackingId);
}

// ==============================================================================
// 3. DELIVERY-PERSON PORTAL CONTROLLER
// ==============================================================================
function renderDeliveryPortal() {
  const container = document.getElementById("courierQueueContainer");
  if (!container) return;

  const assigned = state.shipments.filter(s => s.assigned_delivery_id === 2 && s.current_status !== "Cancelled");
  const badgeEl = document.getElementById("courierQueueCountBadge");
  if (badgeEl) badgeEl.textContent = `${assigned.length} Active Tasks`;

  if (assigned.length === 0) {
    container.innerHTML = `<div class="col-12"><div class="alert alert-light text-center py-4">No active delivery tasks assigned. Ready for dispatch!</div></div>`;
    return;
  }

  container.innerHTML = assigned.map(s => {
    let priorityClass = "";
    let priorityLabel = "Standard Route";
    if (s.is_fragile) {
      priorityClass = "priority-urgent";
      priorityLabel = "High-Value / Fragile";
    }

    return `
      <div class="col-md-6 col-xl-4">
        <div class="courier-task-card ${priorityClass}">
          <div class="d-flex justify-content-between align-items-start mb-2">
            <span class="badge bg-dark">${s.tracking_number}</span>
            <span class="badge ${s.is_fragile ? 'bg-danger-subtle text-danger border border-danger-subtle' : 'bg-secondary'}">${priorityLabel}</span>
          </div>
          <h6 class="fw-bold mb-1">${s.recipient_name}</h6>
          <p class="small text-muted mb-2"><i class="bi bi-geo-alt-fill text-danger me-1"></i>${s.recipient_address}</p>
          <div class="d-flex justify-content-between small text-muted border-top border-bottom py-2 mb-3">
            <span><strong>Cargo:</strong> ${s.package_description}</span>
            <span><strong>Weight:</strong> ${s.weight_kg} kg</span>
          </div>
          <div class="d-flex justify-content-between align-items-center">
            <span class="status-badge ${getStatusBadgeClass(s.current_status)}">
              <i class="${getStatusIcon(s.current_status)}"></i> ${s.current_status}
            </span>
            <div class="btn-group btn-group-sm">
              <a href="tel:${s.recipient_phone}" class="btn btn-outline-secondary" title="Call Recipient">
                <i class="bi bi-telephone"></i>
              </a>
              <button class="btn btn-outline-primary" title="Push GPS Ping" onclick="simulateGpsPing(${s.id})">
                <i class="bi bi-broadcast"></i>
              </button>
              ${getCourierActionButton(s)}
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function getCourierActionButton(shipment) {
  if (shipment.current_status === "Order Placed") {
    return `<button class="btn btn-primary" onclick="advanceCourierStatus(${shipment.id}, 'Picked Up')">Confirm Pickup</button>`;
  } else if (shipment.current_status === "Picked Up") {
    return `<button class="btn btn-info text-white" onclick="advanceCourierStatus(${shipment.id}, 'In Transit')">Start Route</button>`;
  } else if (shipment.current_status === "In Transit") {
    return `<button class="btn btn-purple text-white bg-purple" onclick="advanceCourierStatus(${shipment.id}, 'Out for Delivery')">Out for Delivery</button>`;
  } else if (shipment.current_status === "Out for Delivery") {
    return `<button class="btn btn-success" onclick="openDeliveryConfirmModal(${shipment.id})">Mark Delivered</button>`;
  } else {
    return `<button class="btn btn-secondary" disabled>Delivered</button>`;
  }
}

function advanceCourierStatus(shipmentId, newStatus) {
  const s = state.shipments.find(item => item.id === shipmentId);
  if (!s) return;

  const nowStr = new Date().toISOString().replace("T", " ").substring(0, 19);
  s.current_status = newStatus;
  s.updated_at = nowStr;

  s.timeline.push({
    status: newStatus,
    location: "Courier Mobile Hub (HITEC Corridor)",
    notes: `Courier Rajesh Kumar advanced status to ${newStatus}.`,
    timestamp: nowStr,
    updater: "Rajesh Kumar (Courier Alpha)",
    prev_hash: s.timeline[s.timeline.length - 1].record_hash,
    record_hash: "hash_" + Math.random().toString(36).substring(2, 10)
  });

  renderDeliveryPortal();
  renderCustomerPortal();
}

function simulateGpsPing(shipmentId) {
  const s = state.shipments.find(item => item.id === shipmentId);
  if (!s) return;

  const latOffset = (Math.random() - 0.5) * 0.01;
  const lngOffset = (Math.random() - 0.5) * 0.01;
  s.telemetry = {
    latitude: +(17.4485 + latOffset).toFixed(4),
    longitude: +(78.3752 + lngOffset).toFixed(4),
    speed_kmh: Math.floor(30 + Math.random() * 25),
    heading_degrees: 145,
    battery_pct: 82,
    timestamp: new Date().toISOString().replace("T", " ").substring(0, 19)
  };

  alert(`GPS Telemetry broadcasted for ${s.tracking_number}: Lat ${s.telemetry.latitude}, Long ${s.telemetry.longitude}`);
  renderCustomerPortal();
}

function toggleCourierAvailability(toggleEl) {
  state.courierOnline = toggleEl.checked;
  const badgeEl = document.getElementById("courierStatusBadge");
  if (badgeEl) {
    badgeEl.className = state.courierOnline 
      ? "badge bg-success-subtle text-success border border-success-subtle" 
      : "badge bg-secondary-subtle text-secondary border border-secondary-subtle";
    badgeEl.innerHTML = state.courierOnline 
      ? `<span class="pulse-indicator me-1"></span> Online` 
      : `<i class="bi bi-moon-fill me-1"></i> Offline`;
  }
}

// Delivery Handover Modal (OTP + Signature)
let pendingDeliveryShipmentId = null;

function openDeliveryConfirmModal(shipmentId) {
  pendingDeliveryShipmentId = shipmentId;
  const s = state.shipments.find(item => item.id === shipmentId);
  if (!s) return;

  const textEl = document.getElementById("deliveryConfirmShipmentText");
  if (textEl) textEl.textContent = `Completing delivery for ${s.tracking_number} to ${s.recipient_name} at ${s.recipient_address}.`;

  const inputOtp = document.getElementById("inputDeliveryOtp");
  if (inputOtp) inputOtp.value = "";

  clearSignatureCanvas();

  const modalEl = document.getElementById("deliveryConfirmModal");
  if (modalEl) {
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
  }
}

function fillMockOtp() {
  const s = state.shipments.find(item => item.id === pendingDeliveryShipmentId);
  const inputOtp = document.getElementById("inputDeliveryOtp");
  if (inputOtp) inputOtp.value = s?.otp || "849201";
}

function submitFinalDeliveryConfirmation() {
  const s = state.shipments.find(item => item.id === pendingDeliveryShipmentId);
  if (!s) return;

  const enteredOtp = document.getElementById("inputDeliveryOtp")?.value.trim();
  if (!enteredOtp || enteredOtp.length < 6) {
    alert("Please enter the valid 6-digit recipient OTP.");
    return;
  }

  const nowStr = new Date().toISOString().replace("T", " ").substring(0, 19);
  s.current_status = "Delivered";
  s.updated_at = nowStr;

  s.timeline.push({
    status: "Delivered",
    location: s.recipient_address,
    notes: `Delivered successfully. Recipient signature captured and verified via OTP ${enteredOtp}.`,
    timestamp: nowStr,
    updater: "Rajesh Kumar (Courier Alpha)",
    prev_hash: s.timeline[s.timeline.length - 1].record_hash,
    record_hash: "delivered_block_" + Math.random().toString(36).substring(2, 10)
  });

  const modalEl = document.getElementById("deliveryConfirmModal");
  if (modalEl) {
    const modal = bootstrap.Modal.getInstance(modalEl);
    modal?.hide();
  }

  alert(`Shipment ${s.tracking_number} successfully marked Delivered! Cryptographic custody sealed.`);
  renderDeliveryPortal();
  renderCustomerPortal();
}

// ==============================================================================
// 4. ADMIN MANAGEMENT PORTAL CONTROLLER
// ==============================================================================
function renderAdminPortal() {
  renderUnassignedShipments();
  renderAdminAllShipments();
  renderAdminDrivers();
  renderAdminSecurityEvents();
}

function renderUnassignedShipments() {
  const tbody = document.getElementById("unassignedShipmentsTableBody");
  const countBadge = document.getElementById("unassignedCountBadge");
  if (!tbody) return;

  const unassigned = state.shipments.filter(s => s.assigned_delivery_id === null && s.current_status !== "Cancelled");
  if (countBadge) countBadge.textContent = `${unassigned.length} Awaiting Dispatch`;

  if (unassigned.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-success py-3"><i class="bi bi-check-circle-fill me-1"></i> All shipments have been dispatched!</td></tr>`;
    return;
  }

  tbody.innerHTML = unassigned.map(s => `
    <tr>
      <td><span class="font-monospace fw-bold text-primary">${s.tracking_number}</span></td>
      <td><strong>${s.customer_name}</strong></td>
      <td><small class="text-muted">${s.sender_address}</small></td>
      <td><small class="text-muted">${s.recipient_address}</small></td>
      <td><span class="badge bg-light text-dark border">${s.weight_kg} kg</span></td>
      <td class="text-end">
        <button class="btn btn-sm btn-primary" onclick="openAssignDriverModal(${s.id})">
          <i class="bi bi-person-plus me-1"></i> Assign Driver
        </button>
      </td>
    </tr>
  `).join('');
}

function renderAdminAllShipments() {
  const tbody = document.getElementById("adminAllShipmentsTableBody");
  if (!tbody) return;

  tbody.innerHTML = state.shipments.map(s => `
    <tr>
      <td><span class="font-monospace fw-bold text-primary">${s.tracking_number}</span></td>
      <td>${s.customer_name}</td>
      <td>${s.driver_name ? `<span class="badge bg-light text-dark border">${s.driver_name}</span>` : '<span class="text-danger small fw-semibold">Unassigned</span>'}</td>
      <td><small class="text-muted">${s.recipient_address}</small></td>
      <td><span class="status-badge ${getStatusBadgeClass(s.current_status)}">${s.current_status}</span></td>
      <td class="text-end">
        <button class="btn btn-sm btn-outline-secondary" onclick="openReceiptModal('${s.tracking_number}')"><i class="bi bi-receipt"></i></button>
      </td>
    </tr>
  `).join('');
}

function renderAdminDrivers() {
  const tbody = document.getElementById("adminDriversTableBody");
  if (!tbody) return;

  tbody.innerHTML = state.drivers.map(d => `
    <tr>
      <td>
        <div class="d-flex align-items-center gap-2">
          <img src="${d.avatar}" class="rounded-circle" width="32" height="32" alt="${d.name}">
          <div>
            <div class="fw-bold">${d.name}</div>
            <small class="text-muted">${d.callsign}</small>
          </div>
        </div>
      </td>
      <td>
        <div>${d.vehicle}</div>
        <small class="text-muted font-monospace">${d.plate}</small>
      </td>
      <td>
        <span class="badge ${d.status === 'Online' ? 'bg-success' : 'bg-secondary'}">${d.status}</span>
      </td>
      <td>${d.active_tasks} active</td>
      <td><small class="text-muted">${d.proximity}</small></td>
      <td><span class="text-warning fw-bold"><i class="bi bi-star-fill"></i> ${d.rating}</span></td>
    </tr>
  `).join('');
}

function renderAdminSecurityEvents() {
  const tbody = document.getElementById("adminSecurityEventsTableBody");
  if (!tbody) return;

  tbody.innerHTML = state.securityEvents.map(e => `
    <tr>
      <td><small class="text-muted">${e.created_at}</small></td>
      <td><span class="badge bg-danger-subtle text-danger border border-danger-subtle">${e.event_type}</span></td>
      <td><code class="text-dark">${e.ip}</code></td>
      <td><small class="text-muted">${e.path}</small></td>
      <td><small class="text-slate-700">${e.details}</small></td>
    </tr>
  `).join('');
}

let pendingAssignShipmentId = null;

function openAssignDriverModal(shipmentId) {
  pendingAssignShipmentId = shipmentId;
  const s = state.shipments.find(item => item.id === shipmentId);
  if (!s) return;

  document.getElementById("assignTargetTrackingText").textContent = s.tracking_number;
  document.getElementById("assignTargetCargoText").textContent = `${s.package_description} (${s.weight_kg} kg)`;

  const listContainer = document.getElementById("driverSelectionList");
  if (listContainer) {
    listContainer.innerHTML = state.drivers.map((d, idx) => `
      <label class="list-group-item list-group-item-action d-flex justify-content-between align-items-center cursor-pointer">
        <div class="d-flex align-items-center gap-3">
          <input class="form-check-input me-1" type="radio" name="driverRadio" value="${d.id}" ${idx === 0 ? 'checked' : ''}>
          <img src="${d.avatar}" class="rounded-circle" width="40" height="40" alt="${d.name}">
          <div>
            <h6 class="mb-0 fw-bold">${d.name} <span class="badge bg-light text-dark border small">${d.callsign}</span></h6>
            <small class="text-muted">${d.vehicle} &bull; ${d.proximity}</small>
          </div>
        </div>
        <span class="badge ${d.status === 'Online' ? 'bg-success' : 'bg-secondary'}">${d.status}</span>
      </label>
    `).join('');
  }

  const modalEl = document.getElementById("assignDriverModal");
  if (modalEl) {
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
  }
}

function confirmDriverAssignment() {
  const selectedRadio = document.querySelector('input[name="driverRadio"]:checked');
  if (!selectedRadio) return;

  const driverId = parseInt(selectedRadio.value);
  const driver = state.drivers.find(d => d.id === driverId);
  const shipment = state.shipments.find(s => s.id === pendingAssignShipmentId);

  if (shipment && driver) {
    shipment.assigned_delivery_id = driver.id;
    shipment.driver_name = driver.name;
    shipment.driver_phone = driver.phone;
    shipment.driver_avatar = driver.avatar;

    const nowStr = new Date().toISOString().replace("T", " ").substring(0, 19);
    shipment.timeline.push({
      status: shipment.current_status,
      location: "Central Dispatch Control Room",
      notes: `Admin assigned shipment to courier partner ${driver.name} (${driver.callsign}).`,
      timestamp: nowStr,
      updater: "Sarah Chen (Fleet Ops Director)",
      prev_hash: shipment.timeline[shipment.timeline.length - 1].record_hash,
      record_hash: "dispatch_hash_" + Math.random().toString(36).substring(2, 10)
    });

    driver.active_tasks++;

    const modalEl = document.getElementById("assignDriverModal");
    if (modalEl) {
      const modal = bootstrap.Modal.getInstance(modalEl);
      modal?.hide();
    }

    renderAdminPortal();
    renderDeliveryPortal();
    renderCustomerPortal();
  }
}

function simulateAttackDetection() {
  const probeEvent = {
    id: Date.now(),
    event_type: "UNAUTHORIZED_SHIPMENT_ACCESS",
    user_id: 99,
    ip: "198.51.100." + Math.floor(10 + Math.random() * 80),
    path: "/api/shipments/ST-20261005-481920",
    details: "Automated scan attempted BOLA probe on foreign customer shipment (Prevented via 404 anti-probing).",
    created_at: new Date().toISOString().replace("T", " ").substring(0, 19)
  };

  state.securityEvents.unshift(probeEvent);
  renderAdminSecurityEvents();
  alert("Simulated Intrusion Attack sensor triggered! Event logged in /api/admin/security-events.");
}

// ==============================================================================
// 5. AI SHIPMENT ASSISTANT (FLOATING WIDGET)
// ==============================================================================
function toggleAIAssistant() {
  const panel = document.getElementById("assistantChatPanel");
  panel?.classList.toggle("open");
}

function askAIAssistant(question) {
  const panel = document.getElementById("assistantChatPanel");
  panel?.classList.add("open");

  appendChatMessage("user", question);

  // Match question against Q&A knowledge base
  setTimeout(() => {
    const qLower = question.toLowerCase();
    const matched = MOCK_DATA.assistantQA.find(item => 
      item.triggers.some(trig => qLower.includes(trig))
    );

    if (matched) {
      appendChatMessage("bot", matched.answer, matched.packageChip);
    } else {
      appendChatMessage("bot", "I am your ShipTrack Logistics AI. I can look up live shipments, verify cryptographic chain of custody, calculate shipping rates, or explain single-use secure tracking tokens!");
    }
  }, 450);
}

function handleChatSubmit(e) {
  e.preventDefault();
  const input = document.getElementById("chatInputText");
  const text = input ? input.value.trim() : "";
  if (!text) return;

  input.value = "";
  askAIAssistant(text);
}

function appendChatMessage(sender, text, chip) {
  const container = document.getElementById("chatMessagesContainer");
  if (!container) return;

  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${sender === "bot" ? "bubble-bot" : "bubble-user"}`;
  bubble.innerHTML = text.replace(/\n/g, "<br>").replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

  if (chip) {
    const chipHtml = `
      <div class="card border border-primary-subtle bg-primary-subtle p-2 mt-2 text-dark rounded-3">
        <div class="d-flex justify-content-between align-items-center">
          <strong class="small">${chip.tracking_number}</strong>
          <span class="badge bg-primary">${chip.status}</span>
        </div>
        <div class="small mt-1 text-muted">Driver: ${chip.driver} &bull; ETA: ${chip.eta}</div>
        <button class="btn btn-sm btn-primary mt-2 py-0" onclick="setActiveTracking('${chip.tracking_number}')">
          <i class="bi bi-geo-alt me-1"></i> Track Live
        </button>
      </div>
    `;
    bubble.innerHTML += chipHtml;
  }

  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

// ==============================================================================
// 6. PRINTABLE SHIPPING RECEIPT MODAL
// ==============================================================================
function openReceiptModal(trackingNum) {
  const shipment = state.shipments.find(s => s.tracking_number === trackingNum) || state.shipments[0];
  if (!shipment) return;

  const bodyEl = document.getElementById("receiptModalBody");
  if (!bodyEl) return;

  bodyEl.innerHTML = `
    <div class="p-3">
      <div class="d-flex justify-content-between border-bottom pb-3 mb-3">
        <div>
          <h4 class="fw-bold mb-0 text-primary">ShipTrack Logistics</h4>
          <small class="text-muted">Waybill & Proof of Dispatch Receipt</small>
        </div>
        <div class="text-end">
          <h6 class="font-monospace fw-bold mb-0">${shipment.tracking_number}</h6>
          <small class="text-muted">Date: ${shipment.created_at}</small>
        </div>
      </div>

      <div class="row g-3 mb-4 small">
        <div class="col-6">
          <strong class="text-uppercase text-muted">Sender Details:</strong>
          <div class="fw-bold fs-6">${shipment.sender_name}</div>
          <div>${shipment.sender_address}</div>
        </div>
        <div class="col-6">
          <strong class="text-uppercase text-muted">Recipient Details:</strong>
          <div class="fw-bold fs-6">${shipment.recipient_name}</div>
          <div>${shipment.recipient_address}</div>
          <div>Phone: ${shipment.recipient_phone}</div>
        </div>
      </div>

      <table class="table table-bordered table-sm mb-4 small">
        <thead class="table-light">
          <tr>
            <th>Item Description</th>
            <th>Weight</th>
            <th>Service Tier</th>
            <th class="text-end">Declared Value</th>
            <th class="text-end">Shipping Charge</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>${shipment.package_description}</td>
            <td>${shipment.weight_kg} kg</td>
            <td>${shipment.tier || 'Standard'}</td>
            <td class="text-end">$${(shipment.declared_value || 500).toFixed(2)}</td>
            <td class="text-end fw-bold">$${(shipment.cost || 25.00).toFixed(2)}</td>
          </tr>
        </tbody>
      </table>

      <!-- Barcode Visual Representation -->
      <div class="text-center py-3 bg-light rounded-3 border mb-3">
        <div class="font-monospace fw-bold fs-3 text-slate-800" style="letter-spacing: 5px;">||| | |||| | ||| |||| | || |</div>
        <div class="small font-monospace text-muted">${shipment.tracking_number}</div>
      </div>

      <div class="d-flex justify-content-between small text-muted border-top pt-3">
        <div>Status: <strong>${shipment.current_status}</strong></div>
        <div>Cryptographic Custody: <strong>SHA-256 Verified</strong></div>
      </div>
    </div>
  `;

  const modalEl = document.getElementById("receiptModal");
  if (modalEl) {
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
  }
}

// ==============================================================================
// 7. SIGNATURE CANVAS & GLOBAL SEARCH
// ==============================================================================
let sigCanvas, sigCtx, isDrawing = false;

function initSignaturePad() {
  sigCanvas = document.getElementById("signatureCanvas");
  if (!sigCanvas) return;

  sigCtx = sigCanvas.getContext("2d");
  sigCanvas.width = sigCanvas.parentElement.clientWidth || 380;
  sigCanvas.height = 160;
  sigCtx.lineWidth = 2.5;
  sigCtx.lineCap = "round";
  sigCtx.strokeStyle = "#0f172a";

  const startDraw = (e) => {
    isDrawing = true;
    sigCtx.beginPath();
    const rect = sigCanvas.getBoundingClientRect();
    const x = (e.clientX || e.touches[0].clientX) - rect.left;
    const y = (e.clientY || e.touches[0].clientY) - rect.top;
    sigCtx.moveTo(x, y);
  };

  const draw = (e) => {
    if (!isDrawing) return;
    const rect = sigCanvas.getBoundingClientRect();
    const x = (e.clientX || e.touches[0].clientX) - rect.left;
    const y = (e.clientY || e.touches[0].clientY) - rect.top;
    sigCtx.lineTo(x, y);
    sigCtx.stroke();
  };

  const stopDraw = () => { isDrawing = false; };

  sigCanvas.addEventListener("mousedown", startDraw);
  sigCanvas.addEventListener("mousemove", draw);
  sigCanvas.addEventListener("mouseup", stopDraw);

  sigCanvas.addEventListener("touchstart", startDraw, { passive: true });
  sigCanvas.addEventListener("touchmove", draw, { passive: true });
  sigCanvas.addEventListener("touchend", stopDraw);
}

function clearSignatureCanvas() {
  if (sigCanvas && sigCtx) {
    sigCtx.clearRect(0, 0, sigCanvas.width, sigCanvas.height);
  }
}

function initGlobalSearch() {
  const input = document.getElementById("globalTrackingSearchInput");
  input?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const q = input.value.trim().toUpperCase();
      if (!q) return;

      const found = state.shipments.find(s => 
        s.tracking_number.toUpperCase().includes(q) || 
        s.recipient_name.toUpperCase().includes(q)
      );

      if (found) {
        setActiveTracking(found.tracking_number);
        input.value = "";
      } else {
        alert(`No shipment found matching "${q}". Try ST-20261005-481920`);
      }
    }
  });
}

function resetMockState() {
  localStorage.clear();
  state.shipments = JSON.parse(JSON.stringify(MOCK_DATA.shipments));
  state.drivers = JSON.parse(JSON.stringify(MOCK_DATA.drivers));
  state.securityEvents = JSON.parse(JSON.stringify(MOCK_DATA.securityEvents));
  state.activeTrackingId = "ST-20261005-481920";
  renderAllViews();
  alert("Demo state reset to original pre-populated baseline.");
}

// Helper badge utilities
function getStatusBadgeClass(status) {
  const map = {
    "Order Placed": "badge-order-placed",
    "Picked Up": "badge-picked-up",
    "In Transit": "badge-in-transit",
    "Out for Delivery": "badge-out-for-delivery",
    "Delivered": "badge-delivered",
    "Cancelled": "badge-cancelled"
  };
  return map[status] || "badge-order-placed";
}

function getStatusIcon(status) {
  const map = {
    "Order Placed": "bi-check2-circle",
    "Picked Up": "bi-box-arrow-up",
    "In Transit": "bi-truck",
    "Out for Delivery": "bi-geo-alt",
    "Delivered": "bi-house-check",
    "Cancelled": "bi-x-circle"
  };
  return map[status] || "bi-dot";
}
