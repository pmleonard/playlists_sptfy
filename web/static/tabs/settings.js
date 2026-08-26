import { api, showToast } from "/static/app.js";

const LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"];

export async function render(container) {
  container.innerHTML = `<p class="loading">Loading…</p>`;
  let settings;
  try {
    settings = await api("GET", "/api/settings/");
  } catch (err) {
    container.innerHTML = `<p class="error-msg">Error: ${err.message}</p>`;
    return;
  }
  draw(container, settings);
}

function draw(container, settings) {
  container.innerHTML = `
    <div class="card">
      <div class="card-header"><strong>Settings</strong></div>
      <div id="fields-container">
        ${Object.entries(settings).map(([k, v]) => fieldHtml(k, v)).join("")}
      </div>
      <div class="mt-16">
        <button class="btn btn-primary" id="btn-save">Save Settings</button>
      </div>
    </div>`;

  container.querySelector("#btn-save").onclick = async () => {
    const body = readFields(container, settings);
    try {
      await api("PUT", "/api/settings/", body);
      showToast("Settings saved");
    } catch (err) { showToast(err.message, "error"); }
  };
}

function fieldHtml(key, value) {
  if (key === "log_level") {
    const opts = LOG_LEVELS.map((l) =>
      `<option value="${l}" ${l === value ? "selected" : ""}>${l}</option>`
    ).join("");
    return `<div class="form-group"><label>${key}</label><select data-key="${key}">${opts}</select></div>`;
  }
  if (typeof value === "boolean") {
    return `
      <div class="form-group" style="display:flex;align-items:center;gap:8px">
        <input type="checkbox" data-key="${key}" id="field-${key}" ${value ? "checked" : ""}>
        <label for="field-${key}" style="font-weight:normal">${key}</label>
      </div>`;
  }
  if (typeof value === "number") {
    return `<div class="form-group"><label>${key}</label><input type="number" data-key="${key}" value="${value}"></div>`;
  }
  return `<div class="form-group"><label>${key}</label><input type="text" data-key="${key}" value="${escHtml(String(value))}"></div>`;
}

function readFields(container, original) {
  const result = {};
  for (const [key, origVal] of Object.entries(original)) {
    const el = container.querySelector(`[data-key="${key}"]`);
    if (!el) continue;
    if (typeof origVal === "boolean") {
      result[key] = el.checked;
    } else if (typeof origVal === "number") {
      result[key] = Number(el.value);
    } else {
      result[key] = el.value;
    }
  }
  return result;
}

function escHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
