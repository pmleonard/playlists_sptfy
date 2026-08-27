import { api, showToast, showConfirm } from "/static/app.js";

export async function render(container) {
  container.innerHTML = `<p class="loading">Loading…</p>`;
  let groups;
  try {
    groups = await api("GET", "/api/grouped-songs/");
  } catch (err) {
    container.innerHTML = `<p class="error-msg">Error: ${err.message}</p>`;
    return;
  }
  draw(container, groups);
}

function draw(container, groups) {
  container.innerHTML = `
    <div class="card">
      <div class="card-header">
        <strong>Grouped Songs (${groups.length})</strong>
        <button class="btn btn-primary btn-sm" id="btn-new">+ New Group</button>
      </div>
      <div id="new-form" style="display:none" class="inline-panel mb-12">
        ${groupForm()}
        <div class="flex-row mt-8">
          <button class="btn btn-primary btn-sm" id="btn-new-save">Save</button>
          <button class="btn btn-secondary btn-sm" id="btn-new-cancel">Cancel</button>
        </div>
      </div>
      <ul class="file-list" id="group-list"></ul>
    </div>`;

  renderList(container, groups);

  container.querySelector("#btn-new").onclick = () => {
    container.querySelector("#new-form").style.display = "block";
  };
  container.querySelector("#btn-new-cancel").onclick = () => {
    container.querySelector("#new-form").style.display = "none";
  };
  container.querySelector("#btn-new-save").onclick = async () => {
    const entry = readForm(container.querySelector("#new-form"));
    if (!entry) return;
    try {
      await api("POST", "/api/grouped-songs/", entry);
      showToast("Group created");
      render(container);
    } catch (err) { showToast(err.message, "error"); }
  };
}

function renderList(container, groups) {
  const list = container.querySelector("#group-list");
  const sorted = [...groups].sort((a, b) => {
    const ac = a.artist.toLowerCase(), bc = b.artist.toLowerCase();
    if (ac !== bc) return ac < bc ? -1 : 1;
    return a.group_name.toLowerCase().localeCompare(b.group_name.toLowerCase());
  });
  list.innerHTML = groups.length
    ? sorted.map((g) => {
        const i = groups.indexOf(g);
        return `
      <li data-index="${i}">
        <span class="file-name">${escHtml(g.artist)} - ${escHtml(g.group_name)} (${g.songs.length})</span>
        <button class="btn btn-secondary btn-sm" data-action="edit" data-index="${i}">Edit</button>
        <button class="btn btn-danger btn-sm" data-action="delete" data-index="${i}">Delete</button>
      </li>`;
      }).join("")
    : `<li style="color:#888">No groups.</li>`;

  list.querySelectorAll("[data-action]").forEach((btn) => {
    btn.onclick = () => handleAction(btn.dataset.action, parseInt(btn.dataset.index), groups, container, btn);
  });
}

function closeInlinePanel(list) {
  list.querySelectorAll(".inline-item-panel").forEach((el) => el.remove());
}

