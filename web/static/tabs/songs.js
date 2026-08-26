import { api, showToast } from "/static/app.js";

let allSongs = [];
let activeTags = new Set();
let columnFilters = {};

export async function render(container) {
  container.innerHTML = `<p class="loading">Loading songs…</p>`;
  try {
    allSongs = await api("GET", "/api/songs/");
  } catch (err) {
    container.innerHTML = `<p class="error-msg">Error: ${err.message}</p>`;
    return;
  }
  activeTags = new Set();
  columnFilters = {};
  drawShell(container);
  renderTable(container);
}

function drawShell(container) {
  const tags = collectTags(allSongs);
  container.innerHTML = `
    <div class="tag-filters" id="tag-filters">
      ${tags.map((t) => `<button class="tag-btn" data-tag="${t}">${t}</button>`).join("")}
    </div>
    <div class="status-bar" id="status"></div>
    <div style="overflow-x:auto">
      <table id="songs-table">
        <thead>
          <tr>
            <th>Artist</th><th>Title</th><th>Album</th>
            <th>Released</th><th>Duration</th><th>Track</th><th>Tags</th><th>Link</th>
          </tr>
          <tr class="filter-row">
            <td><input data-col="artist" placeholder="filter…"></td>
            <td><input data-col="title" placeholder="filter…"></td>
            <td><input data-col="album" placeholder="filter…"></td>
            <td><input data-col="released" placeholder="filter…"></td>
            <td><input data-col="duration" placeholder="filter…"></td>
            <td><input data-col="track" placeholder="filter…"></td>
            <td><input data-col="tags" placeholder="filter…"></td>
            <td></td>
          </tr>
        </thead>
        <tbody id="songs-body"></tbody>
      </table>
    </div>`;

  container.querySelector("#tag-filters").addEventListener("click", (e) => {
    const btn = e.target.closest(".tag-btn");
    if (!btn) return;
    const tag = btn.dataset.tag;
    if (activeTags.has(tag)) activeTags.delete(tag);
    else activeTags.add(tag);
    btn.classList.toggle("active", activeTags.has(tag));
    renderTable(container);
  });

  container.querySelectorAll(".filter-row input").forEach((inp) => {
    inp.addEventListener("input", () => {
      columnFilters[inp.dataset.col] = inp.value.toLowerCase();
      renderTable(container);
    });
  });
}

function renderTable(container) {
  const filtered = allSongs.filter((s) => {
    if (activeTags.size > 0) {
      const songTags = (s.tags || "").split(",").map((t) => t.trim());
      if (!songTags.some((t) => activeTags.has(t))) return false;
    }
    for (const [col, val] of Object.entries(columnFilters)) {
      if (!val) continue;
      const cell = String(s[col] ?? "").toLowerCase();
      if (!cell.includes(val)) return false;
    }
    return true;
  });

  const tbody = container.querySelector("#songs-body");
  tbody.innerHTML = filtered.map((s) => `
    <tr>
      <td title="${escHtml(s.artist || "")}">${escHtml(s.artist || "")}</td>
      <td title="${escHtml(s.title || "")}">${escHtml(s.title || "")}</td>
      <td title="${escHtml(s.album || "")}">${escHtml(s.album || "")}</td>
      <td>${fmtDate(s.released)}</td>
      <td>${fmtDuration(s.duration)}</td>
      <td>${s.track ?? ""}</td>
      <td title="${escHtml(s.tags || "")}">${escHtml(s.tags || "")}</td>
      <td>${s.link ? `<a href="${escHtml(s.link)}" target="_blank" rel="noopener">open</a>` : ""}</td>
    </tr>`).join("");

  container.querySelector("#status").textContent =
    `Showing ${filtered.length} of ${allSongs.length} songs`;
}

function collectTags(songs) {
  const set = new Set();
  for (const s of songs) {
    if (s.tags) s.tags.split(",").forEach((t) => set.add(t.trim()));
  }
  return [...set].sort();
}

function fmtDuration(secs) {
  const n = parseInt(secs, 10);
  if (isNaN(n)) return secs ?? "";
  return `${Math.floor(n / 60)}:${String(n % 60).padStart(2, "0")}`;
}

function fmtDate(d) {
  if (!d) return "";
  return String(d).slice(0, 10);
}

function escHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
