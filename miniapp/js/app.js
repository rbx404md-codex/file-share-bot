const tg = window.Telegram?.WebApp;
tg?.ready();
tg?.expand();

const initData = tg?.initData || "";

async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": initData,
      ...(opts.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `HTTP ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}

function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 1800);
}

function openModal(id) { document.getElementById(id).classList.add("show"); }
function closeModal(id) { document.getElementById(id).classList.remove("show"); }

function esc(s) {
  return (s || "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

const TYPE_ICON = {
  document: "📄", video: "🎥", photo: "🖼", audio: "🎵",
  voice: "🎤", animation: "🎞", sticker: "🧩", text: "📝",
};

let ME = null;
let currentType = "";
let currentFolder = "__any__";
let currentModalFile = null;
let selectMode = false;
let selectedIds = new Set();
let folderPickerTarget = null; // 'bulk' | fileId
let foldersCache = [];

// ── navigation ──────────────────────────────────────────
document.querySelectorAll(".nav-item").forEach(el => {
  el.addEventListener("click", () => goPage(el.dataset.page));
});

function goPage(name) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  const page = document.getElementById("page-" + name);
  if (page) page.classList.add("active");
  const nav = document.querySelector(`.nav-item[data-page="${name}"]`);
  if (nav) nav.classList.add("active");
  if (name === "files") loadFiles();
  if (name === "favorites") loadFavorites();
  if (name === "collections") loadCollections();
  if (name === "trash") loadTrash();
  if (name === "profile") loadProfile();
}

// ── home ────────────────────────────────────────────────
async function loadHome() {
  ME = await api("/api/me");
  document.getElementById("helloText").textContent =
    `Hello, ${esc(ME.name || "RBX404 User")} 👋`;
  const s = ME.stats;
  document.getElementById("statsGrid").innerHTML = `
    <div class="stat"><div class="n">${s.files}</div><div class="l">📁 Files</div></div>
    <div class="stat"><div class="n">${s.downloads}</div><div class="l">⬇️ Downloads</div></div>
    <div class="stat"><div class="n">${s.favorites}</div><div class="l">⭐ Favorites</div></div>
    <div class="stat"><div class="n">${s.storage_h}</div><div class="l">💾 Storage</div></div>
  `;
  if (ME.is_admin) document.getElementById("adminLinkWrap").style.display = "block";
  document.getElementById("langSelect").value = ME.lang;

  const act = await api("/api/activity");
  const list = document.getElementById("activityList");
  if (!act.activity.length) {
    list.innerHTML = `<div class="empty">No activity yet — send a file to get started.</div>`;
  } else {
    list.innerHTML = act.activity.map(a => `
      <div class="file-row">
        <div class="file-icon">${a.kind === "upload" ? "📤" : a.kind === "trash" ? "🗑" : "•"}</div>
        <div class="file-info">
          <div class="file-name">${esc(a.label || a.kind)}</div>
          <div class="file-meta">${a.kind} · ${new Date(a.created_at).toLocaleString()}</div>
        </div>
      </div>`).join("");
  }
}

document.getElementById("homeSearch").addEventListener("keydown", e => {
  if (e.key === "Enter") {
    document.getElementById("fileSearch").value = e.target.value;
    goPage("files");
  }
});

// ── files ───────────────────────────────────────────────
function fileRowHtml(f) {
  if (selectMode) {
    const on = selectedIds.has(f.id);
    return `
      <div class="file-row selectable" data-id="${f.id}" onclick="toggleSelect('${f.id}')">
        <div class="check-box ${on ? "on" : ""}">${on ? "✓" : ""}</div>
        <div class="file-icon">${TYPE_ICON[f.type] || "📦"}</div>
        <div class="file-info">
          <div class="file-name">${esc(f.name)}</div>
          <div class="file-meta">${f.size_h} · ${f.downloads} downloads${f.disabled ? " · ⛔ disabled" : ""}</div>
        </div>
      </div>`;
  }
  return `
    <div class="file-row" data-id="${f.id}">
      <div class="file-icon">${TYPE_ICON[f.type] || "📦"}</div>
      <div class="file-info" onclick="openFileModal('${f.id}')">
        <div class="file-name">${esc(f.name)}</div>
        <div class="file-meta">${f.size_h} · ${f.downloads} downloads${f.disabled ? " · ⛔ disabled" : ""}</div>
      </div>
      <div class="fav-star ${f.favorite ? "on" : ""}" onclick="toggleFav(this,'${f.id}',${f.favorite})">★</div>
    </div>`;
}

async function loadFolders() {
  const data = await api("/api/folders?parent_id=root");
  foldersCache = data.folders;
  const opts = foldersCache.map(fo => `<option value="${fo.id}">📁 ${esc(fo.name)}</option>`).join("");
  const filterSel = document.getElementById("folderFilter");
  const keep = filterSel.value;
  filterSel.innerHTML = `<option value="__any__">📁 All Folders</option><option value="root">📂 Root (no folder)</option>${opts}`;
  filterSel.value = keep || "__any__";
  const fmSel = document.getElementById("fmFolder");
  fmSel.innerHTML = `<option value="">📂 Root (no folder)</option>${opts}`;
}

async function loadFiles() {
  if (!foldersCache.length) await loadFolders().catch(() => {});
  const q = document.getElementById("fileSearch").value.trim();
  const params = new URLSearchParams({ pp: 50 });
  if (currentType) params.set("type", currentType);
  if (q) params.set("q", q);
  if (currentFolder !== "__any__") params.set("folder_id", currentFolder);
  const data = await api("/api/files?" + params.toString());
  const el = document.getElementById("filesList");
  el.innerHTML = data.files.length
    ? data.files.map(fileRowHtml).join("")
    : `<div class="empty">📭 No files here yet.<br>Send anything to the bot to create one.</div>`;
}

document.getElementById("folderFilter").addEventListener("change", e => {
  currentFolder = e.target.value;
  loadFiles();
});
document.getElementById("newFolderBtn").addEventListener("click", async () => {
  const name = prompt("Folder name:");
  if (!name) return;
  await api("/api/folders", { method: "POST", body: JSON.stringify({ name }) });
  await loadFolders();
  toast("📁 Folder created");
});

// ── bulk select ─────────────────────────────────────────
document.getElementById("selectModeBtn").addEventListener("click", () => {
  selectMode = !selectMode;
  document.getElementById("selectModeBtn").style.color = selectMode ? "var(--red2)" : "";
  if (!selectMode) exitSelectMode(false);
  else { document.getElementById("bulkBar").classList.add("show"); loadFiles(); }
});
function toggleSelect(fid) {
  if (selectedIds.has(fid)) selectedIds.delete(fid); else selectedIds.add(fid);
  document.getElementById("bulkCount").textContent = `${selectedIds.size} selected`;
  loadFiles();
}
function exitSelectMode(reload = true) {
  selectMode = false;
  selectedIds.clear();
  document.getElementById("selectModeBtn").style.color = "";
  document.getElementById("bulkBar").classList.remove("show");
  if (reload) loadFiles();
}
async function bulkFavorite() {
  if (!selectedIds.size) return;
  await Promise.all([...selectedIds].map(fid => api(`/api/files/${fid}/favorite`, { method: "POST" })));
  toast(`⭐ Favorited ${selectedIds.size} file(s)`);
  exitSelectMode();
}
async function bulkTrash() {
  if (!selectedIds.size) return;
  if (!confirm(`Move ${selectedIds.size} file(s) to Trash?`)) return;
  await Promise.all([...selectedIds].map(fid => api(`/api/files/${fid}/trash`, { method: "POST" })));
  toast(`🗑 Trashed ${selectedIds.size} file(s)`);
  exitSelectMode();
}

// ── folder picker modal (shared: bulk move + single-file modal shortcut) ──
async function openFolderPicker(target) {
  if (target === "bulk" && !selectedIds.size) return;
  folderPickerTarget = target;
  if (!foldersCache.length) await loadFolders().catch(() => {});
  document.getElementById("folderPickerList").innerHTML = foldersCache.map(fo => `
    <div class="folder-pick-row" onclick="pickFolder('${fo.id}')">📁 ${esc(fo.name)}</div>
  `).join("") || `<div class="empty">No folders yet — create one first.</div>`;
  openModal("folderPickerBg");
}
async function pickFolder(folderId) {
  closeModal("folderPickerBg");
  if (folderPickerTarget === "bulk") {
    await Promise.all([...selectedIds].map(fid =>
      api(`/api/files/${fid}`, { method: "PATCH", body: JSON.stringify({ folder_id: folderId }) })));
    toast(`📁 Moved ${selectedIds.size} file(s)`);
    exitSelectMode();
  }
}

document.getElementById("fileSearch").addEventListener("input", debounce(loadFiles, 350));
document.querySelectorAll("#typeTabs .tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll("#typeTabs .tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    currentType = tab.dataset.type;
    loadFiles();
  });
});

function debounce(fn, ms) {
  let h;
  return (...a) => { clearTimeout(h); h = setTimeout(() => fn(...a), ms); };
}

async function toggleFav(el, fid, isFav) {
  try {
    if (isFav) await api(`/api/files/${fid}/favorite`, { method: "DELETE" });
    else await api(`/api/files/${fid}/favorite`, { method: "POST" });
    el.classList.toggle("on");
    el.setAttribute("onclick", `toggleFav(this,'${fid}',${!isFav})`);
    toast(isFav ? "Removed from favorites" : "Added to favorites");
  } catch (e) { toast("Error: " + e.message); }
}

// ── file modal ──────────────────────────────────────────
async function openFileModal(fid) {
  const f = await api(`/api/files/${fid}`);
  currentModalFile = f;
  if (!foldersCache.length) await loadFolders().catch(() => {});
  document.getElementById("fmName").textContent = f.name;
  document.getElementById("fmMeta").textContent =
    `${f.size_h} · ${f.type} · ${f.views} views · ${f.downloads} downloads`;
  document.getElementById("fmExpiry").value =
    ["never", "1h", "1d", "7d", "30d"].includes(f.expiry_type) ? f.expiry_type : "never";
  document.getElementById("fmFolder").value = f.folder_id || "";
  document.getElementById("fmLimit").value = f.download_limit || 0;
  document.getElementById("fmPassword").value = "";
  document.getElementById("fmOneTime").textContent = "One-time: " + (f.one_time ? "On" : "Off");
  document.getElementById("fmOneTime").dataset.v = f.one_time ? "1" : "0";
  document.getElementById("fmDisabled").textContent = "Status: " + (f.disabled ? "Disabled" : "Active");
  document.getElementById("fmDisabled").dataset.v = f.disabled ? "1" : "0";
  openModal("fileModalBg");
}

document.getElementById("fmOneTime").addEventListener("click", function () {
  const on = this.dataset.v === "1";
  this.dataset.v = on ? "0" : "1";
  this.textContent = "One-time: " + (on ? "Off" : "On");
});
document.getElementById("fmDisabled").addEventListener("click", function () {
  const on = this.dataset.v === "1";
  this.dataset.v = on ? "0" : "1";
  this.textContent = "Status: " + (on ? "Active" : "Disabled");
});

const EXPIRY_MS = { "1h": 3600e3, "1d": 86400e3, "7d": 7 * 86400e3, "30d": 30 * 86400e3 };

document.getElementById("fmSave").addEventListener("click", async () => {
  const expiry_type = document.getElementById("fmExpiry").value;
  const body = {
    expiry_type,
    expires_at: expiry_type === "never" ? null : new Date(Date.now() + EXPIRY_MS[expiry_type]).toISOString(),
    download_limit: parseInt(document.getElementById("fmLimit").value || "0", 10),
    one_time: document.getElementById("fmOneTime").dataset.v === "1",
    disabled: document.getElementById("fmDisabled").dataset.v === "1",
    folder_id: document.getElementById("fmFolder").value || null,
  };
  const pw = document.getElementById("fmPassword").value;
  if (pw) body.password = pw;
  try {
    await api(`/api/files/${currentModalFile.id}`, { method: "PATCH", body: JSON.stringify(body) });
    toast("✅ Saved");
    closeModal("fileModalBg");
    loadFiles();
  } catch (e) { toast("Error: " + e.message); }
});

document.getElementById("fmCopy").addEventListener("click", () => {
  navigator.clipboard?.writeText(currentModalFile.share_url).then(() => toast("🔗 Link copied"));
  tg?.showPopup?.({ message: currentModalFile.share_url });
});
document.getElementById("fmQr").addEventListener("click", () => {
  window.open(`/api/files/${currentModalFile.id}/qr.png`, "_blank");
});
document.getElementById("fmTrash").addEventListener("click", async () => {
  await api(`/api/files/${currentModalFile.id}/trash`, { method: "POST" });
  toast("🗑 Moved to Trash");
  closeModal("fileModalBg");
  loadFiles();
});

// ── favorites ───────────────────────────────────────────
async function loadFavorites() {
  const data = await api("/api/favorites");
  const el = document.getElementById("favList");
  el.innerHTML = data.files.length
    ? data.files.map(fileRowHtml).join("")
    : `<div class="empty">⭐ No favorites yet.</div>`;
}

// ── collections ─────────────────────────────────────────
async function loadCollections() {
  const data = await api("/api/collections");
  const el = document.getElementById("collectionsList");
  el.innerHTML = data.collections.length ? data.collections.map(c => `
    <div class="list-link">
      <div>
        <div style="font-weight:600">📦 ${esc(c.name)}</div>
        <div class="file-meta">${c.file_count} file(s) · ${c.is_public ? "public" : "private"}</div>
      </div>
      <div style="display:flex;gap:10px">
        <span onclick="navigator.clipboard.writeText('${c.share_url}');toast('🔗 Link copied')">🔗</span>
        <span onclick="deleteCollection('${c.id}')">🗑</span>
      </div>
    </div>`).join("") : `<div class="empty">📦 No collections yet.</div>`;
}

document.getElementById("newCollectionBtn").addEventListener("click", async () => {
  const name = prompt("Collection name:");
  if (!name) return;
  await api("/api/collections", { method: "POST", body: JSON.stringify({ name, is_public: true }) });
  loadCollections();
});

async function deleteCollection(cid) {
  if (!confirm("Delete this collection? Files stay, only the pack is removed.")) return;
  await api(`/api/collections/${cid}`, { method: "DELETE" });
  loadCollections();
}

// ── trash ───────────────────────────────────────────────
document.getElementById("trashLink").addEventListener("click", () => goPage("trash"));

async function loadTrash() {
  const data = await api("/api/trash");
  document.getElementById("trashNote").textContent =
    `Files are kept for ${data.retention_days} days before permanent deletion.`;
  const el = document.getElementById("trashList");
  el.innerHTML = data.files.length ? data.files.map(f => `
    <div class="list-link">
      <div>
        <div style="font-weight:600">${TYPE_ICON[f.type] || "📦"} ${esc(f.name)}</div>
        <div class="file-meta">${f.size_h}</div>
      </div>
      <div style="display:flex;gap:10px">
        <span onclick="restoreFile('${f.id}')">♻️</span>
        <span onclick="deleteForever('${f.id}')">🗑</span>
      </div>
    </div>`).join("") : `<div class="empty">🗑 Recycle Bin is empty.</div>`;
}
async function restoreFile(fid) {
  await api(`/api/files/${fid}/restore`, { method: "POST" });
  toast("♻️ Restored");
  loadTrash();
}
async function deleteForever(fid) {
  if (!confirm("Permanently delete this file? This cannot be undone.")) return;
  await api(`/api/files/${fid}`, { method: "DELETE" });
  toast("🗑 Deleted forever");
  loadTrash();
}

// ── profile ─────────────────────────────────────────────
async function loadProfile() {
  if (!ME) ME = await api("/api/me");
  document.getElementById("profileCard").innerHTML = `
    <div style="font-weight:700;font-size:16px">👤 ${esc(ME.name || "RBX404 User")}</div>
    <div class="file-meta" style="margin-top:4px">ID: ${ME.id}</div>
    <div class="stats-grid">
      <div class="stat"><div class="n">${ME.stats.files}</div><div class="l">Files</div></div>
      <div class="stat"><div class="n">${ME.stats.downloads}</div><div class="l">Downloads</div></div>
    </div>`;
}
document.getElementById("langSelect").addEventListener("change", async e => {
  await api("/api/me/lang", { method: "POST", body: JSON.stringify({ lang: e.target.value }) });
  toast("✅ Language updated");
});

// ── deep link: #file/<token> ────────────────────────────
function handleHash() {
  const h = location.hash;
  if (h.startsWith("#file/")) {
    const token = h.slice(6);
    goPage("files");
    openFileModal(token).catch(() => toast("File not found"));
  }
}

// ── init ────────────────────────────────────────────────
(async function init() {
  if (!initData) {
    document.body.innerHTML = `<div class="empty" style="margin-top:60px">
      ⚠️ Please open this from the RBX404 Telegram bot.</div>`;
    return;
  }
  try {
    await loadHome();
    handleHash();
  } catch (e) {
    toast("Error: " + e.message);
  }
})();
