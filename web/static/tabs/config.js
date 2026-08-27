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
      <div style="overflow-x:auto">
        <table id="exports-table" style="width:100%;border-collapse:collapse;font-size:13px">
          <thead>
            <tr style="color:#888">
              <th style="text-align:left;padding:4px 6px;font-weight:normal">Filename</th>
              <th style="text-align:center;padding:4px 6px;font-weight:normal">Random</th>
              <th style="text-align:left;padding:4px 6px;font-weight:normal">Include Tags</th>
              <th style="text-align:left;padding:4px 6px;font-weight:normal">Exclude Tags</th>
              <th></th>
            </tr>
          </thead>
          <tbody id="exports-body">
            ${exports.map((ex) => exportRow(ex)).join("")}
          </tbody>
        </table>
      </div>
      <div class="flex-row mt-8">
        <button class="btn btn-secondary btn-sm" id="btn-add-export">+ Add Export</button>
        <button class="btn btn-primary" id="btn-save">Save Config</button>
      </div>
    </div>`;

  container.querySelector("#btn-add-export").onclick = () => {
    container.querySelector("#exports-body").insertAdjacentHTML("beforeend", exportRow({}));
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

function exportRow(ex) {
  const inc = (ex.tags_filter?.include || []).join(", ");
  const excl = (ex.tags_filter?.exclude || []).join(", ");
  return `
    <tr class="export-row">
      <td style="padding:4px 6px"><input class="ex-filename" type="text" value="${escHtml(ex.filename || "")}" style="width:100%"></td>
      <td style="padding:4px 6px;text-align:center"><input class="ex-random" type="checkbox" ${ex.random ? "checked" : ""}></td>
      <td style="padding:4px 6px"><input class="ex-include" type="text" value="${escHtml(inc)}" style="width:100%"></td>
      <td style="padding:4px 6px"><input class="ex-exclude" type="text" value="${escHtml(excl)}" style="width:100%"></td>
      <td style="padding:4px 6px"><button class="btn btn-danger btn-sm remove-export-btn">Remove</button></td>
    </tr>`;
}

function bindRemoveButtons(container) {
  container.querySelectorAll(".remove-export-btn").forEach((btn) => {
    btn.onclick = () => btn.closest(".export-row").remove();
  });
}

function readExports(container) {
  return [...container.querySelectorAll(".export-row")].map((el) => ({
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
