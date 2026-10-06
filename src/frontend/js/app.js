/**
 * ShipTrack: Delivery & Shipment Management (PS-05)
 * Production Application Controller (Direct API Integration)
 *
 * Rules Enforcement:
 * - Strict DOM textContent usage for all server and user data (XSS prevention).
 * - Zero tokens or passwords stored in localStorage.
 * - Zero hardcoded demo credentials in UI.
 * - Dynamic view routing driven strictly by GET /api/auth/me server response.
 */

// Application State (In-Memory Only, No localStorage credentials)
const appState = {
  currentUser: null,
  activeShipmentId: null,
  activeTrackingNumber: null
};

// ==============================================================================
// INITIALIZATION
// ==============================================================================
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  checkAuthSession();
});

function setupEventListeners() {
  // Navigation / Logout
  document.getElementById("btnNavLogout")?.addEventListener("click", handleLogout);
  document.getElementById("btnGlobalSearch")?.addEventListener("click", handleGlobalSearch);
  document.getElementById("globalTrackingInput")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleGlobalSearch();
  });

  // Auth Tabs & Forms
  document.getElementById("tabLoginBtn")?.addEventListener("click", () => switchAuthTab("login"));
  document.getElementById("tabRegisterBtn")?.addEventListener("click", () => switchAuthTab("register"));
  document.getElementById("formLogin")?.addEventListener("submit", handleLoginSubmit);
  document.getElementById("formRegister")?.addEventListener("submit", handleRegisterSubmit);
  document.getElementById("btnAccessPublicToken")?.addEventListener("click", handlePublicTokenAccess);

  // Customer Actions
  document.getElementById("formCreateShipment")?.addEventListener("submit", handleCreateShipmentSubmit);
  document.getElementById("btnRefreshCustomerShipments")?.addEventListener("click", loadCustomerShipments);
  document.getElementById("btnCloseTrackingDetail")?.addEventListener("click", closeCustomerTrackingDetail);
  document.getElementById("btnVerifyChain")?.addEventListener("click", handleVerifyChainClick);
  document.getElementById("btnGenerateToken")?.addEventListener("click", handleGenerateTokenClick);

  // Delivery Actions
  document.getElementById("btnRefreshDeliveryTasks")?.addEventListener("click", loadDeliveryDashboard);
  document.getElementById("formCourierStatus")?.addEventListener("submit", handleCourierStatusSubmit);

  // Admin Actions
  document.getElementById("btnRefreshAdminData")?.addEventListener("click", loadAdminDashboard);
  document.getElementById("tabAdminShipmentsBtn")?.addEventListener("click", () => switchAdminTab("shipments"));
  document.getElementById("tabAdminDispatchBtn")?.addEventListener("click", () => switchAdminTab("dispatch"));
  document.getElementById("tabAdminUsersBtn")?.addEventListener("click", () => switchAdminTab("users"));
  document.getElementById("tabAdminSecurityBtn")?.addEventListener("click", () => switchAdminTab("security"));
  document.getElementById("formAdminAssign")?.addEventListener("submit", handleAdminAssignSubmit);
}

// ==============================================================================
// SESSION AUTHENTICATION & VIEW ROUTING
// ==============================================================================
async function checkAuthSession() {
  try {
    const res = await fetch("/api/auth/me", { method: "GET" });
    if (res.status === 200) {
      const data = await res.json();
      appState.currentUser = data.user;
      renderAuthenticatedLayout(data.user);
    } else {
      appState.currentUser = null;
      renderUnauthenticatedLayout();
    }
  } catch (err) {
    appState.currentUser = null;
    renderUnauthenticatedLayout();
  }
}

function renderAuthenticatedLayout(user) {
  // Update Navbar Session Display
  const navUserBadge = document.getElementById("navUserBadge");
  const navUserName = document.getElementById("navUserName");
  const navUserRole = document.getElementById("navUserRole");
  const btnNavLogout = document.getElementById("btnNavLogout");

  if (navUserName) navUserName.textContent = user.full_name || user.username;
  if (navUserRole) navUserRole.textContent = user.role;
  navUserBadge?.classList.remove("d-none");
  btnNavLogout?.classList.remove("d-none");

  // Hide Auth Screen
  document.getElementById("authView")?.classList.add("d-none");

  // Show only the dashboard for the role returned by the server
  const custView = document.getElementById("customerView");
  const delivView = document.getElementById("deliveryView");
  const adminView = document.getElementById("adminView");

  custView?.classList.add("d-none");
  delivView?.classList.add("d-none");
  adminView?.classList.add("d-none");

  if (user.role === "customer") {
    custView?.classList.remove("d-none");
    loadCustomerShipments();
  } else if (user.role === "delivery_person") {
    delivView?.classList.remove("d-none");
    loadDeliveryDashboard();
  } else if (user.role === "admin") {
    adminView?.classList.remove("d-none");
    loadAdminDashboard();
  }
}

function renderUnauthenticatedLayout() {
  // Hide Navbar Session Display
  document.getElementById("navUserBadge")?.classList.add("d-none");
  document.getElementById("btnNavLogout")?.classList.add("d-none");

  // Hide All Role Dashboards
  document.getElementById("customerView")?.classList.add("d-none");
  document.getElementById("deliveryView")?.classList.add("d-none");
  document.getElementById("adminView")?.classList.add("d-none");

  // Show Auth Screen
  document.getElementById("authView")?.classList.remove("d-none");
  switchAuthTab("login");
}

function switchAuthTab(tab) {
  const loginTab = document.getElementById("tabLoginBtn");
  const regTab = document.getElementById("tabRegisterBtn");
  const formLogin = document.getElementById("formLogin");
  const formRegister = document.getElementById("formRegister");

  clearFeedback("loginFeedback");
  clearFeedback("registerFeedback");

  if (tab === "login") {
    loginTab?.classList.add("active");
    regTab?.classList.remove("active");
    formLogin?.classList.remove("d-none");
    formRegister?.classList.add("d-none");
  } else {
    regTab?.classList.add("active");
    loginTab?.classList.remove("active");
    formRegister?.classList.remove("d-none");
    formLogin?.classList.add("d-none");
  }
}

