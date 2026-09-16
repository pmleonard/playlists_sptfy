import { api, showToast } from "/static/app.js";
import { getPageSize, paginate, paginationBarHtml, bindPaginationBar } from "/static/pagination.js";

let allSongs = [];
let genreTags = new Set();
let eraTags = new Set();
let selectedTag = null;
let scored = [];
let columnFilters = {};
let activeRankings = new Set();
let pageState = { page: 1, pageSize: getPageSize("suggestions") };

export async function render(container) {
  container.innerHTML = `<p class="loading">Loading songs…</p>`;
  try {
    const [songs, tagGroups] = await Promise.all([
      api("GET", "/api/songs/"),
      api("GET", "/api/tag-groups/"),
    ]);
    allSongs = songs;
    genreTags = new Set(tagGroups.genre_tags);
    eraTags = new Set(tagGroups.era_tags);
  } catch (err) {
    container.innerHTML = `<p class="error-msg">Error: ${err.message}</p>`;
    return;
  }
  selectedTag = null;
  scored = [];
  columnFilters = {};
  activeRankings = new Set();
  pageState = { page: 1, pageSize: getPageSize("suggestions") };
  drawShell(container);
  renderTable(container);
}

function drawShell(container) {
  const tagOptions = otherTagsByCount(allSongs, genreTags, eraTags);
  const rankingOptions = ["5", "4", "3", "2", "1", "unrated"];

  container.innerHTML = `
    <div class="flex-row" style="gap:8px;align-items:center;margin-bottom:12px">
      <label for="suggestion-tag-select"><strong>Suggest songs for tag:</strong></label>
      <select id="suggestion-tag-select">
        <option value="" disabled ${selectedTag ? "" : "selected"}>— Select a tag —</option>
        ${tagOptions.map((t) => `<option value="${escHtml(t)}" ${t === selectedTag ? "selected" : ""}>${escHtml(t)}</option>`).join("")}
      </select>
    </div>
    <div id="ranking-filters">
      <div class="tag-filters">${rankingOptions.map(rankingBtnHtml).join("")}</div>
    </div>
    <div class="status-bar" id="status"></div>
    <div id="pagination-bar"></div>
    <div style="overflow-x:auto">
      <table id="suggestions-table">
        <thead>
          <tr>
            <th>Artist</th>
            <th>Album</th>
            <th>Track</th>
            <th>Title</th>
            <th>Duration</th>
            <th>Released</th>
            <th>Tags</th>
            <th>Ranking</th>
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
            <td></td>
          </tr>
        </thead>
        <tbody id="suggestions-body"></tbody>
      </table>
    </div>`;

  container.querySelector("#suggestion-tag-select").addEventListener("change", (e) => {
    selectedTag = e.target.value || null;
    columnFilters = {};
    pageState.page = 1;
    scored = selectedTag ? computeSuggestions(allSongs, selectedTag) : [];
    renderTable(container);
  });

  container.querySelectorAll(".filter-row input").forEach((inp) => {
    inp.addEventListener("input", () => {
      columnFilters[inp.dataset.col] = inp.value.toLowerCase();
      pageState.page = 1;
      renderTable(container);
    });
  });

  container.querySelector("#ranking-filters").addEventListener("click", (e) => {
    const btn = e.target.closest(".tag-btn");
    if (!btn) return;
    const ranking = btn.dataset.ranking;
    if (activeRankings.has(ranking)) activeRankings.delete(ranking);
    else activeRankings.add(ranking);
    btn.classList.toggle("active", activeRankings.has(ranking));
    pageState.page = 1;
    renderTable(container);
  });

  // Delegated handler on the table — survives tbody re-renders
  container.querySelector("#suggestions-table").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-action='add-tag']");
    if (!btn) return;
    addTag(container, btn.dataset.link);
  });
}

