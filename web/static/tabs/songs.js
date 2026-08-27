import { api, showToast, showConfirm } from "/static/app.js";

let allSongs = [];
let activeTags = new Set();
let columnFilters = {};
let sortCol = null;
let sortDir = 1;

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
  sortCol = null;
  sortDir = 1;
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
            <th data-sort="artist">Artist</th>
            <th data-sort="album">Album</th>
            <th data-sort="track">Track</th>
            <th data-sort="title">Title</th>
            <th data-sort="duration">Duration</th>
            <th data-sort="released">Released</th>
            <th>Tags</th>
            <th></th>
          </tr>
          <tr class="filter-row">
            <td><input data-col="artist" placeholder="filter…"></td>
            <td><input data-col="album" placeholder="filter…"></td>
            <td><input data-col="track" placeholder="filter…"></td>
            <td><input data-col="title" placeholder="filter…"></td>
            <td><input data-col="duration" placeholder="filter…"></td>
            <td><input data-col="released" placeholder="filter…"></td>
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

  container.querySelector("thead tr:first-child").addEventListener("click", (e) => {
    const th = e.target.closest("th[data-sort]");
    if (!th) return;
    const col = th.dataset.sort;
    if (sortCol === col) {
      sortDir = -sortDir;
    } else {
      sortCol = col;
      sortDir = 1;
    }
    container.querySelectorAll("th[data-sort]").forEach((h) => {
      h.classList.remove("sort-asc", "sort-desc");
      if (h.dataset.sort === sortCol) {
        h.classList.add(sortDir === 1 ? "sort-asc" : "sort-desc");
      }
    });
    renderTable(container);
  });

  // Delegated handler on the table — survives tbody re-renders
  container.querySelector("#songs-table").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-action]");
    if (!btn) return;
    const idx = parseInt(btn.dataset.idx, 10);
    if (btn.dataset.action === "edit") openEditPanel(container, idx);
    if (btn.dataset.action === "delete") deleteSong(container, idx);
  });
}

function renderTable(container) {
  container.querySelectorAll(".inline-edit-row").forEach((r) => r.remove());

  let indexed = allSongs.map((s, i) => ({ s, i }));

  indexed = indexed.filter(({ s }) => {
    if (activeTags.size > 0) {
      const songTags = (s.tags || "").split(",").map((t) => t.trim());
      if (!songTags.some((t) => activeTags.has(t))) return false;
    }
    for (const [col, val] of Object.entries(columnFilters)) {
      if (!val) continue;
      if (!String(s[col] ?? "").toLowerCase().includes(val)) return false;
    }
    return true;
  });

  if (sortCol) {
    indexed.sort((a, b) => {
      const av = a.s[sortCol] ?? "";
      const bv = b.s[sortCol] ?? "";
      if (sortCol === "track" || sortCol === "duration") {
        return (parseFloat(av) - parseFloat(bv)) * sortDir;
      }
      return String(av).localeCompare(String(bv)) * sortDir;
    });
  }

  const tbody = container.querySelector("#songs-body");
  tbody.innerHTML = indexed.map(({ s, i }) => `
    <tr data-idx="${i}">
      <td title="${escHtml(s.artist || "")}">${escHtml(s.artist || "")}</td>
      <td title="${escHtml(s.album || "")}">${escHtml(s.album || "")}</td>
      <td>${s.track ?? ""}</td>
      <td title="${escHtml(s.title || "")}">${escHtml(s.title || "")}</td>
      <td>${fmtDuration(s.duration)}</td>
      <td>${fmtDate(s.released)}</td>
      <td title="${escHtml(s.tags || "")}">${escHtml(s.tags || "")}</td>
      <td class="row-actions">
        <button class="btn btn-secondary btn-sm" data-action="edit" data-idx="${i}">Edit</button>
        <button class="btn btn-danger btn-sm" data-action="delete" data-idx="${i}">Delete</button>
      </td>
    </tr>`).join("");

  container.querySelector("#status").textContent =
    `Showing ${indexed.length} of ${allSongs.length} songs`;
}