// ==============================================================================
// AUTHENTICATION HANDLERS
// ==============================================================================
async function handleLoginSubmit(e) {
  e.preventDefault();
  const identifierInput = document.getElementById("loginIdentifier");
  const passwordInput = document.getElementById("loginPassword");
  const submitBtn = document.getElementById("btnSubmitLogin");

  const identifier = identifierInput ? identifierInput.value.trim() : "";
  const password = passwordInput ? passwordInput.value : "";

  if (!identifier || !password) {
    showFeedback("loginFeedback", "Please enter both identifier and password.", "danger");
    return;
  }

  if (submitBtn) submitBtn.disabled = true;
  clearFeedback("loginFeedback");

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier, password })
    });

    const data = await res.json();
    if (res.ok) {
      if (passwordInput) passwordInput.value = "";
      await checkAuthSession();
    } else {
      showFeedback("loginFeedback", data.error || "Login failed.", "danger");
    }
  } catch (err) {
    showFeedback("loginFeedback", "Network error communicating with server.", "danger");
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

async function handleRegisterSubmit(e) {
  e.preventDefault();
  const usernameInput = document.getElementById("regUsername");
  const emailInput = document.getElementById("regEmail");
  const fullNameInput = document.getElementById("regFullName");
  const phoneInput = document.getElementById("regPhone");
  const passwordInput = document.getElementById("regPassword");
  const submitBtn = document.getElementById("btnSubmitRegister");

  const username = usernameInput ? usernameInput.value.trim() : "";
  const email = emailInput ? emailInput.value.trim() : "";
  const full_name = fullNameInput ? fullNameInput.value.trim() : "";
  const phone = phoneInput ? phoneInput.value.trim() : "";
  const password = passwordInput ? passwordInput.value : "";

  if (submitBtn) submitBtn.disabled = true;
  clearFeedback("registerFeedback");

  try {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, full_name, phone, password })
    });

    const data = await res.json();
    if (res.status === 201) {
      showFeedback("registerFeedback", "Registration successful! You may now sign in.", "success");
      if (passwordInput) passwordInput.value = "";
      setTimeout(() => switchAuthTab("login"), 1500);
    } else {
      showFeedback("registerFeedback", data.error || "Registration failed.", "danger");
    }
  } catch (err) {
    showFeedback("registerFeedback", "Network error communicating with server.", "danger");
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

async function handleLogout() {
  try {
    await fetch("/api/auth/logout", { method: "POST" });
  } catch (err) {
    // proceed to clear UI
  }
  appState.currentUser = null;
  renderUnauthenticatedLayout();
}

// ==============================================================================
// CUSTOMER PORTAL
// ==============================================================================
async function loadCustomerShipments() {
  const tbody = document.getElementById("customerShipmentsTableBody");
  if (!tbody) return;

  clearElement(tbody);
  const loadingRow = document.createElement("tr");
  const loadingTd = document.createElement("td");
  loadingTd.colSpan = 7;
  loadingTd.className = "text-center py-4 text-muted";
  loadingTd.textContent = "Loading shipments from server...";
  loadingRow.appendChild(loadingTd);
  tbody.appendChild(loadingRow);

  try {
    const res = await fetch("/api/shipments", { method: "GET" });
    if (!res.ok) {
      clearElement(tbody);
      const errRow = document.createElement("tr");
      const errTd = document.createElement("td");
      errTd.colSpan = 7;
      errTd.className = "text-center py-4 text-danger";
      errTd.textContent = "Unable to load shipments from server.";
      errRow.appendChild(errTd);
      tbody.appendChild(errRow);
      return;
    }

    const data = await res.json();
    const shipments = data.shipments || [];
    clearElement(tbody);

    if (shipments.length === 0) {
      const emptyRow = document.createElement("tr");
      const emptyTd = document.createElement("td");
      emptyTd.colSpan = 7;
      emptyTd.className = "text-center py-4 text-muted";
      emptyTd.textContent = "No shipments created yet. Click 'New Shipment' above to create one.";
      emptyRow.appendChild(emptyTd);
      tbody.appendChild(emptyRow);
      return;
    }

    shipments.forEach(s => {
      const tr = document.createElement("tr");

      // Tracking Number
      const tdTracking = document.createElement("td");
      const btnTrack = document.createElement("button");
      btnTrack.type = "button";
      btnTrack.className = "btn btn-link p-0 font-monospace fw-bold text-decoration-none";
      btnTrack.textContent = s.tracking_number;
      btnTrack.addEventListener("click", () => fetchAndShowTrackingDetails(s.tracking_number));
      tdTracking.appendChild(btnTrack);
      tr.appendChild(tdTracking);

      // Recipient & Destination
      const tdRecip = document.createElement("td");
      const recipName = document.createElement("div");
      recipName.className = "fw-semibold";
      recipName.textContent = s.recipient_name;
      const recipAddr = document.createElement("small");
      recipAddr.className = "text-muted d-block text-truncate";
      recipAddr.style.maxWidth = "220px";
      recipAddr.textContent = s.recipient_address;
      tdRecip.appendChild(recipName);
      tdRecip.appendChild(recipAddr);
      tr.appendChild(tdRecip);

      // Description
      const tdDesc = document.createElement("td");
      tdDesc.className = "small text-secondary";
      tdDesc.textContent = s.package_description;
      tr.appendChild(tdDesc);

      // Weight
      const tdWeight = document.createElement("td");
      tdWeight.className = "small";
      tdWeight.textContent = `${s.weight_kg} kg`;
      tr.appendChild(tdWeight);

      // Status
      const tdStatus = document.createElement("td");
      tdStatus.appendChild(createStatusBadge(s.current_status));
      tr.appendChild(tdStatus);

      // Created Date
      const tdDate = document.createElement("td");
      tdDate.className = "small text-muted";
      tdDate.textContent = s.created_at ? s.created_at.split(" ")[0] : "";
      tr.appendChild(tdDate);

      // Actions
      const tdActions = document.createElement("td");
      tdActions.className = "text-end";

      const btnGroup = document.createElement("div");
      btnGroup.className = "btn-group btn-group-sm";

      const btnInspect = document.createElement("button");
      btnInspect.type = "button";
      btnInspect.className = "btn btn-outline-primary";
      btnInspect.textContent = "Track";
      btnInspect.addEventListener("click", () => fetchAndShowTrackingDetails(s.tracking_number));
      btnGroup.appendChild(btnInspect);

      if (s.current_status === "Order Placed") {
        const btnCancel = document.createElement("button");
        btnCancel.type = "button";
        btnCancel.className = "btn btn-outline-danger";
        btnCancel.textContent = "Cancel";
        btnCancel.addEventListener("click", () => handleCancelShipment(s.id, s.tracking_number));
        btnGroup.appendChild(btnCancel);
      }

      tdActions.appendChild(btnGroup);
      tr.appendChild(tdActions);

      tbody.appendChild(tr);
    });
  } catch (err) {
    clearElement(tbody);
    const errRow = document.createElement("tr");
    const errTd = document.createElement("td");
    errTd.colSpan = 7;
    errTd.className = "text-center py-4 text-danger";
    errTd.textContent = "Failed to load shipments.";
    errRow.appendChild(errTd);
    tbody.appendChild(errRow);
  }
}

async function handleCreateShipmentSubmit(e) {
  e.preventDefault();
  const senderName = document.getElementById("shipSenderName")?.value.trim();
  const senderAddress = document.getElementById("shipSenderAddress")?.value.trim();
  const recipientName = document.getElementById("shipRecipientName")?.value.trim();
  const recipientPhone = document.getElementById("shipRecipientPhone")?.value.trim();
  const recipientAddress = document.getElementById("shipRecipientAddress")?.value.trim();
  const packageDesc = document.getElementById("shipPackageDesc")?.value.trim();
  const weightKg = parseFloat(document.getElementById("shipWeightKg")?.value);
  const submitBtn = document.getElementById("btnSubmitCreateShipment");

  if (!senderName || !senderAddress || !recipientName || !recipientPhone || !recipientAddress || !packageDesc || isNaN(weightKg)) {
    showFeedback("createShipmentFeedback", "Please fill in all required fields with valid values.", "danger");
    return;
  }

  if (submitBtn) submitBtn.disabled = true;
  clearFeedback("createShipmentFeedback");

  try {
    const res = await fetch("/api/shipments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sender_name: senderName,
        sender_address: senderAddress,
        recipient_name: recipientName,
        recipient_phone: recipientPhone,
        recipient_address: recipientAddress,
        package_description: packageDesc,
        weight_kg: weightKg
      })
    });

    const data = await res.json();
    if (res.status === 201) {
      showFeedback("createShipmentFeedback", `Shipment created successfully! Tracking #: ${data.shipment.tracking_number}`, "success");
      document.getElementById("formCreateShipment")?.reset();
      await loadCustomerShipments();
      await fetchAndShowTrackingDetails(data.shipment.tracking_number);
    } else {
      showFeedback("createShipmentFeedback", data.error || "Shipment creation failed.", "danger");
    }
  } catch (err) {
    showFeedback("createShipmentFeedback", "Network error creating shipment.", "danger");
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

async function fetchAndShowTrackingDetails(trackingNumber) {
  const detailCard = document.getElementById("customerTrackingDetailCard");
  if (!detailCard) return;

  clearFeedback("chainVerificationAlertContainer");
  clearFeedback("generatedTokenAlertContainer");

  try {
    const res = await fetch(`/api/shipments/${encodeURIComponent(trackingNumber)}`, { method: "GET" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showSystemAlert(err.error || "Shipment not found or unauthorized.", "danger");
      return;
    }

    const data = await res.json();
    const s = data.shipment;
    const timeline = data.timeline || [];

    appState.activeShipmentId = s.id;
    appState.activeTrackingNumber = s.tracking_number;

    // Populate Metadata via textContent
    setText("detailTrackingNumBadge", s.tracking_number);
    const statusBadge = document.getElementById("detailStatusBadge");
    if (statusBadge) {
      clearElement(statusBadge);
      statusBadge.appendChild(createStatusBadge(s.current_status));
    }
    setText("detailSenderName", s.sender_name);
    setText("detailSenderAddress", s.sender_address);
    setText("detailRecipientName", s.recipient_name);
    setText("detailRecipientAddress", s.recipient_address);
    setText("detailRecipientPhone", s.recipient_phone);
    setText("detailPackageDesc", s.package_description);
    setText("detailWeightKg", s.weight_kg);
    setText("detailCreatedAt", s.created_at);

    // Populate Timeline Table via textContent
    const tbody = document.getElementById("timelineTableBody");
    if (tbody) {
      clearElement(tbody);
      timeline.forEach(item => {
        const tr = document.createElement("tr");

        const tdStatus = document.createElement("td");
        tdStatus.appendChild(createStatusBadge(item.status));
        tr.appendChild(tdStatus);

        const tdLoc = document.createElement("td");
        tdLoc.textContent = item.location || "";
        tr.appendChild(tdLoc);

        const tdNotes = document.createElement("td");
        tdNotes.textContent = item.notes || "";
        tr.appendChild(tdNotes);

        const tdTime = document.createElement("td");
        tdTime.textContent = item.timestamp || "";
        tr.appendChild(tdTime);

        const tdUpdater = document.createElement("td");
        tdUpdater.textContent = item.updater_username ? `${item.updater_username} (${item.updater_role})` : `User #${item.updated_by_id}`;
        tr.appendChild(tdUpdater);

        const tdHash = document.createElement("td");
        tdHash.className = "font-monospace";
        tdHash.style.fontSize = "0.72rem";
        tdHash.textContent = item.record_hash ? item.record_hash.substring(0, 16) + "..." : "";
        tr.appendChild(tdHash);

        tbody.appendChild(tr);
      });
    }

    detailCard.classList.remove("d-none");
    detailCard.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    showSystemAlert("Failed to retrieve tracking details.", "danger");
  }
}

function closeCustomerTrackingDetail() {
  document.getElementById("customerTrackingDetailCard")?.classList.add("d-none");
  appState.activeShipmentId = null;
  appState.activeTrackingNumber = null;
}

async function handleCancelShipment(shipmentId, trackingNumber) {
  if (!confirm(`Are you sure you want to cancel shipment ${trackingNumber}?`)) return;

  try {
    const res = await fetch(`/api/shipments/${shipmentId}/cancel`, { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      showSystemAlert(`Shipment ${trackingNumber} cancelled successfully.`, "success");
      await loadCustomerShipments();
      if (appState.activeShipmentId === shipmentId) {
        await fetchAndShowTrackingDetails(trackingNumber);
      }
    } else {
      showSystemAlert(data.error || "Failed to cancel shipment.", "danger");
    }
  } catch (err) {
    showSystemAlert("Network error while cancelling shipment.", "danger");
  }
}

async function handleVerifyChainClick() {
  if (!appState.activeShipmentId) return;

  const container = document.getElementById("chainVerificationAlertContainer");
  if (!container) return;

  clearFeedback("chainVerificationAlertContainer");

  try {
    const res = await fetch(`/api/shipments/${appState.activeShipmentId}/verify`, { method: "GET" });
    const data = await res.json();

    const alertDiv = document.createElement("div");
    if (res.ok && data.valid === true) {
      alertDiv.className = "alert alert-success border-success p-3 small mb-0";
      alertDiv.textContent = `Cryptographic Chain Verified: Intact. Verified across ${data.record_count} status record(s). Zero tampering detected.`;
    } else {
      alertDiv.className = "alert alert-danger border-danger p-3 small mb-0";
      alertDiv.textContent = `Tamper Alert: Cryptographic chain compromised at record #${data.broken_at_record_id || 'unknown'}!`;
    }
    container.appendChild(alertDiv);
  } catch (err) {
    showFeedback("chainVerificationAlertContainer", "Error verifying chain integrity.", "danger");
  }
}

async function handleGenerateTokenClick() {
  if (!appState.activeShipmentId) return;

  const container = document.getElementById("generatedTokenAlertContainer");
  if (!container) return;

  clearFeedback("generatedTokenAlertContainer");

  try {
    const res = await fetch(`/api/shipments/${appState.activeShipmentId}/generate-tracking-link`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ttl_minutes: 15 })
    });

    const data = await res.json();
    if (res.status === 201) {
      const alertDiv = document.createElement("div");
      alertDiv.className = "alert alert-info border-info p-3 small mb-0";

      const title = document.createElement("strong");
      title.className = "d-block mb-1";
      title.textContent = "Ephemeral 1-Time Secure Tracking Link Generated";
      alertDiv.appendChild(title);

      const desc = document.createElement("div");
      desc.textContent = "This token is single-use and will burn permanently upon first view. Share the token with recipient:";
      alertDiv.appendChild(desc);

      const tokenBox = document.createElement("div");
      tokenBox.className = "font-monospace bg-white p-2 rounded border my-2 text-break fw-bold text-dark";
      tokenBox.textContent = data.token;
      alertDiv.appendChild(tokenBox);

      const exp = document.createElement("small");
      exp.className = "text-muted d-block";
      exp.textContent = `Expires at (UTC): ${data.expires_at}`;
      alertDiv.appendChild(exp);

      container.appendChild(alertDiv);
    } else {
      showFeedback("generatedTokenAlertContainer", data.error || "Failed to generate link.", "danger");
    }
  } catch (err) {
    showFeedback("generatedTokenAlertContainer", "Error generating link.", "danger");
  }
}

