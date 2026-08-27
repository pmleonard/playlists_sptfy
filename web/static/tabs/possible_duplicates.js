import { api, showToast } from "/static/app.js";

const BASE = "/api/possible-duplicates";

export async function render(container) {
  container.innerHTML = `<p class="loading">Loading…</p>`;
  let data;
  try {
    data = await api("GET", `${BASE}/`);
  } catch (err) {
    container.innerHTML = `<p class="error-msg">Error: ${err.message}</p>`;
    return;
  }
  draw(container, data);
}

function draw(container, data) {
  const keys = Object.keys(data);
  container.innerHTML = `
    <div class="card">
      <div class="card-header">
        <strong>Possible Duplicates (${keys.length} entries)</strong>
      </div>
      <ul class="file-list" id="entry-list"></ul>
    </div>`;

  renderList(container, data);
}

function renderList(container, data) {
  const list = container.querySelector("#entry-list");
  const keys = Object.keys(data);
  list.innerHTML = keys.length
    ? keys.map((k) => `
      <li data-key="${escHtml(k)}">
        <span class="file-name">${escHtml(k)} <small style="color:#888">(${data[k].length} songs)</small></span>
        <button class="btn btn-secondary btn-sm" data-action="view" data-key="${escHtml(k)}">View</button>
        <button class="btn btn-secondary btn-sm" data-action="move" data-key="${escHtml(k)}">Move to Ignored</button>
      </li>`).join("")
    : `<li style="color:#888">No entries.</li>`;

  list.querySelectorAll("[data-action='view']").forEach((btn) => {
    btn.onclick = () => handleView(btn.dataset.key, data, container, btn);
  });

  list.querySelectorAll("[data-action='move']").forEach((btn) => {
    btn.onclick = () => moveToIgnored(btn.dataset.key, container, btn);
  });
}

function closeInlinePanel(list) {
  list.querySelectorAll(".inline-item-panel").forEach((el) => el.remove());
}

function handleView(key, data, container, triggerBtn) {
  const list = container.querySelector("#entry-list");

  const existingPanel = triggerBtn.closest("li").nextElementSibling;
  const isSamePanel = existingPanel?.classList.contains("inline-item-panel") &&
                      existingPanel.dataset.for === key;
  closeInlinePanel(list);
  if (isSamePanel) return;

  const panel = document.createElement("li");
  panel.className = "inline-item-panel";
  panel.dataset.for = key;
  panel.innerHTML = `
    <div class="inline-panel" style="width:100%">
      <div class="card-header" style="margin-bottom:8px"><strong>View: ${escHtml(key)}</strong></div>
      <div class="songs-table-wrap"></div>
      <div class="flex-row mt-8">
        <button class="btn btn-secondary btn-sm close-panel-btn">Close</button>
      </div>
    </div>`;

  panel.querySelector(".close-panel-btn").onclick = () => panel.remove();
  triggerBtn.closest("li").after(panel);
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });

  renderSongsTable(panel.querySelector(".songs-table-wrap"), key, data[key], data, container);
}

function renderSongsTable(wrap, key, songs, data, container) {
  if (!songs.length) {
    wrap.innerHTML = `<p style="color:#888">No songs.</p>`;
    return;
  }
  wrap.innerHTML = `
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr>
          <th style="text-align:left;padding:4px 6px">Artist</th>
          <th style="text-align:left;padding:4px 6px">Title</th>
          <th style="text-align:left;padding:4px 6px">Album</th>
          <th style="text-align:left;padding:4px 6px">Released</th>
          <th style="text-align:left;padding:4px 6px">Duration</th>
          <th style="text-align:left;padding:4px 6px">Tags</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        ${songs.map((s, si) => `
          <tr>
            <td style="padding:4px 6px">${escHtml(s.artist || "")}</td>
            <td style="padding:4px 6px">${escHtml(s.title || "")}</td>
            <td style="padding:4px 6px">${escHtml(s.album || "")}</td>
            <td style="padding:4px 6px">${String(s.released || "").slice(0, 10)}</td>
            <td style="padding:4px 6px">${fmtDuration(s.duration)}</td>
            <td style="padding:4px 6px">${escHtml(s.tags || "")}</td>
            <td style="padding:4px 6px">
              <button class="btn btn-danger btn-sm" data-song-idx="${si}">Delete</button>
            </td>
          </tr>`).join("")}
      </tbody>
    </table>`;

  wrap.querySelectorAll("[data-song-idx]").forEach((btn) => {
    btn.onclick = () => deleteSongFromEntry(key, parseInt(btn.dataset.songIdx, 10), data, container, wrap, btn);
  });
}

async function deleteSongFromEntry(key, songIdx, data, container, wrap, btn) {
  btn.disabled = true;
  try {
    const result = await api("DELETE", `${BASE}/${encodeURIComponent(key)}/songs/${songIdx}`);
    showToast("Song removed");
    if (result.entry_deleted) {
      render(container);
    } else {
      // Refresh the panel's song table
      const updated = await api("GET", `${BASE}/`);
      const updatedSongs = updated[key] || [];
      renderSongsTable(wrap, key, updatedSongs, updated, container);
    }
  } catch (err) {
    showToast(err.message, "error");
    btn.disabled = false;
  }
}

async function moveToIgnored(key, container, btn) {
  btn.disabled = true;
  try {
    await api("POST", `${BASE}/${encodeURIComponent(key)}/move-to-ignored`);
    showToast(`Moved "${key}" to Ignored Duplicates`);
    render(container);
  } catch (err) {
    showToast(err.message, "error");
    btn.disabled = false;
  }
}

function fmtDuration(secs) {
  const n = parseInt(secs, 10);
  if (isNaN(n)) return secs ?? "";
  return `${Math.floor(n / 60)}:${String(n % 60).padStart(2, "0")}`;
}

function escHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
