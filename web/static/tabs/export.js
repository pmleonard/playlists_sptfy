import { api, showToast } from "/static/app.js";

export async function render(container) {
  container.innerHTML = `<p class="loading">Loading…</p>`;
  let files;
  try {
    files = await api("GET", "/api/export/");
  } catch (err) {
    container.innerHTML = `<p class="error-msg">Error: ${err.message}</p>`;
    return;
  }

  container.innerHTML = `
    <div class="card">
      <div class="card-header"><strong>Export Files</strong></div>
      <ul class="file-list">
        ${files.length
          ? files.map((f) => `
            <li>
              <span class="file-name">${f}</span>
              <button class="btn btn-secondary btn-sm" data-action="view" data-name="${f}">View</button>
              <button class="btn btn-primary btn-sm" data-action="copy" data-name="${f}">Copy All</button>
            </li>`).join("")
          : `<li style="color:#888">No export files found.</li>`}
      </ul>
    </div>
    <div id="detail-panel"></div>`;

  container.querySelectorAll("[data-action]").forEach((btn) => {
    btn.onclick = () => handleAction(btn.dataset.action, btn.dataset.name, container);
  });
}

async function handleAction(action, name, container) {
  let content;
  try {
    const res = await api("GET", `/api/export/${name}`);
    content = res.content;
  } catch (err) { showToast(err.message, "error"); return; }

  if (action === "copy") {
    try {
      await navigator.clipboard.writeText(content);
      showToast(`Copied ${name} to clipboard`);
    } catch {
      showToast("Clipboard access denied", "error");
    }
    return;
  }

  const panel = container.querySelector("#detail-panel");
  panel.innerHTML = `
    <div class="card">
      <div class="card-header">
        <strong>${name}.txt</strong>
        <div class="flex-row">
          <button class="btn btn-primary btn-sm" id="copy-btn">Copy All</button>
          <button class="btn btn-secondary btn-sm" id="close-btn">✕</button>
        </div>
      </div>
      <pre style="white-space:pre-wrap;font-size:12px;font-family:monospace;max-height:400px;overflow-y:auto">${escHtml(content)}</pre>
    </div>`;
  panel.querySelector("#close-btn").onclick = () => { panel.innerHTML = ""; };
  panel.querySelector("#copy-btn").onclick = async () => {
    try {
      await navigator.clipboard.writeText(content);
      showToast(`Copied ${name} to clipboard`);
    } catch { showToast("Clipboard access denied", "error"); }
  };
}

function escHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