// ==============================================================================
// PUBLIC 1-TIME EPHEMERAL TOKEN VIEWER
// ==============================================================================
async function handlePublicTokenAccess() {
  const tokenInput = document.getElementById("publicTokenInput");
  const token = tokenInput ? tokenInput.value.trim() : "";
  if (!token) return;

  const resultBody = document.getElementById("publicTokenResultBody");
  if (!resultBody) return;

  clearElement(resultBody);
  const loading = document.createElement("p");
  loading.className = "text-muted small";
  loading.textContent = "Accessing single-use tracking link...";
  resultBody.appendChild(loading);

  const modalEl = document.getElementById("modalPublicTokenResult");
  const modal = modalEl ? new bootstrap.Modal(modalEl) : null;
  modal?.show();

  try {
    const res = await fetch(`/api/tracking/live/${encodeURIComponent(token)}`, { method: "GET" });
    const data = await res.json();

    clearElement(resultBody);

    if (res.status === 200) {
      const successCard = document.createElement("div");
      successCard.className = "alert alert-success border-success small mb-3";

      const heading = document.createElement("strong");
      heading.className = "d-block mb-1";
      heading.textContent = "Single-Use Tracking Authorized";
      successCard.appendChild(heading);

      const notice = document.createElement("div");
      notice.textContent = data.notice || "This link has been accessed and permanently burned.";
      successCard.appendChild(notice);
      resultBody.appendChild(successCard);

      if (data.shipment) {
        const shipInfo = document.createElement("div");
        shipInfo.className = "card bg-light border-0 p-3 mb-3 small";

        const line1 = document.createElement("div");
        line1.textContent = `Tracking #: ${data.shipment.tracking_number}`;
        shipInfo.appendChild(line1);

        const line2 = document.createElement("div");
        line2.textContent = `Current Status: ${data.shipment.current_status}`;
        shipInfo.appendChild(line2);

        const line3 = document.createElement("div");
        line3.textContent = `Cargo: ${data.shipment.package_description}`;
        shipInfo.appendChild(line3);

        const line4 = document.createElement("div");
        line4.textContent = `Destination: ${data.shipment.destination}`;
        shipInfo.appendChild(line4);

        resultBody.appendChild(shipInfo);
      }

      if (data.live_gps) {
        const gpsInfo = document.createElement("div");
        gpsInfo.className = "card border p-3 small mb-2";

        const gpsTitle = document.createElement("strong");
        gpsTitle.textContent = "Live GPS Coordinates:";
        gpsInfo.appendChild(gpsTitle);

        const coords = document.createElement("div");
        coords.className = "font-monospace mt-1";
        coords.textContent = `Lat: ${data.live_gps.latitude}, Long: ${data.live_gps.longitude} (Speed: ${data.live_gps.speed_kmh} km/h)`;
        gpsInfo.appendChild(coords);

        resultBody.appendChild(gpsInfo);
      }
    } else if (res.status === 410) {
      const errCard = document.createElement("div");
      errCard.className = "alert alert-danger border-danger small";

      const errTitle = document.createElement("strong");
      errTitle.className = "d-block mb-1";
      errTitle.textContent = "HTTP 410 Gone: Link Inactivated";
      errCard.appendChild(errTitle);

      const errMsg = document.createElement("div");
      errMsg.textContent = data.error || "This single-use link has expired or has already been consumed.";
      errCard.appendChild(errMsg);

      resultBody.appendChild(errCard);
    } else {
      const errCard = document.createElement("div");
      errCard.className = "alert alert-warning border-warning small";
      errCard.textContent = data.error || "Invalid tracking token.";
      resultBody.appendChild(errCard);
    }
  } catch (err) {
    clearElement(resultBody);
    const errCard = document.createElement("div");
    errCard.className = "alert alert-danger small";
    errCard.textContent = "Network error accessing tracking link.";
    resultBody.appendChild(errCard);
  }
}

