import { api, showToast, showConfirm } from "/static/app.js";

const BASE = "/api/ignore-duplicates";

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
        <strong>Ignored Duplicates (${keys.length} entries)</strong>
        <button class="btn btn-primary btn-sm" id="btn-new">+ New Entry</button>
      </div>
      <div id="new-form" style="display:none" class="inline-panel mb-12">
        <div class="form-group"><label>Key (song title)</label><input type="text" id="new-key"></div>
        <div id="new-songs-container"></div>
        <div class="flex-row mt-8">
          <button class="btn btn-secondary btn-sm" id="btn-add-song">+ Add Song</button>
          <button class="btn btn-primary btn-sm" id="btn-new-save">Save</button>
          <button class="btn btn-secondary btn-sm" id="btn-new-cancel">Cancel</button>
        </div>
      </div>
      <ul class="file-list" id="entry-list"></ul>
    </div>`;

  renderList(container, data);
  setupNewForm(container, data);
}

function renderList(container, data) {
  const list = container.querySelector("#entry-list");
  const keys = Object.keys(data);
  list.innerHTML = keys.length
    ? keys.map((k) => `
      <li data-key="${escHtml(k)}">
        <span class="file-name">${escHtml(k)} <small style="color:#888">(${data[k].length} songs)</small></span>
        <button class="btn btn-secondary btn-sm" data-action="edit" data-key="${escHtml(k)}">View/Edit</button>
        <button class="btn btn-danger btn-sm" data-action="delete" data-key="${escHtml(k)}">Delete</button>
      </li>`).join("")
    : `<li style="color:#888">No entries.</li>`;

  list.querySelectorAll("[data-action]").forEach((btn) => {
    btn.onclick = () => handleAction(btn.dataset.action, btn.dataset.key, data, container, btn);
  });
}

function setupNewForm(container) {
  container.querySelector("#btn-new").onclick = () => {
    const form = container.querySelector("#new-form");
    form.style.display = "block";
    addSongSubform(container.querySelector("#new-songs-container"));
  };
  container.querySelector("#btn-new-cancel").onclick = () => {
    container.querySelector("#new-form").style.display = "none";
    container.querySelector("#new-songs-container").innerHTML = "";
  };
  container.querySelector("#btn-add-song").onclick = () => {
    addSongSubform(container.querySelector("#new-songs-container"));
  };
  container.querySelector("#btn-new-save").onclick = async () => {
    const key = container.querySelector("#new-key").value.trim();
    if (!key) { showToast("Key required", "error"); return; }
    const songs = readSongSubforms(container.querySelector("#new-songs-container"));
    try {
      await api("POST", `${BASE}/`, { key, songs });
      showToast("Entry created");
      render(container);
    } catch (err) { showToast(err.message, "error"); }
  };
}

function closeInlinePanel(list) {
  list.querySelectorAll(".inline-item-panel").forEach((el) => el.remove());
}

async function handleAction(action, key, data, container, triggerBtn) {
  const list = container.querySelector("#entry-list");

  if (action === "delete") {
    const ok = await showConfirm(`Delete entry "${key}"?`);
    if (!ok) return;
    try {
      await api("DELETE", `${BASE}/${encodeURIComponent(key)}`);
      showToast("Deleted");
      render(container);
    } catch (err) { showToast(err.message, "error"); }
    return;
  }

  const existingPanel = triggerBtn.closest("li").nextElementSibling;
  const isSamePanel = existingPanel?.classList.contains("inline-item-panel") &&
                      existingPanel.dataset.for === key;
  closeInlinePanel(list);
  if (isSamePanel) return;

  const songs = data[key] || [];
  const panel = document.createElement("li");
  panel.className = "inline-item-panel";
  panel.dataset.for = key;
  panel.innerHTML = `
    <div class="inline-panel" style="width:100%">
      <div class="card-header" style="margin-bottom:8px"><strong>Edit: ${escHtml(key)}</strong></div>
      <div class="edit-songs-container"></div>
      <div class="flex-row mt-8">
        <button class="btn btn-secondary btn-sm btn-add-song">+ Add Song</button>
        <button class="btn btn-primary btn-sm save-btn">Save</button>
        <button class="btn btn-secondary btn-sm close-panel-btn">Cancel</button>
      </div>
    </div>`;

  const sc = panel.querySelector(".edit-songs-container");
  songs.forEach((s) => addSongSubform(sc, s));
  panel.querySelector(".btn-add-song").onclick = () => addSongSubform(sc);
  panel.querySelector(".close-panel-btn").onclick = () => panel.remove();
  panel.querySelector(".save-btn").onclick = async () => {
    const updated = readSongSubforms(sc);
    try {
      await api("PUT", `${BASE}/${encodeURIComponent(key)}`, { songs: updated });
      showToast("Saved");
      render(container);
    } catch (err) { showToast(err.message, "error"); }
  };

  triggerBtn.closest("li").after(panel);
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function addSongSubform(container, song = {}) {
  const div = document.createElement("div");
  div.className = "song-subform";
  div.innerHTML = `
    <div class="song-subform-grid">
      <div class="form-group"><label>Link</label><input class="sf-link" type="text" value="${escHtml(song.link || "")}"></div>
      <div class="form-group"><label>Artist</label><input class="sf-artist" type="text" value="${escHtml(song.artist || "")}"></div>
      <div class="form-group"><label>Title</label><input class="sf-title" type="text" value="${escHtml(song.title || "")}"></div>
      <div class="form-group"><label>Released</label><input class="sf-released" type="text" value="${escHtml(song.released || "")}"></div>
      <div class="form-group"><label>Duration (s)</label><input class="sf-duration" type="text" value="${escHtml(String(song.duration || ""))}"></div>
      <div class="form-group"><label>Album</label><input class="sf-album" type="text" value="${escHtml(song.album || "")}"></div>
      <div class="form-group"><label>Track</label><input class="sf-track" type="text" value="${escHtml(String(song.track || ""))}"></div>
      <div class="form-group"><label>Tags</label><input class="sf-tags" type="text" value="${escHtml(song.tags || "")}"></div>
    </div>
    <button class="btn btn-danger btn-sm mt-8 remove-song-btn">Remove</button>`;
  div.querySelector(".remove-song-btn").onclick = () => div.remove();
  container.appendChild(div);
}

function readSongSubforms(container) {
  return [...container.querySelectorAll(".song-subform")].map((el) => ({
    link: el.querySelector(".sf-link").value.trim(),
    artist: el.querySelector(".sf-artist").value.trim(),
    title: el.querySelector(".sf-title").value.trim(),
    released: el.querySelector(".sf-released").value.trim(),
    duration: el.querySelector(".sf-duration").value.trim(),
    album: el.querySelector(".sf-album").value.trim(),
    track: el.querySelector(".sf-track").value.trim(),
    tags: el.querySelector(".sf-tags").value.trim(),
  }));
}

function escHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