function renderTable(container) {
  const status = container.querySelector("#status");
  const tbody = container.querySelector("#suggestions-body");
  const pagBar = container.querySelector("#pagination-bar");

  if (!selectedTag) {
    tbody.innerHTML = "";
    pagBar.innerHTML = "";
    status.textContent = "Select a tag above to see suggestions.";
    return;
  }

  const filtered = scored.filter(({ song: s }) => {
    if (activeRankings.size > 0) {
      const key = s.ranking || "unrated";
      if (!activeRankings.has(key)) return false;
    }
    for (const [col, val] of Object.entries(columnFilters)) {
      if (!val) continue;
      if (!String(s[col] ?? "").toLowerCase().includes(val)) return false;
    }
    return true;
  });

  const { slice, page } = paginate(filtered, pageState.page, pageState.pageSize);
  pageState.page = page;

  tbody.innerHTML = slice.map(({ song: s }) => `
    <tr>
      <td title="${escHtml(s.artist || "")}">${escHtml(s.artist || "")}</td>
      <td title="${escHtml(s.album || "")}">${escHtml(s.album || "")}</td>
      <td>${s.track ?? ""}</td>
      <td title="${escHtml(s.title || "")}">${escHtml(s.title || "")}</td>
      <td>${fmtDuration(s.duration)}</td>
      <td>${fmtDate(s.released)}</td>
      <td title="${escHtml(s.tags || "")}">${escHtml(s.tags || "")}</td>
      <td>${s.ranking ? escHtml(s.ranking) : "—"}</td>
      <td class="row-actions">
        ${s.link ? `<a class="btn btn-secondary btn-sm" href="${escHtml(s.link)}" target="_blank" rel="noopener">Open ↗</a>` : ""}
        <button class="btn btn-primary btn-sm" data-action="add-tag" data-link="${escHtml(s.link || "")}">Add Tag</button>
      </td>
    </tr>`).join("");

  pagBar.innerHTML = paginationBarHtml(pageState, filtered.length);
  bindPaginationBar(pagBar, "suggestions", pageState, () => renderTable(container));

  status.textContent =
    `Showing ${slice.length} of ${filtered.length} suggestions for "${selectedTag}"`;
}

async function addTag(container, link) {
  const idx = allSongs.findIndex((s) => s.link === link);
  if (idx === -1) return;
  const btn = container.querySelector(`[data-action='add-tag'][data-link="${cssEscape(link)}"]`);
  if (btn) btn.disabled = true;
  try {
    await api("PATCH", `/api/songs/${idx}/tags`, { tag: selectedTag });
    const current = (allSongs[idx].tags || "").split(",").map((t) => t.trim()).filter(Boolean);
    current.push(selectedTag);
    allSongs[idx].tags = current.join(", ");
    scored = scored.filter((r) => r.song.link !== link);
    showToast("Tag added");
    renderTable(container);
  } catch (err) {
    showToast(err.message, "error");
    if (btn) btn.disabled = false;
  }
}

function computeSuggestions(songs, tag) {
  const hasTag = (s) => tagsSet(s.tags).has(tag);
  const tagged = songs.filter(hasTag);
  const candidates = songs.filter((s) => !hasTag(s));

  const totalTagCount = tagged.length;

  const artistCounts = new Map();
  const artistAlbumCounts = new Map();
  for (const s of tagged) {
    const a = lc(s.artist);
    const key = artistAlbumKey(s);
    artistCounts.set(a, (artistCounts.get(a) || 0) + 1);
    artistAlbumCounts.set(key, (artistAlbumCounts.get(key) || 0) + 1);
  }

  const withScores = candidates.map((s) => {
    const a = lc(s.artist);
    const key = artistAlbumKey(s);
    const byArtist = artistCounts.get(a) || 0;
    const byArtistAlbum = artistAlbumCounts.get(key) || 0;
    const byTotal = totalTagCount;
    const byRanking = parseInt(s.ranking, 10) || 0;
    return {
      song: s,
      score: byArtist + byArtistAlbum + byTotal + byRanking,
      byArtist,
      byArtistAlbum,
      byTotal,
      byRanking,
    };
  });

  withScores.sort((x, y) =>
    y.score - x.score ||
    lc(x.song.artist).localeCompare(lc(y.song.artist)) ||
    lc(x.song.title).localeCompare(lc(y.song.title))
  );

  const cutoff = Math.floor(withScores.length * 0.8);
  return withScores.slice(0, cutoff);
}

function artistAlbumKey(s) {
  return JSON.stringify([lc(s.artist), lc(s.album)]);
}

function lc(v) {
  return String(v ?? "").toLowerCase();
}

function tagsSet(tags) {
  return new Set((tags || "").split(",").map((t) => t.trim()).filter(Boolean));
}

function otherTagsByCount(songs, genreSet, eraSet) {
  const counts = new Map();
  for (const s of songs) {
    (s.tags || "").split(",").map((t) => t.trim()).filter(Boolean)
      .forEach((t) => counts.set(t, (counts.get(t) || 0) + 1));
  }
  return [...counts.keys()]
    .filter((t) => !genreSet.has(t) && !eraSet.has(t))
    .sort((a, b) => counts.get(b) - counts.get(a) || a.localeCompare(b));
}

function rankingBtnHtml(r) {
  const label = r === "unrated" ? "Unrated" : `${r}★`;
  return `<button class="tag-btn ${activeRankings.has(r) ? "active" : ""}" data-ranking="${r}">${label}</button>`;
}

function cssEscape(s) {
  return window.CSS && CSS.escape ? CSS.escape(s) : String(s).replace(/["\\]/g, "\\$&");
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