// ==============================================================================
// DELIVERY COURIER PORTAL
// ==============================================================================
async function loadDeliveryDashboard() {
  const tbody = document.getElementById("deliveryTasksTableBody");
  if (!tbody) return;

  clearElement(tbody);

  try {
    const res = await fetch("/api/delivery/dashboard", { method: "GET" });
    if (!res.ok) return;

    const data = await res.json();
    const metrics = data.metrics || {};
    const tasks = data.active_shipments || data.assigned_shipments || [];

    // Populate Metrics via textContent
    setText("delivMetricTotal", metrics.total_assigned || 0);
    setText("delivMetricTransit", (metrics.picked_up || 0) + (metrics.in_transit || 0));
    setText("delivMetricOut", metrics.out_for_delivery || 0);
    setText("delivMetricDelivered", metrics.delivered || 0);

    if (tasks.length === 0) {
      const emptyRow = document.createElement("tr");
      const emptyTd = document.createElement("td");
      emptyTd.colSpan = 7;
      emptyTd.className = "text-center py-4 text-muted";
      emptyTd.textContent = "No shipments currently assigned to you.";
      emptyRow.appendChild(emptyTd);
      tbody.appendChild(emptyRow);
      return;
    }

    tasks.forEach(t => {
      const tr = document.createElement("tr");

      const tdTracking = document.createElement("td");
      tdTracking.className = "font-monospace fw-bold text-primary";
      tdTracking.textContent = t.tracking_number;
      tr.appendChild(tdTracking);

      const tdPickup = document.createElement("td");
      tdPickup.className = "small text-muted";
      tdPickup.textContent = t.sender_address;
      tr.appendChild(tdPickup);

      const tdDeliv = document.createElement("td");
      tdDeliv.className = "small text-muted";
      tdDeliv.textContent = t.recipient_address;
      tr.appendChild(tdDeliv);

      const tdPhone = document.createElement("td");
      tdPhone.className = "small";
      tdPhone.textContent = t.recipient_phone;
      tr.appendChild(tdPhone);

      const tdCargo = document.createElement("td");
      tdCargo.className = "small";
      tdCargo.textContent = `${t.package_description} (${t.weight_kg} kg)`;
      tr.appendChild(tdCargo);

      const tdStatus = document.createElement("td");
      tdStatus.appendChild(createStatusBadge(t.current_status));
      tr.appendChild(tdStatus);

      const tdAction = document.createElement("td");
      tdAction.className = "text-end";

      if (t.current_status === "Delivered" || t.current_status === "Cancelled") {
        const badge = document.createElement("span");
        badge.className = "badge bg-light text-dark border";
        badge.textContent = "Completed";
        tdAction.appendChild(badge);
      } else {
        const btnUpdate = document.createElement("button");
        btnUpdate.type = "button";
        btnUpdate.className = "btn btn-sm btn-primary";
        btnUpdate.textContent = "Advance Milestone";
        btnUpdate.addEventListener("click", () => openCourierStatusModal(t));
        tdAction.appendChild(btnUpdate);
      }

      tr.appendChild(tdAction);
      tbody.appendChild(tr);
    });
  } catch (err) {
    // handled gracefully
  }
}

