import { api, showToast } from "/static/app.js";

let rows = [];
let filters = { minTracks: "", artist: "", album: "" };
let openIndex = null;

export async function render(container) {
  container.innerHTML = `<p class="loading">Loading…</p>`;
  try {
    rows = await api("GET", "/api/albums/");
  } catch (err) {
    container.innerHTML = `<p class="error-msg">Error: ${err.message}</p>`;
    return;
  }
  filters = { minTracks: "", artist: "", album: "" };
  openIndex = null;
  draw(container);
}

function draw(container) {
  if (!rows.length) {
    container.innerHTML = `<p style="color:#888">No albums found.</p>`;
    return;
  }

  const trackCounts = [...new Set(rows.map((r) => r.track_count))].sort((a, b) => a - b);

  container.innerHTML = `
    <div class="card">
      <div class="flex-row" style="flex-wrap:wrap;gap:20px">
        <label class="flex-row" style="gap:6px">
          Artist:
          <input type="text" id="filter-artist" placeholder="filter…">
        </label>
        <label class="flex-row" style="gap:6px">
          Album:
          <input type="text" id="filter-album" placeholder="filter…">
        </label>
        <label class="flex-row" style="gap:6px">
          Tracks (at least):
          <select id="filter-min-tracks">
            <option value="">All</option>
            ${trackCounts.map((n) => `<option value="${n}">${n}</option>`).join("")}
          </select>
        </label>
        <span id="filter-status" style="color:#888;margin-left:auto"></span>
      </div>
    </div>
    <div id="row-list"></div>`;

  const artistInput = container.querySelector("#filter-artist");
  const albumInput = container.querySelector("#filter-album");
  const minTracksSelect = container.querySelector("#filter-min-tracks");
  artistInput.value = filters.artist;
  albumInput.value = filters.album;
  minTracksSelect.value = filters.minTracks;

  artistInput.addEventListener("input", () => {
    filters.artist = artistInput.value.toLowerCase();
    openIndex = null;
    renderList(container);
  });
  albumInput.addEventListener("input", () => {
    filters.album = albumInput.value.toLowerCase();
    openIndex = null;
    renderList(container);
  });
  minTracksSelect.addEventListener("change", () => {
    filters.minTracks = minTracksSelect.value;
    openIndex = null;
    renderList(container);
  });

  renderList(container);
}

function renderList(container) {
  const filtered = rows
    .map((r, i) => ({ r, i }))
    .filter(({ r }) => filters.minTracks === "" || r.track_count >= parseInt(filters.minTracks, 10))
    .filter(({ r }) => !filters.artist || r.artist.toLowerCase().includes(filters.artist))
    .filter(({ r }) => !filters.album || r.album.toLowerCase().includes(filters.album));

  const list = container.querySelector("#row-list");
  list.innerHTML = filtered.length
    ? filtered.map(({ r, i }) => rowHtml(r, i)).join("")
    : `<p style="color:#888;padding:16px">No albums match the current filters.</p>`;

  container.querySelector("#filter-status").textContent =
    `Showing ${filtered.length} of ${rows.length}`;

  list.querySelectorAll(".album-row").forEach((row) => {
    row.addEventListener("click", () => {
      const idx = parseInt(row.dataset.idx, 10);
      openIndex = openIndex === idx ? null : idx;
      renderList(container);
    });
  });

  list.querySelectorAll("[data-action='show-create-group']").forEach((btn) => {
    btn.addEventListener("click", () => {
      const form = list.querySelector(`.create-group-form[data-idx="${btn.dataset.idx}"]`);
      if (form) form.style.display = "block";
    });
  });

  list.querySelectorAll("[data-action='cancel-create-group']").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.closest(".create-group-form").style.display = "none";
    });
  });

  list.querySelectorAll("[data-action='confirm-create-group']").forEach((btn) => {
    btn.addEventListener("click", () => handleCreateGroup(btn));
  });
}

function rowHtml(r, i) {
  const years = r.year_min == null
    ? "—"
    : r.year_min === r.year_max
      ? r.year_min
      : `${r.year_min}–${r.year_max}`;
  const isOpen = openIndex === i;

  return `
    <div class="album-row" data-idx="${i}">
      <strong>${escHtml(r.artist)} — ${escHtml(r.album)}</strong>
      <div class="flex-row" style="gap:10px">
        <span style="color:#888">${r.track_count} track${r.track_count === 1 ? "" : "s"} • ${years}</span>
        <button class="btn btn-secondary btn-sm" data-action="view" data-idx="${i}">${isOpen ? "Hide" : "View"}</button>
      </div>
    </div>
    ${isOpen ? trackPanelHtml(r, i) : ""}`;
}

function trackPanelHtml(r, i) {
  return `
    <div class="album-row-panel">
      <div style="overflow-x:auto">
        <table>
          <thead>
            <tr><th>Track</th><th>Artist</th><th>Title</th><th>Duration</th><th>Released</th><th>Tags</th></tr>
          </thead>
          <tbody>
            ${r.tracks
              .map(
                (t) => `
              <tr>
                <td>${t.track ?? ""}</td>
                <td title="${escHtml(t.artist)}">${escHtml(t.artist)}</td>
                <td title="${escHtml(t.title)}">${escHtml(t.title)}</td>
                <td>${fmtDuration(t.duration)}</td>
                <td>${fmtDate(t.released)}</td>
                <td title="${escHtml(t.tags)}">${escHtml(t.tags)}</td>
              </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>
      <div class="mt-8">
        <button class="btn btn-primary btn-sm" data-action="show-create-group" data-idx="${i}">Create Group</button>
        <div class="create-group-form inline-panel mt-8" data-idx="${i}" style="display:none">
          <div class="form-group">
            <label>Group Name</label>
            <input class="f-group-name" type="text" value="${escHtml(r.album)}">
          </div>
          <div class="flex-row mt-8">
            <button class="btn btn-primary btn-sm" data-action="confirm-create-group" data-idx="${i}">Save</button>
            <button class="btn btn-secondary btn-sm" data-action="cancel-create-group" data-idx="${i}">Cancel</button>
          </div>
        </div>
      </div>
    </div>`;
}

async function handleCreateGroup(btn) {
  const idx = parseInt(btn.dataset.idx, 10);
  const row = rows[idx];
  const form = btn.closest(".create-group-form");
  const group_name = form.querySelector(".f-group-name").value.trim();
  if (!group_name) {
    showToast("Group name required", "error");
    return;
  }

  const songs = row.tracks.filter((t) => t.link).map((t) => t.link);
  if (!songs.length) {
    showToast("No linked tracks to group", "error");
    return;
  }

  btn.disabled = true;
  try {
    await api("POST", "/api/grouped-songs/", { artist: row.artist, group_name, songs });
    showToast("Group created");
    form.style.display = "none";
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
  }
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
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
