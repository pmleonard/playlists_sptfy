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
  list.innerHTML = groups.length
    ? groups.map((g, i) => `
      <li data-index="${i}">
        <span class="file-name">${escHtml(g.group_name)} <small style="color:#888">(${escHtml(g.artist)})</small></span>
        <button class="btn btn-secondary btn-sm" data-action="edit" data-index="${i}">Edit</button>
        <button class="btn btn-danger btn-sm" data-action="delete" data-index="${i}">Delete</button>
      </li>`).join("")
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
  const panel = document.createElement("li");
  panel.className = "inline-item-panel";
  panel.dataset.for = `edit:${index}`;
  panel.innerHTML = `
    <div class="inline-panel" style="width:100%">
      <div class="card-header" style="margin-bottom:8px"><strong>Edit Group</strong></div>
      <div class="edit-form">${groupForm(g)}</div>
      <div class="flex-row mt-8">
        <button class="btn btn-primary btn-sm save-btn">Save</button>
        <button class="btn btn-secondary btn-sm close-panel-btn">Cancel</button>
      </div>
    </div>`;

  panel.querySelector(".close-panel-btn").onclick = () => panel.remove();
  panel.querySelector(".save-btn").onclick = async () => {
    const entry = readForm(panel.querySelector(".edit-form"));
    if (!entry) return;
    try {
      await api("PUT", `/api/grouped-songs/${index}`, entry);
      showToast("Saved");
      render(container);
    } catch (err) { showToast(err.message, "error"); }
  };

  triggerBtn.closest("li").after(panel);
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
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