function openCourierStatusModal(shipment) {
  const modalEl = document.getElementById("modalCourierStatus");
  if (!modalEl) return;

  const idInput = document.getElementById("statusShipmentId");
  if (idInput) idInput.value = shipment.id;

  const titleEl = document.getElementById("modalCourierStatusTitle");
  if (titleEl) titleEl.textContent = `Update Status for ${shipment.tracking_number}`;

  const selectStatus = document.getElementById("selectNextStatus");
  if (selectStatus) {
    clearElement(selectStatus);

    const nextStatuses = [];
    if (shipment.current_status === "Order Placed") nextStatuses.push("Picked Up");
    else if (shipment.current_status === "Picked Up") nextStatuses.push("In Transit");
    else if (shipment.current_status === "In Transit") nextStatuses.push("Out for Delivery");
    else if (shipment.current_status === "Out for Delivery") nextStatuses.push("Delivered");

    nextStatuses.forEach(st => {
      const opt = document.createElement("option");
      opt.value = st;
      opt.textContent = st;
      selectStatus.appendChild(opt);
    });
  }

  const locInput = document.getElementById("inputStatusLocation");
  if (locInput) locInput.value = "";

  const notesInput = document.getElementById("inputStatusNotes");
  if (notesInput) notesInput.value = "";

  clearFeedback("statusModalFeedback");

  const modal = new bootstrap.Modal(modalEl);
  modal.show();
}

