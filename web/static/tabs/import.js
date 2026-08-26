import { api, showToast, showConfirm } from "/static/app.js";

export async function render(container) {
  container.innerHTML = `<p class="loading">Loading…</p>`;
  let files;
  try {
    files = await api("GET", "/api/import/");
  } catch (err) {
    container.innerHTML = `<p class="error-msg">Error: ${err.message}</p>`;
    return;
  }
  draw(container, files);
}

function draw(container, files) {
  container.innerHTML = `
    <div class="card">
      <div class="card-header">
        <strong>Import Files</strong>
        <button class="btn btn-primary btn-sm" id="btn-new">+ New File</button>
      </div>
      <div id="new-form" style="display:none" class="inline-panel mb-12">
        <div class="form-group"><label>File name (no extension)</label><input type="text" id="new-name"></div>
        <div class="form-group"><label>Content (one URL per line)</label><textarea id="new-content"></textarea></div>
        <div class="flex-row"><button class="btn btn-primary btn-sm" id="btn-new-save">Save</button><button class="btn btn-secondary btn-sm" id="btn-new-cancel">Cancel</button></div>
      </div>
      <ul class="file-list" id="file-list"></ul>
    </div>`;

  renderList(container.querySelector("#file-list"), files, container);

  container.querySelector("#btn-new").onclick = () => {
    container.querySelector("#new-form").style.display = "block";
  };
  container.querySelector("#btn-new-cancel").onclick = () => {
    container.querySelector("#new-form").style.display = "none";
  };
  container.querySelector("#btn-new-save").onclick = async () => {
    const name = container.querySelector("#new-name").value.trim();
    const content = container.querySelector("#new-content").value;
    if (!name) { showToast("Name required", "error"); return; }
    try {
      await api("POST", `/api/import/${name}`, { content });
      showToast(`Created ${name}`);
      render(container);
    } catch (err) { showToast(err.message, "error"); }
  };
}

function renderList(list, files, container) {
  list.innerHTML = files.length
    ? files.map((f) => `
      <li data-name="${f}">
        <span class="file-name">${f}</span>
        <button class="btn btn-secondary btn-sm" data-action="view" data-name="${f}">View</button>
        <button class="btn btn-secondary btn-sm" data-action="edit" data-name="${f}">Edit</button>
        <button class="btn btn-danger btn-sm" data-action="delete" data-name="${f}">Delete</button>
      </li>`).join("")
    : `<li style="color:#888">No import files found.</li>`;

  list.querySelectorAll("[data-action]").forEach((btn) => {
    btn.onclick = () => handleAction(btn.dataset.action, btn.dataset.name, btn, container);
  });
}

function closeInlinePanel(list) {
  list.querySelectorAll(".inline-item-panel").forEach((el) => el.remove());
}

async function handleAction(action, name, triggerBtn, container) {
  const list = container.querySelector("#file-list");

  if (action === "delete") {
    const ok = await showConfirm(`Delete "${name}.txt"?`);
    if (!ok) return;
    try {
      await api("DELETE", `/api/import/${name}`);
      showToast(`Deleted ${name}`);
      render(container);
    } catch (err) { showToast(err.message, "error"); }
    return;
  }

  // Close any open panel; if clicking same item's same action, just close and return
  const existingPanel = triggerBtn.closest("li").nextElementSibling;
  const isSamePanel = existingPanel?.classList.contains("inline-item-panel") &&
                      existingPanel.dataset.for === `${action}:${name}`;
  closeInlinePanel(list);
  if (isSamePanel) return;

  let content = "";
  try {
    const res = await api("GET", `/api/import/${name}`);
    content = res.content;
  } catch (err) { showToast(err.message, "error"); return; }

  const panel = document.createElement("li");
  panel.className = "inline-item-panel";
  panel.dataset.for = `${action}:${name}`;

  if (action === "view") {
    panel.innerHTML = `
      <div class="inline-panel" style="width:100%">
        <div class="card-header" style="margin-bottom:8px"><strong>${name}.txt</strong>
          <button class="btn btn-secondary btn-sm close-panel-btn">✕</button>
        </div>
        <pre style="white-space:pre-wrap;font-size:12px;font-family:monospace;max-height:300px;overflow-y:auto">${escHtml(content)}</pre>
      </div>`;
    panel.querySelector(".close-panel-btn").onclick = () => panel.remove();
  } else {
    panel.innerHTML = `
      <div class="inline-panel" style="width:100%">
        <div class="card-header" style="margin-bottom:8px"><strong>Edit: ${name}.txt</strong></div>
        <div class="form-group"><textarea class="edit-content">${escHtml(content)}</textarea></div>
        <div class="flex-row">
          <button class="btn btn-primary btn-sm save-btn">Save</button>
          <button class="btn btn-secondary btn-sm close-panel-btn">Cancel</button>
        </div>
      </div>`;
    panel.querySelector(".close-panel-btn").onclick = () => panel.remove();
    panel.querySelector(".save-btn").onclick = async () => {
      const newContent = panel.querySelector(".edit-content").value;
      try {
        await api("PUT", `/api/import/${name}`, { content: newContent });
        showToast(`Saved ${name}`);
        panel.remove();
      } catch (err) { showToast(err.message, "error"); }
    };
  }

  triggerBtn.closest("li").after(panel);
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function escHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
