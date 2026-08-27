import { api, showToast } from "/static/app.js";

export async function render(container) {
  container.innerHTML = `
    <div class="card">
      <div class="card-header"><strong>Update</strong></div>
      <div class="flex-row mt-8">
        <button class="btn btn-primary" id="btn-run">Run (make run)</button>
        <span id="run-status" style="color:#888"></span>
      </div>
      <div id="summary-output" style="margin-top:16px"></div>
    </div>`;

  container.querySelector("#btn-run").onclick = () => runScript(container);
}

async function runScript(container) {
  const btn = container.querySelector("#btn-run");
  const status = container.querySelector("#run-status");
  btn.disabled = true;
  status.textContent = "Running…";
  container.querySelector("#summary-output").innerHTML = "";

  try {
    const result = await api("POST", "/api/update/run");
    if (result.ok) {
      status.textContent = "Completed successfully.";
      await loadSummary(container);
    } else {
      status.textContent = `Failed (exit code ${result.returncode}).`;
      container.querySelector("#summary-output").innerHTML =
        `<pre class="error-msg" style="white-space:pre-wrap;word-break:break-all">${escHtml(result.stderr)}</pre>`;
    }
  } catch (err) {
    showToast(err.message, "error");
    status.textContent = "Error — see toast.";
  } finally {
    btn.disabled = false;
  }
}

async function loadSummary(container) {
  try {
    const data = await api("GET", "/api/update/summary");
    container.querySelector("#summary-output").innerHTML = renderSummary(data);
  } catch (err) {
    container.querySelector("#summary-output").innerHTML =
      `<p class="error-msg">Could not load summary: ${escHtml(err.message)}</p>`;
  }
}

function renderSummary(data) {
  const skip = new Set(["tags_summary"]);
  const rows = Object.entries(data)
    .filter(([k]) => !skip.has(k))
    .map(([k, v]) => `
      <tr>
        <td style="padding:4px 8px;font-weight:500">${escHtml(k)}</td>
        <td style="padding:4px 8px">${escHtml(String(v))}</td>
      </tr>`).join("");

  let tagTable = "";
  if (data.tags_summary?.tag_counts) {
    const tagRows = data.tags_summary.tag_counts.map((t) => `
      <tr>
        <td style="padding:3px 8px">${escHtml(t.tag)}</td>
        <td style="padding:3px 8px">${t.count}</td>
      </tr>`).join("");
    tagTable = `
      <h3 style="margin:16px 0 8px">Tags</h3>
      <table style="border-collapse:collapse;font-size:13px">
        <thead><tr>
          <th style="text-align:left;padding:3px 8px">Tag</th>
          <th style="text-align:left;padding:3px 8px">Count</th>
        </tr></thead>
        <tbody>${tagRows}</tbody>
      </table>`;
  }

  return `
    <h3 style="margin:0 0 8px">Run Summary</h3>
    <table style="border-collapse:collapse;font-size:13px">
      <tbody>${rows}</tbody>
    </table>
    ${tagTable}`;
}

function escHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