async function handleCourierStatusSubmit(e) {
  e.preventDefault();
  const shipmentId = document.getElementById("statusShipmentId")?.value;
  const status = document.getElementById("selectNextStatus")?.value;
  const location = document.getElementById("inputStatusLocation")?.value.trim();
  const notes = document.getElementById("inputStatusNotes")?.value.trim();

  if (!shipmentId || !status || !location) {
    showFeedback("statusModalFeedback", "Status and location are required.", "danger");
    return;
  }

  try {
    const res = await fetch(`/api/delivery/shipments/${shipmentId}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status, location, notes })
    });

    const data = await res.json();
    if (res.ok) {
      const modalEl = document.getElementById("modalCourierStatus");
      const modal = modalEl ? bootstrap.Modal.getInstance(modalEl) : null;
      modal?.hide();

      showSystemAlert(`Milestone advanced to '${status}'.`, "success");
      await loadDeliveryDashboard();
    } else {
      showFeedback("statusModalFeedback", data.error || "Status update failed.", "danger");
    }
  } catch (err) {
    showFeedback("statusModalFeedback", "Error updating status.", "danger");
  }
}

// ==============================================================================
// ADMIN MANAGEMENT PORTAL
// ==============================================================================
async function loadAdminDashboard() {
  try {
    const res = await fetch("/api/admin/dashboard", { method: "GET" });
    if (!res.ok) return;

    const data = await res.json();
    const m = data.metrics || {};
    const statusCounts = m.status_counts || {};

    setText("adminMetricShipments", m.total_shipments || 0);
    setText("adminMetricUsers", m.total_users || 0);
    setText("adminMetricInDelivery", (statusCounts["In Transit"] || 0) + (statusCounts["Out for Delivery"] || 0));
    setText("adminMetricAlerts", m.recent_security_events_count || 0);

    // Load active tab data
    loadAdminShipments();
    loadAdminDispatch();
    loadAdminUsers();
    loadAdminSecurityEvents();
  } catch (err) {
    // handled gracefully
  }
}

function switchAdminTab(tabName) {
  const tabs = ["tabAdminShipmentsBtn", "tabAdminDispatchBtn", "tabAdminUsersBtn", "tabAdminSecurityBtn"];
  const panels = ["adminShipmentsPanel", "adminDispatchPanel", "adminUsersPanel", "adminSecurityPanel"];

  tabs.forEach(t => document.getElementById(t)?.classList.remove("active"));
  panels.forEach(p => document.getElementById(p)?.classList.add("d-none"));

  if (tabName === "shipments") {
    document.getElementById("tabAdminShipmentsBtn")?.classList.add("active");
    document.getElementById("adminShipmentsPanel")?.classList.remove("d-none");
    loadAdminShipments();
  } else if (tabName === "dispatch") {
    document.getElementById("tabAdminDispatchBtn")?.classList.add("active");
    document.getElementById("adminDispatchPanel")?.classList.remove("d-none");
    loadAdminDispatch();
  } else if (tabName === "users") {
    document.getElementById("tabAdminUsersBtn")?.classList.add("active");
    document.getElementById("adminUsersPanel")?.classList.remove("d-none");
    loadAdminUsers();
  } else if (tabName === "security") {
    document.getElementById("tabAdminSecurityBtn")?.classList.add("active");
    document.getElementById("adminSecurityPanel")?.classList.remove("d-none");
    loadAdminSecurityEvents();
  }
}

async function loadAdminShipments() {
  const tbody = document.getElementById("adminShipmentsTableBody");
  if (!tbody) return;

  clearElement(tbody);

  try {
    const res = await fetch("/api/admin/shipments?page=1&per_page=50", { method: "GET" });
    if (!res.ok) return;

    const data = await res.json();
    const shipments = data.shipments || [];

    if (shipments.length === 0) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 6;
      td.className = "text-center py-3 text-muted";
      td.textContent = "No shipments registered.";
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }

    shipments.forEach(s => {
      const tr = document.createElement("tr");

      const tdTracking = document.createElement("td");
      tdTracking.className = "font-monospace fw-bold text-primary";
      tdTracking.textContent = s.tracking_number;
      tr.appendChild(tdTracking);

      const tdCustomer = document.createElement("td");
      tdCustomer.textContent = s.customer_username || `Customer #${s.customer_id}`;
      tr.appendChild(tdCustomer);

      const tdCourier = document.createElement("td");
      if (s.courier_name || s.courier_username) {
        tdCourier.textContent = s.courier_name || s.courier_username;
      } else {
        const unassigned = document.createElement("span");
        unassigned.className = "badge bg-danger-subtle text-danger border border-danger-subtle";
        unassigned.textContent = "Unassigned";
        tdCourier.appendChild(unassigned);
      }
      tr.appendChild(tdCourier);

      const tdDest = document.createElement("td");
      tdDest.className = "small text-muted text-truncate";
      tdDest.style.maxWidth = "200px";
      tdDest.textContent = s.recipient_address;
      tr.appendChild(tdDest);

      const tdStatus = document.createElement("td");
      tdStatus.appendChild(createStatusBadge(s.current_status));
      tr.appendChild(tdStatus);

      const tdDate = document.createElement("td");
      tdDate.className = "small text-muted";
      tdDate.textContent = s.created_at ? s.created_at.split(" ")[0] : "";
      tr.appendChild(tdDate);

      tbody.appendChild(tr);
    });
  } catch (err) {}
}

