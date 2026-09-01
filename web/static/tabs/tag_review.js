import { api, showToast } from "/static/app.js";

const ERA_TAGS = ["50s", "60s", "70s", "80s", "90s", "2000s", "2010s"];
const CATEGORIES = [
  { key: "mismatch", label: "Mismatch" },
  { key: "missing", label: "Missing" },
  { key: "multiple", label: "Multiple" },
];

let rows = [];
const dismissed = new Set();
let activeTags = new Set();

export async function render(container) {
  container.innerHTML = `<p class="loading">Loading…</p>`;
  try {
    rows = await api("GET", "/api/tag-review/");
  } catch (err) {
    container.innerHTML = `<p class="error-msg">Error: ${err.message}</p>`;
    return;
  }
  activeTags = new Set();
  draw(container);
}

function draw(container) {
  const visible = rows.filter((r) => !dismissed.has(r.idx));
  const filtered = activeTags.size
    ? visible.filter((r) => (r.current_tags || []).some((t) => activeTags.has(t)))
    : visible;

  container.innerHTML = `
    <div class="card">
      <div class="tag-filters" id="tag-filters">
        ${ERA_TAGS.map(
          (t) =>
            `<button class="tag-btn ${activeTags.has(t) ? "active" : ""}" data-tag="${t}">${t}</button>`
        ).join("")}
      </div>
      <div class="flex-row mt-8">
        <button class="btn btn-danger btn-sm" id="dismiss-all-btn" ${activeTags.size === 0 ? "disabled" : ""}>
          Dismiss All Filtered${activeTags.size ? ` (${filtered.length})` : ""}
        </button>
      </div>
    </div>
    ${CATEGORIES.map(({ key, label }) => sectionHtml(key, label, filtered)).join("")}`;

  container.querySelector("#tag-filters").addEventListener("click", (e) => {
    const btn = e.target.closest(".tag-btn");
    if (!btn) return;
    const tag = btn.dataset.tag;
    if (activeTags.has(tag)) activeTags.delete(tag);
    else activeTags.add(tag);
    draw(container);
  });

  container.querySelector("#dismiss-all-btn").addEventListener("click", () => {
    filtered.forEach((r) => dismissed.add(r.idx));
    draw(container);
  });

  container.querySelectorAll("[data-action='save']").forEach((btn) => {
    btn.addEventListener("click", () => handleSave(container, btn));
  });
  container.querySelectorAll("[data-action='dismiss']").forEach((btn) => {
    btn.addEventListener("click", () => handleDismiss(container, btn));
  });
}

function sectionHtml(key, label, visible) {
  const sectionRows = visible.filter((r) => r.category === key);
  return `
    <div class="card">
      <div class="card-header"><strong>${label} (${sectionRows.length})</strong></div>
      ${sectionRows.length ? tableHtml(sectionRows) : `<p style="color:#888">No ${label.toLowerCase()} songs found.</p>`}
    </div>`;
}

function tableHtml(sectionRows) {
  return `
    <div style="overflow-x:auto">
      <table>
        <thead>
          <tr>
            <th>Artist</th>
            <th>Title</th>
            <th>Album</th>
            <th>Released</th>
            <th>Current Tag(s)</th>
            <th>Expected</th>
            <th>Reissue?</th>
            <th>Candidate Yr</th>
            <th>Fix</th>
          </tr>
        </thead>
        <tbody>
          ${sectionRows.map(rowHtml).join("")}
        </tbody>
      </table>
    </div>`;
}

function rowHtml(r) {
  const options = [`<option value="">(none)</option>`]
    .concat(
      ERA_TAGS.map(
        (t) => `<option value="${t}" ${t === r.expected_decade ? "selected" : ""}>${t}</option>`
      )
    )
    .join("");

  return `
    <tr data-idx="${r.idx}">
      <td title="${escHtml(r.artist)}">${escHtml(r.artist)}</td>
      <td title="${escHtml(r.title)}">${escHtml(r.title)}</td>
      <td title="${escHtml(r.album)}">${escHtml(r.album)}${r.likely_reissue ? ` <span class="badge-warn">likely reissue</span>` : ""}</td>
      <td>${fmtDate(r.released)}</td>
      <td>${escHtml((r.current_tags || []).join(", "))}</td>
      <td>${escHtml(r.expected_decade || "")}</td>
      <td>${r.likely_reissue ? "Yes" : ""}</td>
      <td>${r.candidate_year ?? ""}</td>
      <td>
        <div class="flex-row">
          <select class="era-select">${options}</select>
          <button class="btn btn-primary btn-sm" data-action="save" data-idx="${r.idx}">Save</button>
          <button class="btn btn-secondary btn-sm" data-action="dismiss" data-idx="${r.idx}">Dismiss</button>
        </div>
      </td>
    </tr>`;
}

async function handleSave(container, btn) {
  const idx = parseInt(btn.dataset.idx, 10);
  const row = btn.closest("tr");
  const select = row.querySelector(".era-select");
  const value = select.value || null;

  btn.disabled = true;
  try {
    await api("PATCH", `/api/tag-review/${idx}`, { tag: value });
    showToast("Tag saved");
    rows = rows.filter((r) => r.idx !== idx);
    draw(container);
  } catch (err) {
    showToast(err.message, "error");
    btn.disabled = false;
  }
}

function handleDismiss(container, btn) {
  const idx = parseInt(btn.dataset.idx, 10);
  dismissed.add(idx);
  draw(container);
}

function fmtDate(d) {
  if (!d) return "";
  return String(d).slice(0, 10);
}

function escHtml(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
