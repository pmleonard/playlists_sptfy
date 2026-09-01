import { api, showConfirm, showToast } from "/static/app.js";

const GENRE_TAGS = [
  "rock",
  "pop",
  "oldies",
  "reggae",
  "country",
  "hiphop",
  "world",
  "folk",
  "edm",
  "classical",
  "rnb",
  "jazz",
  "soul",
];
const CATEGORIES = [
  { key: "mismatch", label: "Mismatch" },
  { key: "missing", label: "Missing" },
  { key: "multiple", label: "Multiple" },
];

let rows = [];
const dismissed = new Set(); // session-only, "multiple" rows only
let activeTags = new Set();

export async function render(container) {
  container.innerHTML = `<p class="loading">Loading…</p>`;
  try {
    rows = await api("GET", "/api/genre-review/");
  } catch (err) {
    container.innerHTML = `<p class="error-msg">Error: ${err.message}</p>`;
    return;
  }
  activeTags = new Set();
  draw(container);
}

function matchesTagFilter(r) {
  if (!activeTags.size) return true;
  // Missing rows have no current tag by definition — filter those by the
  // proposed genre (Proposed column) instead.
  if (r.category === "missing") return activeTags.has(r.proposed_genre);
  return (r.current_tags || []).some((t) => activeTags.has(t));
}

function draw(container) {
  const visible = rows.filter((r) => !dismissed.has(r.idx));
  const filtered = visible.filter(matchesTagFilter);
  const byCategory = Object.fromEntries(
    CATEGORIES.map(({ key }) => [key, filtered.filter((r) => r.category === key)])
  );

  container.innerHTML = `
    <div class="card">
      <div class="tag-filters" id="tag-filters">
        ${GENRE_TAGS.map(
          (t) =>
            `<button class="tag-btn ${activeTags.has(t) ? "active" : ""}" data-tag="${t}">${t}</button>`
        ).join("")}
      </div>
    </div>
    ${CATEGORIES.map(({ key, label }) => sectionHtml(key, label, byCategory[key])).join("")}`;

  container.querySelector("#tag-filters").addEventListener("click", (e) => {
    const btn = e.target.closest(".tag-btn");
    if (!btn) return;
    const tag = btn.dataset.tag;
    if (activeTags.has(tag)) activeTags.delete(tag);
    else activeTags.add(tag);
    draw(container);
  });

  const dismissAllBtn = container.querySelector("[data-action='dismiss-all-mismatch']");
  if (dismissAllBtn) {
    dismissAllBtn.addEventListener("click", () => {
      handleDismissMismatch(
        container,
        byCategory.mismatch.map((r) => r.idx)
      );
    });
  }

  const applyAllBtn = container.querySelector("[data-action='apply-proposed-all']");
  if (applyAllBtn) {
    applyAllBtn.addEventListener("click", () => {
      handleApplyProposedBulk(
        container,
        byCategory.missing.map((r) => r.idx)
      );
    });
  }

  container.querySelectorAll("[data-action='save']").forEach((btn) => {
    btn.addEventListener("click", () => handleSave(container, btn));
  });
  container.querySelectorAll("[data-action='dismiss']").forEach((btn) => {
    btn.addEventListener("click", () => handleDismiss(container, btn));
  });
  container.querySelectorAll("[data-action='dismiss-mismatch']").forEach((btn) => {
    btn.addEventListener("click", () =>
      handleDismissMismatch(container, [parseInt(btn.dataset.idx, 10)])
    );
  });
}

function sectionHtml(key, label, sectionRows) {
  return `
    <div class="card">
      <div class="card-header">
        <strong>${label} (${sectionRows.length})</strong>
        ${bulkActionHtml(key, sectionRows)}
      </div>
      ${sectionRows.length ? tableHtml(key, sectionRows) : `<p style="color:#888">No ${label.toLowerCase()} songs found.</p>`}
    </div>`;
}

function bulkActionHtml(key, sectionRows) {
  const enabled = activeTags.size > 0 && sectionRows.length > 0;
  const countSuffix = activeTags.size ? ` (${sectionRows.length})` : "";

  if (key === "mismatch") {
    return `<button class="btn btn-danger btn-sm" data-action="dismiss-all-mismatch" ${enabled ? "" : "disabled"}>Dismiss All Filtered${countSuffix}</button>`;
  }
  if (key === "missing") {
    return `<button class="btn btn-primary btn-sm" data-action="apply-proposed-all" ${enabled ? "" : "disabled"}>Apply Proposed Tag to All Filtered${countSuffix}</button>`;
  }
  return "";
}

function tableHtml(category, sectionRows) {
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
            <th>Proposed</th>
            <th>Fix</th>
          </tr>
        </thead>
        <tbody>
          ${sectionRows.map((r) => rowHtml(category, r)).join("")}
        </tbody>
      </table>
    </div>`;
}

function dismissButtonHtml(category, r) {
  if (category === "missing") return ""; // not applicable — nothing to "not an issue" about a blank tag
  if (category === "mismatch") {
    return `<button class="btn btn-sm btn-secondary" data-action="dismiss-mismatch" data-idx="${r.idx}">Dismiss</button>`;
  }
  return `<button class="btn btn-sm btn-secondary" data-action="dismiss" data-idx="${r.idx}">Dismiss</button>`;
}

function rowHtml(category, r) {
  const options = [`<option value="">(none)</option>`]
    .concat(
      GENRE_TAGS.map(
        (t) => `<option value="${t}" ${t === r.proposed_genre ? "selected" : ""}>${t}</option>`
      )
    )
    .join("");

  return `
    <tr data-idx="${r.idx}">
      <td title="${escHtml(r.artist)}">${escHtml(r.artist)}</td>
      <td title="${escHtml(r.title)}">${escHtml(r.title)}</td>
      <td title="${escHtml(r.album)}">${escHtml(r.album)}</td>
      <td>${fmtDate(r.released)}</td>
      <td>${escHtml((r.current_tags || []).join(", "))}</td>
      <td>${escHtml(r.proposed_genre || "")}</td>
      <td>
        <div class="flex-row">
          <select class="era-select">${options}</select>
          <button class="btn btn-primary btn-sm" data-action="save" data-idx="${r.idx}">Save</button>
          ${dismissButtonHtml(category, r)}
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
    await api("PATCH", `/api/genre-review/${idx}`, { tag: value });
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

async function handleDismissMismatch(container, idxs) {
  if (!idxs.length) return;
  if (idxs.length > 1) {
    const ok = await showConfirm(
      `Permanently dismiss ${idxs.length} mismatched song(s) matching the current filter? Unlike other dismiss actions, this persists — they won't reappear on reload.`
    );
    if (!ok) return;
  }

  try {
    await api("POST", "/api/genre-review/dismiss-mismatch", { idxs });
    showToast(idxs.length > 1 ? `${idxs.length} mismatch(es) dismissed` : "Dismissed");
    const idxSet = new Set(idxs);
    rows = rows.filter((r) => !idxSet.has(r.idx));
    draw(container);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleApplyProposedBulk(container, idxs) {
  if (!idxs.length) return;
  const ok = await showConfirm(
    `Apply the proposed genre tag to ${idxs.length} missing song(s) matching the current filter?`
  );
  if (!ok) return;

  try {
    const result = await api("POST", "/api/genre-review/apply-proposed-bulk", { idxs });
    showToast(`${result.changed} tag(s) applied`);
    const idxSet = new Set(idxs);
    rows = rows.filter((r) => !idxSet.has(r.idx));
    draw(container);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function fmtDate(d) {
  if (!d) return "";
  return String(d).slice(0, 10);
}

function escHtml(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