async function loadAdminDispatch() {
  const tbody = document.getElementById("adminDispatchTableBody");
  if (!tbody) return;

  clearElement(tbody);

  try {
    const res = await fetch("/api/admin/shipments?page=1&per_page=100", { method: "GET" });
    if (!res.ok) return;

    const data = await res.json();
    const shipments = (data.shipments || []).filter(s => !s.assigned_delivery_id && s.current_status !== "Cancelled");

    if (shipments.length === 0) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 6;
      td.className = "text-center py-3 text-success";
      td.textContent = "No unassigned shipments pending dispatch.";
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }

    shipments.forEach(s => {
      const tr = document.createElement("tr");

      const tdTracking = document.createElement("td");
      tdTracking.className = "font-monospace fw-bold";
      tdTracking.textContent = s.tracking_number;
      tr.appendChild(tdTracking);

      const tdCustomer = document.createElement("td");
      tdCustomer.textContent = s.customer_username || s.sender_name;
      tr.appendChild(tdCustomer);

      const tdPickup = document.createElement("td");
      tdPickup.className = "small text-muted";
      tdPickup.textContent = s.sender_address;
      tr.appendChild(tdPickup);

      const tdDest = document.createElement("td");
      tdDest.className = "small text-muted";
      tdDest.textContent = s.recipient_address;
      tr.appendChild(tdDest);

      const tdCargo = document.createElement("td");
      tdCargo.className = "small";
      tdCargo.textContent = `${s.package_description} (${s.weight_kg} kg)`;
      tr.appendChild(tdCargo);

      const tdAction = document.createElement("td");
      tdAction.className = "text-end";
      const btnAssign = document.createElement("button");
      btnAssign.type = "button";
      btnAssign.className = "btn btn-sm btn-primary";
      btnAssign.textContent = "Assign Courier";
      btnAssign.addEventListener("click", () => openAdminAssignModal(s));
      tdAction.appendChild(btnAssign);
      tr.appendChild(tdAction);

      tbody.appendChild(tr);
    });
  } catch (err) {}
}

async function openAdminAssignModal(shipment) {
  const modalEl = document.getElementById("modalAdminAssign");
  if (!modalEl) return;

  const idInput = document.getElementById("assignShipmentId");
  if (idInput) idInput.value = shipment.id;

  setText("assignShipmentTrackingLabel", `${shipment.tracking_number} (${shipment.package_description})`);

  const selectCourier = document.getElementById("selectAssignCourier");
  if (selectCourier) {
    clearElement(selectCourier);

    try {
      const res = await fetch("/api/admin/delivery-persons", { method: "GET" });
      const data = await res.json();
      const couriers = data.delivery_persons || [];

      if (couriers.length === 0) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = "No registered delivery couriers available";
        selectCourier.appendChild(opt);
      } else {
        couriers.forEach(c => {
          const opt = document.createElement("option");
          opt.value = c.id;
          opt.textContent = `${c.full_name} (@${c.username}) — ${c.email}`;
          selectCourier.appendChild(opt);
        });
      }
    } catch (err) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "Error loading courier list";
      selectCourier.appendChild(opt);
    }
  }

  const notesInput = document.getElementById("inputAssignNotes");
  if (notesInput) notesInput.value = "";

  clearFeedback("assignModalFeedback");

  const modal = new bootstrap.Modal(modalEl);
  modal.show();
}

