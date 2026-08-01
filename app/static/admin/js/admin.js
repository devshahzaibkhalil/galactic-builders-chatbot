/* Galactic Builders Admin Dashboard — shared helpers.
 * Every page includes this before its own page script.
 */

const AdminAPI = (() => {
  let csrfToken = null;

  async function getCsrfToken() {
    if (csrfToken) return csrfToken;
    const res = await fetch("/admin/csrf-token", { credentials: "same-origin" });
    const data = await res.json();
    csrfToken = data.csrf_token;
    return csrfToken;
  }

  async function request(path, { method = "GET", body } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (method !== "GET") {
      headers["X-CSRFToken"] = await getCsrfToken();
    }

    const res = await fetch(path, {
      method,
      headers,
      credentials: "same-origin",
      body: body ? JSON.stringify(body) : undefined,
    });

    let data = null;
    try {
      data = await res.json();
    } catch (err) {
      data = null;
    }

    if (!res.ok) {
      const message = (data && (data.message || data.error)) || `Request failed (${res.status})`;
      const error = new Error(message);
      error.status = res.status;
      error.data = data;
      throw error;
    }

    return data;
  }

  return {
    get: (path) => request(path, { method: "GET" }),
    post: (path, body) => request(path, { method: "POST", body }),
  };
})();

function showToast(message, { tone = "info" } = {}) {
  const existing = document.querySelector(".toast");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.className = "toast";
  toast.dataset.tone = tone;
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => toast.remove(), 4000);
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value == null ? "" : String(value);
  return div.innerHTML;
}

function formatServiceName(serviceKey) {
  if (!serviceKey) return "General inquiry";
  return serviceKey
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function formatDate(isoString) {
  if (!isoString) return "";
  const d = new Date(isoString);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function applyTheme(primaryColor, accentColor) {
  document.documentElement.style.setProperty("--navy-900", primaryColor);
  document.documentElement.style.setProperty("--gold-500", accentColor);
  try {
    localStorage.setItem("gb_admin_theme", JSON.stringify({ primaryColor, accentColor }));
  } catch (err) {
    /* localStorage unavailable — theme just won't persist locally, no functional impact */
  }
}

function applyStoredTheme() {
  // Apply a cached copy instantly (avoids a flash of default colors before
  // the network request resolves), then refresh from the server in case
  // another admin changed it since.
  try {
    const cached = JSON.parse(localStorage.getItem("gb_admin_theme") || "null");
    if (cached) applyTheme(cached.primaryColor, cached.accentColor);
  } catch (err) {
    /* ignore malformed cache */
  }

  fetch("/admin/settings", { credentials: "same-origin" })
    .then((res) => (res.ok ? res.json() : null))
    .then((theme) => {
      if (theme) applyTheme(theme.primary_color, theme.accent_color);
    })
    .catch(() => {});
}

function notificationItemTemplate(n) {
  const link = n.related_type === "lead" && n.related_id
    ? `/admin/dashboard/leads`
    : n.related_type === "conversation" && n.related_id
    ? `/admin/dashboard/conversations/${encodeURIComponent(n.related_id)}`
    : null;
  const inner = `
    <div class="bell-item-title">${escapeHtml(n.title)}</div>
    <div class="bell-item-body">${escapeHtml(n.body || "")}</div>
  `;
  return link
    ? `<a class="bell-item" href="${link}" data-notification-id="${n.id}">${inner}</a>`
    : `<div class="bell-item" data-notification-id="${n.id}">${inner}</div>`;
}

async function initNotificationBell() {
  const btn = document.getElementById("bell-btn");
  const badge = document.getElementById("bell-badge");
  const dropdown = document.getElementById("bell-dropdown");
  if (!btn || !badge || !dropdown) return;

  async function refresh() {
    try {
      const data = await AdminAPI.get("/admin/notifications");
      const items = data.notifications || [];
      if (items.length) {
        badge.hidden = false;
        badge.textContent = items.length > 9 ? "9+" : String(items.length);
        dropdown.innerHTML = items.map(notificationItemTemplate).join("");
      } else {
        badge.hidden = true;
        dropdown.innerHTML = `<div class="bell-empty">You're all caught up.</div>`;
      }
    } catch (err) {
      dropdown.innerHTML = `<div class="bell-empty">Could not load notifications.</div>`;
    }
  }

  btn.addEventListener("click", () => {
    dropdown.hidden = !dropdown.hidden;
  });

  dropdown.addEventListener("click", async (e) => {
    const item = e.target.closest("[data-notification-id]");
    if (!item) return;
    try {
      await AdminAPI.post(`/admin/notifications/${encodeURIComponent(item.dataset.notificationId)}/read`);
    } catch (err) {
      /* best effort */
    }
  });

  document.addEventListener("click", (e) => {
    if (!dropdown.hidden && !dropdown.contains(e.target) && e.target !== btn && !btn.contains(e.target)) {
      dropdown.hidden = true;
    }
  });

  await refresh();
  setInterval(refresh, 15000);
}

async function requireLogin() {
  try {
    return await AdminAPI.get("/admin/me");
  } catch (err) {
    window.location.href = "/admin/dashboard/login";
    return null;
  }
}

document.addEventListener("click", async (e) => {
  const logoutBtn = e.target.closest("[data-action='logout']");
  if (!logoutBtn) return;
  try {
    await AdminAPI.post("/admin/logout");
  } finally {
    window.location.href = "/admin/dashboard/login";
  }
});
