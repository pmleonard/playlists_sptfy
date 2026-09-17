import { api, showToast } from "/static/app.js";
import { getPageSize, paginate, paginationBarHtml, bindPaginationBar } from "/static/pagination.js";

let allSongs = [];
let genreTags = new Set();
let eraTags = new Set();
let activeTags = new Set();
let activeRankings = new Set(["unrated"]);
let columnFilters = {};
let sortCol = null;
let sortDir = 1;
let pageState = { page: 1, pageSize: getPageSize("ranking") };

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
  activeTags = new Set();
  activeRankings = new Set(["unrated"]);
  columnFilters = {};
  sortCol = null;
  sortDir = 1;
  pageState = { page: 1, pageSize: getPageSize("ranking") };
  drawShell(container);
  renderTable(container);
}

function drawShell(container) {
  const { genre, era, other } = groupTags(allSongs, genreTags, eraTags);
  const row1 = [
    ...genre.map(tagBtnHtml),
    ...(genre.length && era.length ? [`<span class="tag-sep"></span>`] : []),
    ...era.map(tagBtnHtml),
  ];
  const row2 = other.map(tagBtnHtml);

  const rankingOptions = ["5", "4", "3", "2", "1", "unrated"];
  const rankingRow = rankingOptions.map(rankingBtnHtml).join("");

  container.innerHTML = `
    <div id="tag-filters">
      ${row1.length ? `<div class="tag-filters">${row1.join("")}</div>` : ""}
      ${row2.length ? `<div class="tag-filters">${row2.join("")}</div>` : ""}
    </div>
    <div id="ranking-filters">
      <div class="tag-filters">${rankingRow}</div>
    </div>
    <div class="flex-row mb-12">
      <div class="status-bar" id="status" style="margin-bottom:0"></div>
      <button type="button" class="btn btn-secondary btn-sm" id="refresh-btn">Refresh</button>
    </div>
    <div id="pagination-bar"></div>
    <div style="overflow-x:auto">
      <table id="ranking-table">
        <thead>
          <tr>
            ${["artist", "album", "track", "title"].map((col) => sortHeaderHtml(col)).join("")}
            <th>Ranking</th>
          </tr>
          <tr class="filter-row">
            <td><input data-col="artist" placeholder="filter…" value="${escHtml(columnFilters.artist || "")}"></td>
            <td><input data-col="album" placeholder="filter…" value="${escHtml(columnFilters.album || "")}"></td>
            <td><input data-col="track" placeholder="filter…" value="${escHtml(columnFilters.track || "")}"></td>
            <td><input data-col="title" placeholder="filter…" value="${escHtml(columnFilters.title || "")}"></td>
            <td></td>
          </tr>
        </thead>
        <tbody id="ranking-body"></tbody>
      </table>
    </div>`;

  container.querySelector("#tag-filters").addEventListener("click", (e) => {
    const btn = e.target.closest(".tag-btn");
    if (!btn) return;
    const tag = btn.dataset.tag;
    if (activeTags.has(tag)) activeTags.delete(tag);
    else activeTags.add(tag);
    btn.classList.toggle("active", activeTags.has(tag));
    pageState.page = 1;
    renderTable(container);
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

  container.querySelectorAll(".filter-row input").forEach((inp) => {
    inp.addEventListener("input", () => {
      // Stored as typed (not lowercased) so a mid-session drawShell()
      // rebuild (Refresh) can restore the input's displayed value exactly
      // as the user typed it — matching is still case-insensitive, see
      // renderTable's filter predicate below.
      columnFilters[inp.dataset.col] = inp.value;
      pageState.page = 1;
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
    pageState.page = 1;
    renderTable(container);
  });

  // Delegated handler on the table — survives tbody re-renders. Ranking
  // edits deliberately do NOT go through renderTable (see setRanking) so
  // this listener stays bound across ranking clicks too.
  container.querySelector("#ranking-table").addEventListener("click", (e) => {
    const btn = e.target.closest(".rank-btn");
    if (!btn) return;
    const group = btn.closest(".rank-btns");
    const idx = parseInt(group.dataset.idx, 10);
    const newValue = btn.classList.contains("active") ? "" : btn.dataset.value;
    setRanking(container, idx, newValue);
  });

  container.querySelector("#refresh-btn").addEventListener("click", () => {
    refreshFromServer(container);
  });
}

async function refreshFromServer(container) {
  const btn = container.querySelector("#refresh-btn");
  btn.disabled = true;
  try {
    const [songs, tagGroups] = await Promise.all([
      api("GET", "/api/songs/"),
      api("GET", "/api/tag-groups/"),
    ]);
    allSongs = songs;
    genreTags = new Set(tagGroups.genre_tags);
    eraTags = new Set(tagGroups.era_tags);
    // Rebuilds the shell (tag/ranking chips, table) and re-renders, but
    // deliberately keeps activeTags/activeRankings/columnFilters/sortCol/
    // pageState as they are — refresh re-syncs with the server without
    // discarding the user's current filter/sort/page choices, the same
    // "explicit trigger" contract every other filter/sort/page action
    // already follows (see setRanking's comment / design.md section 1).
    drawShell(container);
    renderTable(container);
  } catch (err) {
    showToast(err.message, "error");
    btn.disabled = false;
  }
}

function sortHeaderHtml(col) {
  const label = col.charAt(0).toUpperCase() + col.slice(1);
  const cls = sortCol === col ? (sortDir === 1 ? "sort-asc" : "sort-desc") : "";
  return `<th data-sort="${col}" class="${cls}">${label}</th>`;
}

function rankButtonsHtml(ranking, i) {
  const btns = [1, 2, 3, 4, 5]
    .map((n) => `<button type="button" class="rank-btn ${String(n) === ranking ? "active" : ""}" data-value="${n}">${n}</button>`)
    .join("");
  return `<div class="rank-btns" data-idx="${i}">${btns}</div>`;
}

async function setRanking(container, idx, ranking) {
  const group = container.querySelector(`.rank-btns[data-idx="${idx}"]`);
  const prevRanking = allSongs[idx].ranking;
  group.querySelectorAll(".rank-btn").forEach((b) => (b.disabled = true));

  const updated = { ...allSongs[idx], ranking };
  try {
    await api("PUT", `/api/songs/${idx}`, updated);
    allSongs[idx] = updated;
    showToast("Ranking updated");
    // Deliberately not calling renderTable(container) here — see design.md
    // section 1/4 and R1 in tasks.md. A ranking edit must not re-filter/
    // re-sort/re-paginate the currently-visible list; it only patches this
    // row's own buttons. allSongs[idx] is still updated above, so the
    // *next* explicit filter/sort/page action (which does call
    // renderTable) will correctly account for this change.
    paintRankButtons(group, ranking);
  } catch (err) {
    showToast(err.message, "error");
    paintRankButtons(group, prevRanking);
  } finally {
    group.querySelectorAll(".rank-btn").forEach((b) => (b.disabled = false));
  }
}

function paintRankButtons(group, ranking) {
  group.querySelectorAll(".rank-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.value === ranking);
  });
}

function renderTable(container) {
  let indexed = allSongs.map((s, i) => ({ s, i }));

  indexed = indexed.filter(({ s }) => {
    if (activeTags.size > 0) {
      const songTags = (s.tags || "").split(",").map((t) => t.trim());
      if (!songTags.some((t) => activeTags.has(t))) return false;
    }
    if (activeRankings.size > 0) {
      const key = s.ranking || "unrated";
      if (!activeRankings.has(key)) return false;
    }
    for (const [col, val] of Object.entries(columnFilters)) {
      if (!val) continue;
      if (!String(s[col] ?? "").toLowerCase().includes(val.toLowerCase())) return false;
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
  } else {
    indexed.sort((a, b) => defaultCompare(a.s, b.s));
  }

  const { slice, page } = paginate(indexed, pageState.page, pageState.pageSize);
  pageState.page = page;

  const tbody = container.querySelector("#ranking-body");
  tbody.innerHTML = slice.map(({ s, i }) => `
    <tr data-idx="${i}">
      <td title="${escHtml(s.artist || "")}">${escHtml(s.artist || "")}</td>
      <td title="${escHtml(s.album || "")}">${escHtml(s.album || "")}</td>
      <td>${s.track ?? ""}</td>
      <td title="${escHtml(s.title || "")}">${escHtml(s.title || "")}</td>
      <td>${rankButtonsHtml(s.ranking, i)}</td>
    </tr>`).join("");

  const pagBar = container.querySelector("#pagination-bar");
  pagBar.innerHTML = paginationBarHtml(pageState, indexed.length);
  bindPaginationBar(pagBar, "ranking", pageState, () => renderTable(container));

  container.querySelector("#status").textContent =
    `Showing ${slice.length} of ${indexed.length} songs (${allSongs.length} total)`;
}

function defaultCompare(a, b) {
  const artistCmp = String(a.artist ?? "").localeCompare(String(b.artist ?? ""));
  if (artistCmp) return artistCmp;
  const albumCmp = String(a.album ?? "").localeCompare(String(b.album ?? ""));
  if (albumCmp) return albumCmp;
  return (parseFloat(a.track) || 0) - (parseFloat(b.track) || 0);
}

function groupTags(songs, genreSet, eraSet) {
  const counts = new Map();
  for (const s of songs) {
    (s.tags || "").split(",").map((t) => t.trim()).filter(Boolean)
      .forEach((t) => counts.set(t, (counts.get(t) || 0) + 1));
  }
  const present = [...counts.keys()];
  const byCountDesc = (a, b) => counts.get(b) - counts.get(a) || a.localeCompare(b);

  const genre = present.filter((t) => genreSet.has(t)).sort(byCountDesc);
  const era = present.filter((t) => eraSet.has(t)).sort((a, b) => a.localeCompare(b));
  const other = present.filter((t) => !genreSet.has(t) && !eraSet.has(t)).sort(byCountDesc);
  return { genre, era, other };
}

function tagBtnHtml(t) {
  return `<button class="tag-btn ${activeTags.has(t) ? "active" : ""}" data-tag="${t}">${escHtml(t)}</button>`;
}

function rankingBtnHtml(r) {
  const label = r === "unrated" ? "Unrated" : `${r}★`;
  return `<button class="tag-btn ${activeRankings.has(r) ? "active" : ""}" data-ranking="${r}">${label}</button>`;
}

function escHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