async function handleAdminAssignSubmit(e) {
  e.preventDefault();
  const shipmentId = document.getElementById("assignShipmentId")?.value;
  const courierId = document.getElementById("selectAssignCourier")?.value;
  const notes = document.getElementById("inputAssignNotes")?.value.trim();

  if (!shipmentId || !courierId) {
    showFeedback("assignModalFeedback", "Please select a valid courier.", "danger");
    return;
  }

  try {
    const res = await fetch(`/api/admin/shipments/${shipmentId}/assign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        delivery_person_id: parseInt(courierId),
        notes: notes || "Assigned via admin dispatch console."
      })
    });

    const data = await res.json();
    if (res.ok) {
      const modalEl = document.getElementById("modalAdminAssign");
      const modal = modalEl ? bootstrap.Modal.getInstance(modalEl) : null;
      modal?.hide();

      showSystemAlert("Shipment assigned successfully.", "success");
      await loadAdminDashboard();
    } else {
      showFeedback("assignModalFeedback", data.error || "Assignment failed.", "danger");
    }
  } catch (err) {
    showFeedback("assignModalFeedback", "Error submitting assignment.", "danger");
  }
}

async function loadAdminUsers() {
  const tbody = document.getElementById("adminUsersTableBody");
  if (!tbody) return;

  clearElement(tbody);

  try {
    const res = await fetch("/api/admin/users?page=1&per_page=50", { method: "GET" });
    if (!res.ok) return;

    const data = await res.json();
    const users = data.users || [];

    users.forEach(u => {
      const tr = document.createElement("tr");

      const tdId = document.createElement("td");
      tdId.textContent = u.id;
      tr.appendChild(tdId);

      const tdUser = document.createElement("td");
      tdUser.className = "fw-semibold";
      tdUser.textContent = u.username;
      tr.appendChild(tdUser);

      const tdEmail = document.createElement("td");
      tdEmail.textContent = u.email;
      tr.appendChild(tdEmail);

      const tdRole = document.createElement("td");
      const roleBadge = document.createElement("span");
      roleBadge.className = "badge";
      if (u.role === "admin") roleBadge.className += " bg-danger";
      else if (u.role === "delivery_person") roleBadge.className += " bg-info text-dark";
      else roleBadge.className += " bg-primary";
      roleBadge.textContent = u.role;
      tdRole.appendChild(roleBadge);
      tr.appendChild(tdRole);

      const tdName = document.createElement("td");
      tdName.textContent = u.full_name || "";
      tr.appendChild(tdName);

      const tdPhone = document.createElement("td");
      tdPhone.textContent = u.phone || "—";
      tr.appendChild(tdPhone);

      const tdCreated = document.createElement("td");
      tdCreated.className = "small text-muted";
      tdCreated.textContent = u.created_at ? u.created_at.split(" ")[0] : "";
      tr.appendChild(tdCreated);

      tbody.appendChild(tr);
    });
  } catch (err) {}
}

async function loadAdminSecurityEvents() {
  const tbody = document.getElementById("adminSecurityTableBody");
  if (!tbody) return;

  clearElement(tbody);

  try {
    const res = await fetch("/api/admin/security-events?page=1&per_page=50", { method: "GET" });
    if (!res.ok) return;

    const data = await res.json();
    const events = data.events || [];

    if (events.length === 0) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 5;
      td.className = "text-center py-3 text-muted";
      td.textContent = "No security events recorded.";
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }

    events.forEach(ev => {
      const tr = document.createElement("tr");

      const tdTime = document.createElement("td");
      tdTime.className = "small text-muted";
      tdTime.textContent = ev.created_at || "";
      tr.appendChild(tdTime);

      const tdType = document.createElement("td");
      const badge = document.createElement("span");
      badge.className = "badge bg-danger-subtle text-danger border border-danger-subtle";
      badge.textContent = ev.event_type;
      tdType.appendChild(badge);
      tr.appendChild(tdType);

      const tdIp = document.createElement("td");
      const code = document.createElement("code");
      code.textContent = ev.ip || "";
      tdIp.appendChild(code);
      tr.appendChild(tdIp);

      const tdPath = document.createElement("td");
      tdPath.className = "small text-muted";
      tdPath.textContent = ev.path || "";
      tr.appendChild(tdPath);

      const tdDetails = document.createElement("td");
      tdDetails.className = "small text-dark";
      tdDetails.textContent = ev.details || "";
      tr.appendChild(tdDetails);

      tbody.appendChild(tr);
    });
  } catch (err) {}
}

// ==============================================================================
// GLOBAL TRACKING LOOKUP (SEARCH BAR)
// ==============================================================================
async function handleGlobalSearch() {
  const input = document.getElementById("globalTrackingInput");
  const trackingNumber = input ? input.value.trim() : "";
  if (!trackingNumber) return;

  if (appState.currentUser && appState.currentUser.role === "customer") {
    await fetchAndShowTrackingDetails(trackingNumber);
    input.value = "";
  } else {
    // If not logged in as customer, inform user or load if authorized
    try {
      const res = await fetch(`/api/shipments/${encodeURIComponent(trackingNumber)}`);
      if (res.ok) {
        showSystemAlert(`Shipment ${trackingNumber} verified on server. Sign in to view full custody log.`, "info");
      } else {
        showSystemAlert(`Tracking number not found or requires authorized login.`, "warning");
      }
    } catch (e) {
      showSystemAlert("Error querying tracking number.", "danger");
    }
  }
}

// ==============================================================================
// DOM & SANITIZATION UTILITIES (STRICT textContent ONLY)
// ==============================================================================
function setText(elementId, text) {
  const el = document.getElementById(elementId);
  if (el) el.textContent = text !== null && text !== undefined ? String(text) : "";
}

function clearElement(element) {
  while (element.firstChild) {
    element.removeChild(element.firstChild);
  }
}

function clearFeedback(containerId) {
  const container = document.getElementById(containerId);
  if (container) clearElement(container);
}

function showFeedback(containerId, message, type) {
  const container = document.getElementById(containerId);
  if (!container) return;

  clearElement(container);
  const div = document.createElement("div");
  div.className = `alert alert-${type} p-2 small mb-0`;
  div.textContent = message;
  container.appendChild(div);
}

function showSystemAlert(message, type) {
  const container = document.getElementById("systemAlertContainer");
  if (!container) return;

  clearElement(container);
  const alertDiv = document.createElement("div");
  alertDiv.className = `alert alert-${type} alert-dismissible fade show p-3 small mb-0`;
  alertDiv.textContent = message;

  const closeBtn = document.createElement("button");
  closeBtn.type = "button";
  closeBtn.className = "btn-close";
  closeBtn.setAttribute("data-bs-dismiss", "alert");
  closeBtn.setAttribute("aria-label", "Close");

  alertDiv.appendChild(closeBtn);
  container.appendChild(alertDiv);

  setTimeout(() => {
    if (container.contains(alertDiv)) {
      alertDiv.classList.remove("show");
      setTimeout(() => clearElement(container), 200);
    }
  }, 5000);
}

function createStatusBadge(status) {
  const badge = document.createElement("span");
  badge.className = "badge";

  if (status === "Order Placed") badge.className += " bg-warning text-dark";
  else if (status === "Picked Up") badge.className += " bg-info text-dark";
  else if (status === "In Transit") badge.className += " bg-primary";
  else if (status === "Out for Delivery") badge.className += " bg-purple text-white";
  else if (status === "Delivered") badge.className += " bg-success";
  else if (status === "Cancelled") badge.className += " bg-danger";
  else badge.className += " bg-secondary";

  badge.textContent = status || "Unknown";
  return badge;
}
