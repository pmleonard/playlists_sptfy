import { api, showToast } from "/static/app.js";

export async function render(container) {
  container.innerHTML = `<p class="loading">Loading…</p>`;
  let config;
  try {
    config = await api("GET", "/api/config/");
  } catch (err) {
    container.innerHTML = `<p class="error-msg">Error: ${err.message}</p>`;
    return;
  }
  draw(container, config);
}

function draw(container, config) {
  const pathFields = [
    "song_list_path", "grouped_songs_path", "songs_csv_path",
    "duplicates_path", "duplicates_report_path", "ignore_duplicates_path",
    "playlist_export_path", "run_summary_path",
  ];

  const exports = config.playlist_exports || [];

  container.innerHTML = `
    <div class="card">
      <div class="card-header"><strong>Config</strong></div>
      ${pathFields.map((f) => `
        <div class="form-group">
          <label>${f}</label>
          <input type="text" data-field="${f}" value="${escHtml(config[f] || "")}">
        </div>`).join("")}

      <div class="mt-16 mb-12"><strong>Playlist Exports</strong></div>
      <div id="exports-container">
        ${exports.map((ex, i) => exportSubform(ex, i)).join("")}
      </div>
      <div class="flex-row mt-8">
        <button class="btn btn-secondary btn-sm" id="btn-add-export">+ Add Export</button>
        <button class="btn btn-primary" id="btn-save">Save Config</button>
      </div>
    </div>`;

  container.querySelector("#btn-add-export").onclick = () => {
    const ec = container.querySelector("#exports-container");
    const idx = ec.querySelectorAll(".export-item").length;
    ec.insertAdjacentHTML("beforeend", exportSubform({}, idx));
    bindRemoveButtons(container);
  };

  bindRemoveButtons(container);

  container.querySelector("#btn-save").onclick = async () => {
    const body = {};
    pathFields.forEach((f) => {
      body[f] = container.querySelector(`[data-field="${f}"]`).value.trim();
    });
    body.playlist_exports = readExports(container);
    try {
      await api("PUT", "/api/config/", body);
      showToast("Config saved");
    } catch (err) { showToast(err.message, "error"); }
  };
}

function exportSubform(ex, i) {
  const inc = (ex.tags_filter?.include || []).join(", ");
  const excl = (ex.tags_filter?.exclude || []).join(", ");
  return `
    <div class="export-item" data-export-idx="${i}">
      <div class="export-item-header">
        <strong>Export ${i + 1}</strong>
        <button class="btn btn-danger btn-sm remove-export-btn">Remove</button>
      </div>
      <div class="form-group"><label>Filename</label><input class="ex-filename" type="text" value="${escHtml(ex.filename || "")}"></div>
      <div class="form-group" style="display:flex;align-items:center;gap:8px">
        <input class="ex-random" type="checkbox" id="ex-random-${i}" ${ex.random ? "checked" : ""}>
        <label for="ex-random-${i}" style="font-weight:normal">Random order</label>
      </div>
      <div class="form-group"><label>Include tags (comma-separated)</label><input class="ex-include" type="text" value="${escHtml(inc)}"></div>
      <div class="form-group"><label>Exclude tags (comma-separated)</label><input class="ex-exclude" type="text" value="${escHtml(excl)}"></div>
    </div>`;
}

function bindRemoveButtons(container) {
  container.querySelectorAll(".remove-export-btn").forEach((btn) => {
    btn.onclick = () => btn.closest(".export-item").remove();
  });
}

function readExports(container) {
  return [...container.querySelectorAll(".export-item")].map((el) => ({
    filename: el.querySelector(".ex-filename").value.trim(),
    random: el.querySelector(".ex-random").checked,
    tags_filter: {
      include: el.querySelector(".ex-include").value.split(",").map((t) => t.trim()).filter(Boolean),
      exclude: el.querySelector(".ex-exclude").value.split(",").map((t) => t.trim()).filter(Boolean),
    },
  }));
}

function escHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