async function handleAction(action, index, groups, container, triggerBtn) {
  const list = container.querySelector("#group-list");

  if (action === "delete") {
    const ok = await showConfirm(`Delete group "${groups[index].group_name}"?`);
    if (!ok) return;
    try {
      await api("DELETE", `/api/grouped-songs/${index}`);
      showToast("Deleted");
      render(container);
    } catch (err) { showToast(err.message, "error"); }
    return;
  }

  const existingPanel = triggerBtn.closest("li").nextElementSibling;
  const isSamePanel = existingPanel?.classList.contains("inline-item-panel") &&
                      existingPanel.dataset.for === `edit:${index}`;
  closeInlinePanel(list);
  if (isSamePanel) return;

  const g = groups[index];
  const editSongs = [...g.songs];

  let songMap = new Map();
  try {
    const allSongs = await api("GET", "/api/songs/");
    for (const s of allSongs) {
      if (s.link) songMap.set(s.link, s);
    }
  } catch (_) { /* fall back to URL-only display */ }

  const panel = document.createElement("li");
  panel.className = "inline-item-panel";
  panel.dataset.for = `edit:${index}`;
  panel.innerHTML = `
    <div class="inline-panel" style="width:100%">
      <div class="card-header" style="margin-bottom:8px"><strong>Edit Group</strong></div>
      <div class="form-group"><label>Artist</label><input class="f-artist" type="text" value="${escHtml(g.artist || "")}"></div>
      <div class="form-group"><label>Group Name</label><input class="f-group_name" type="text" value="${escHtml(g.group_name || "")}"></div>
      <div class="form-group mt-8"><label>Songs</label><div class="songs-table-wrap"></div></div>
      <div class="flex-row mt-8">
        <button class="btn btn-primary btn-sm save-btn">Save</button>
        <button class="btn btn-secondary btn-sm close-panel-btn">Cancel</button>
      </div>
    </div>`;

  panel.querySelector(".close-panel-btn").onclick = () => panel.remove();

  renderSongsEditTable(panel.querySelector(".songs-table-wrap"), editSongs, songMap);

  panel.querySelector(".save-btn").onclick = async () => {
    const artist = panel.querySelector(".f-artist").value.trim();
    const group_name = panel.querySelector(".f-group_name").value.trim();
    if (!artist || !group_name) { showToast("Artist and Group Name required", "error"); return; }
    try {
      await api("PUT", `/api/grouped-songs/${index}`, { artist, group_name, songs: editSongs });
      showToast("Saved");
      render(container);
    } catch (err) { showToast(err.message, "error"); }
  };

  triggerBtn.closest("li").after(panel);
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderSongsEditTable(wrap, songs, songMap) {
  if (!songs.length) {
    wrap.innerHTML = `<p style="color:#888;padding:4px 0">No songs.</p>`;
    return;
  }
  wrap.innerHTML = `
    <table style="width:100%;border-collapse:collapse;font-size:13px;margin-top:4px">
      <thead>
        <tr style="color:#888">
          <th style="padding:3px 6px;text-align:right;font-weight:normal">#</th>
          <th style="padding:3px 6px;text-align:left;font-weight:normal">Artist</th>
          <th style="padding:3px 6px;text-align:left;font-weight:normal">Album</th>
          <th style="padding:3px 6px;text-align:right;font-weight:normal">Track</th>
          <th style="padding:3px 6px;text-align:left;font-weight:normal">Title</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        ${songs.map((url, i) => {
          const s = songMap.get(url);
          return `
          <tr>
            <td style="padding:3px 6px;color:#888;text-align:right">${i + 1}</td>
            <td style="padding:3px 6px" title="${escHtml(url)}">${escHtml(s?.artist || "—")}</td>
            <td style="padding:3px 6px">${escHtml(s?.album  || "—")}</td>
            <td style="padding:3px 6px;text-align:right">${s?.track ?? "—"}</td>
            <td style="padding:3px 6px">${escHtml(s?.title  || "—")}</td>
            <td style="padding:3px 4px;white-space:nowrap">
              <button class="btn btn-secondary btn-sm" data-action="up"     data-idx="${i}" ${i === 0                 ? "disabled" : ""}>▲</button>
              <button class="btn btn-secondary btn-sm" data-action="down"   data-idx="${i}" ${i === songs.length - 1 ? "disabled" : ""}>▼</button>
              <button class="btn btn-danger    btn-sm" data-action="remove" data-idx="${i}">Remove</button>
            </td>
          </tr>`;
        }).join("")}
      </tbody>
    </table>`;

  wrap.querySelectorAll("[data-action='up']").forEach((btn) => {
    btn.onclick = () => {
      const i = parseInt(btn.dataset.idx, 10);
      [songs[i - 1], songs[i]] = [songs[i], songs[i - 1]];
      renderSongsEditTable(wrap, songs, songMap);
    };
  });

  wrap.querySelectorAll("[data-action='down']").forEach((btn) => {
    btn.onclick = () => {
      const i = parseInt(btn.dataset.idx, 10);
      [songs[i], songs[i + 1]] = [songs[i + 1], songs[i]];
      renderSongsEditTable(wrap, songs, songMap);
    };
  });

  wrap.querySelectorAll("[data-action='remove']").forEach((btn) => {
    btn.onclick = () => {
      songs.splice(parseInt(btn.dataset.idx, 10), 1);
      renderSongsEditTable(wrap, songs, songMap);
    };
  });
}

function groupForm(g = {}) {
  return `
    <div class="form-group"><label>Artist</label><input class="f-artist" type="text" value="${escHtml(g.artist || "")}"></div>
    <div class="form-group"><label>Group Name</label><input class="f-group_name" type="text" value="${escHtml(g.group_name || "")}"></div>
    <div class="form-group"><label>Songs (one Spotify URL per line)</label>
      <textarea class="f-songs">${escHtml((g.songs || []).join("\n"))}</textarea></div>`;
}

function readForm(el) {
  const artist = el.querySelector(".f-artist").value.trim();
  const group_name = el.querySelector(".f-group_name").value.trim();
  const songs = el.querySelector(".f-songs").value.split("\n").map((l) => l.trim()).filter(Boolean);
  if (!artist || !group_name) { showToast("Artist and Group Name required", "error"); return null; }
  return { artist, group_name, songs };
}

function escHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