async function openEditPanel(container, idx) {
  container.querySelectorAll(".inline-edit-row").forEach((r) => r.remove());

  const song = allSongs[idx];
  const row = container.querySelector(`tr[data-idx="${idx}"]`);
  if (!row) return;

  let groups = [];
  try {
    groups = await api("GET", "/api/grouped-songs/");
  } catch (err) {
    showToast("Failed to load grouped songs: " + err.message, "error");
  }

  const artistGroups = groups
    .map((g, i) => ({ ...g, origIdx: i }))
    .filter((g) => g.artist.toLowerCase() === (song.artist || "").toLowerCase());

  const gsOptions = artistGroups.length
    ? `<div class="flex-row mt-8">
        <select class="gs-select" style="flex:1">
          ${artistGroups.map((g) => `<option value="${g.origIdx}">${escHtml(g.group_name)}</option>`).join("")}
        </select>
        <button class="btn btn-secondary btn-sm gs-add-btn">Add</button>
       </div>`
    : `<div class="mt-8">
        <p style="color:#888;margin-bottom:6px">No groups for this artist. Create one:</p>
        <div class="flex-row">
          <input class="gs-new-name" type="text" placeholder="Group name" style="flex:1">
          <button class="btn btn-secondary btn-sm gs-create-btn">Create Group</button>
        </div>
       </div>`;

  const panel = document.createElement("tr");
  panel.className = "inline-edit-row";
  panel.innerHTML = `
    <td colspan="8">
      <div class="inline-panel">
        <div class="card-header" style="margin-bottom:8px"><strong>Edit Song</strong></div>
        <div class="song-subform-grid">
          <div class="form-group"><label>Artist</label><input class="f-artist" type="text" value="${escHtml(song.artist || "")}"></div>
          <div class="form-group"><label>Album</label><input class="f-album" type="text" value="${escHtml(song.album || "")}"></div>
          <div class="form-group"><label>Track</label><input class="f-track" type="text" value="${escHtml(String(song.track ?? ""))}"></div>
          <div class="form-group"><label>Title</label><input class="f-title" type="text" value="${escHtml(song.title || "")}"></div>
          <div class="form-group"><label>Duration (s)</label><input class="f-duration" type="text" value="${escHtml(String(song.duration ?? ""))}"></div>
          <div class="form-group"><label>Released</label><input class="f-released" type="text" value="${escHtml(song.released || "")}"></div>
          <div class="form-group"><label>Tags</label><input class="f-tags" type="text" value="${escHtml(song.tags || "")}"></div>
          <div class="form-group"><label>Link</label><input class="f-link" type="text" value="${escHtml(song.link || "")}"></div>
        </div>
        <fieldset style="margin-top:12px;padding:8px;border:1px solid #ddd;border-radius:4px">
          <legend style="padding:0 4px">Add to Grouped Songs</legend>
          ${gsOptions}
        </fieldset>
        <div class="flex-row mt-8">
          <button class="btn btn-primary btn-sm save-btn">Save</button>
          <button class="btn btn-secondary btn-sm cancel-btn">Cancel</button>
        </div>
      </div>
    </td>`;

  row.after(panel);
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });

  panel.querySelector(".cancel-btn").onclick = () => panel.remove();

  panel.querySelector(".save-btn").onclick = async () => {
    const updated = readPanelFields(panel);
    try {
      await api("PUT", `/api/songs/${idx}`, updated);
      showToast("Song saved");
      render(container);
    } catch (err) { showToast(err.message, "error"); }
  };

  const gsAddBtn = panel.querySelector(".gs-add-btn");
  if (gsAddBtn) {
    gsAddBtn.onclick = async () => {
      const gsIdx = parseInt(panel.querySelector(".gs-select").value, 10);
      const group = groups[gsIdx];
      const link = panel.querySelector(".f-link").value.trim() || song.link || "";
      if (!link) { showToast("Song has no link", "error"); return; }
      try {
        await api("PUT", `/api/grouped-songs/${gsIdx}`, { ...group, songs: [...group.songs, link] });
        showToast(`Added to "${group.group_name}"`);
      } catch (err) { showToast(err.message, "error"); }
    };
  }

  const gsCreateBtn = panel.querySelector(".gs-create-btn");
  if (gsCreateBtn) {
    gsCreateBtn.onclick = async () => {
      const name = panel.querySelector(".gs-new-name").value.trim();
      if (!name) { showToast("Group name required", "error"); return; }
      const artist = panel.querySelector(".f-artist").value.trim() || song.artist || "";
      const link = panel.querySelector(".f-link").value.trim() || song.link || "";
      gsCreateBtn.disabled = true;
      try {
        await api("POST", "/api/grouped-songs/", { artist, group_name: name, songs: link ? [link] : [] });
        showToast(`Group "${name}" created`);
        gsCreateBtn.closest("div.mt-8").innerHTML =
          `<p style="color:#2e7d32;margin-top:8px">Group "${escHtml(name)}" created.</p>`;
      } catch (err) {
        showToast(err.message, "error");
        gsCreateBtn.disabled = false;
      }
    };
  }

}

function readPanelFields(panel) {
  return {
    artist:   panel.querySelector(".f-artist").value.trim(),
    album:    panel.querySelector(".f-album").value.trim(),
    track:    panel.querySelector(".f-track").value.trim(),
    title:    panel.querySelector(".f-title").value.trim(),
    duration: panel.querySelector(".f-duration").value.trim(),
    released: panel.querySelector(".f-released").value.trim(),
    tags:     panel.querySelector(".f-tags").value.trim(),
    link:     panel.querySelector(".f-link").value.trim(),
  };
}

async function deleteSong(container, idx) {
  const song = allSongs[idx];
  const ok = await showConfirm(`Delete song "${song.title || song.artist}"?`);
  if (!ok) return;
  try {
    await api("DELETE", `/api/songs/${idx}`);
    showToast("Song deleted");
    render(container);
  } catch (err) { showToast(err.message, "error"); }
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
