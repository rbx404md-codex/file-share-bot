const tg = window.Telegram?.WebApp;
tg?.ready(); tg?.expand();
const initData = tg?.initData || "";

async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: { "Content-Type": "application/json", "X-Telegram-Init-Data": initData, ...(opts.headers || {}) },
  });
  if (!res.ok) {
    const b = await res.json().catch(() => ({}));
    throw new Error(b.error || `HTTP ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}
function toast(m) {
  const el = document.getElementById("toast");
  el.textContent = m; el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 1800);
}
function esc(s) { return (s || "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

document.querySelectorAll(".nav-item").forEach(el => el.addEventListener("click", () => goPage(el.dataset.page)));
function goPage(name) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  document.getElementById("page-" + name).classList.add("active");
  document.querySelector(`.nav-item[data-page="${name}"]`).classList.add("active");
  if (name === "home") loadStats();
  if (name === "users") loadUsers();
  if (name === "forcejoin") loadForceJoin();
  if (name === "audit") loadAudit();
}

async function loadStats() {
  try {
    const s = await api("/api/admin/stats");
    document.getElementById("statsGrid").innerHTML = `
      <div class="stat"><div class="n">${s.users}</div><div class="l">👥 Users</div></div>
      <div class="stat"><div class="n">${s.today_users}</div><div class="l">🟡 Joined Today</div></div>
      <div class="stat"><div class="n">${s.files}</div><div class="l">📁 Files</div></div>
      <div class="stat"><div class="n">${s.downloads}</div><div class="l">⬇️ Downloads</div></div>
      <div class="stat"><div class="n">${s.trashed}</div><div class="l">🗑 Trashed</div></div>
      <div class="stat"><div class="n">${s.storage_h}</div><div class="l">💾 Storage</div></div>
      <div class="stat"><div class="n">${s.banned}</div><div class="l">🔴 Banned</div></div>
    `;
  } catch (e) {
    document.body.innerHTML = `<div class="empty" style="margin-top:60px">⛔ ${e.message === "forbidden" ? "Admins only." : e.message}</div>`;
  }
}

async function loadUsers() {
  const q = document.getElementById("userSearch").value.trim();
  const data = await api("/api/admin/users?q=" + encodeURIComponent(q));
  document.getElementById("usersList").innerHTML = data.users.map(u => `
    <div class="list-link">
      <div>
        <div style="font-weight:600">${esc(u.name || "—")} ${u.username ? "@" + esc(u.username) : ""}</div>
        <div class="file-meta">ID ${u.id} · ${u.files_count} files · ${u.banned ? "🔴 banned" : "🟢 active"}</div>
      </div>
      <div>${u.banned
        ? `<span onclick="unban(${u.id})">✅ Unban</span>`
        : `<span onclick="ban(${u.id})">🚫 Ban</span>`}</div>
    </div>`).join("") || `<div class="empty">No users found.</div>`;
}
document.getElementById("userSearch").addEventListener("input", () => {
  clearTimeout(window._us);
  window._us = setTimeout(loadUsers, 350);
});
async function ban(id) { await api(`/api/admin/users/${id}/ban`, { method: "POST" }); toast("🚫 Banned"); loadUsers(); }
async function unban(id) { await api(`/api/admin/users/${id}/unban`, { method: "POST" }); toast("✅ Unbanned"); loadUsers(); }

async function loadForceJoin() {
  const data = await api("/api/admin/force-join");
  document.getElementById("fjList").innerHTML = data.channels.length ? data.channels.map(c => `
    <div class="list-link">
      <div>
        <div style="font-weight:600">${esc(c.title || c.chat_id)}</div>
        <div class="file-meta">${c.chat_id} · ${c.enabled ? "🟢 enabled" : "⚪ disabled"}</div>
      </div>
      <div style="display:flex;gap:10px">
        <span onclick="toggleFj(${c.id},${c.enabled ? 0 : 1})">${c.enabled ? "⏸" : "▶️"}</span>
        <span onclick="removeFj(${c.id})">🗑</span>
      </div>
    </div>`).join("") : `<div class="empty">No force-join requirements set.</div>`;
}
document.getElementById("fjAdd").addEventListener("click", async () => {
  const chat_id = document.getElementById("fjChatId").value.trim();
  const title = document.getElementById("fjTitle").value.trim();
  const url = document.getElementById("fjUrl").value.trim();
  if (!chat_id || !url) return toast("Chat ID and URL required");
  await api("/api/admin/force-join", { method: "POST", body: JSON.stringify({ chat_id, title, url }) });
  document.getElementById("fjChatId").value = "";
  document.getElementById("fjTitle").value = "";
  document.getElementById("fjUrl").value = "";
  toast("✅ Added"); loadForceJoin();
});
async function toggleFj(id, enabled) {
  await api(`/api/admin/force-join/${id}`, { method: "PATCH", body: JSON.stringify({ enabled: !!enabled }) });
  loadForceJoin();
}
async function removeFj(id) {
  if (!confirm("Remove this requirement?")) return;
  await api(`/api/admin/force-join/${id}`, { method: "DELETE" });
  loadForceJoin();
}

document.getElementById("bcSend").addEventListener("click", async () => {
  const message = document.getElementById("bcMessage").value.trim();
  const audience = document.getElementById("bcAudience").value;
  if (!message) return toast("Write a message first");
  const { job_id, total } = await api("/api/admin/broadcast", {
    method: "POST", body: JSON.stringify({ message, audience }),
  });
  document.getElementById("bcStatus").textContent = `Sending to ${total} users...`;
  const poll = setInterval(async () => {
    const j = await api(`/api/admin/broadcast/${job_id}`);
    document.getElementById("bcStatus").textContent =
      `✅ Sent ${j.sent} · ❌ Failed ${j.failed} · 🚫 Blocked ${j.blocked} / ${j.total}`;
    if (j.done) clearInterval(poll);
  }, 1500);
});

async function loadAudit() {
  const data = await api("/api/admin/audit-log");
  document.getElementById("auditList").innerHTML = data.log.length ? data.log.map(a => `
    <div class="file-row">
      <div class="file-icon">📜</div>
      <div class="file-info">
        <div class="file-name">${esc(a.action)} ${a.target ? "→ " + esc(a.target) : ""}</div>
        <div class="file-meta">Admin ${a.admin_id} · ${new Date(a.created_at).toLocaleString()}</div>
      </div>
    </div>`).join("") : `<div class="empty">No admin actions logged yet.</div>`;
}

loadStats();
