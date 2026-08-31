import { api, showToast, showConfirm } from "/static/app.js";

let clusters = [];

export async function render(container) {
  container.innerHTML = `<p class="loading">Loading…</p>`;
  try {
    clusters = await api("GET", "/api/album-review/");
  } catch (err) {
    container.innerHTML = `<p class="error-msg">Error: ${err.message}</p>`;
    return;
  }
  draw(container);
}

function draw(container) {
  if (!clusters.length) {
    container.innerHTML = `<p style="color:#888">No split or incomplete albums found.</p>`;
    return;
  }

  container.innerHTML = clusters.map((c, ci) => clusterHtml(c, ci)).join("");

  container.querySelectorAll("[data-action='merge']").forEach((btn) => {
    btn.addEventListener("click", () => handleMerge(container, btn));
  });
}

function clusterHtml(c, ci) {
  const maxVariant = c.variants.reduce(
    (a, b) => (b.track_count > a.track_count ? b : a),
    c.variants[0]
  );
  const options = c.variants
    .map(
      (v) =>
        `<option value="${escHtml(v.album)}" ${v.album === maxVariant.album ? "selected" : ""}>${escHtml(v.album)}</option>`
    )
    .join("");

  return `
    <div class="card" data-cluster="${ci}">
      <div class="card-header"><strong>${escHtml(c.artist)} — ${escHtml(c.normalized_key)}</strong></div>
      <div style="overflow-x:auto">
        <table>
          <thead>
            <tr><th>Album</th><th>Track Count</th><th>Tracks</th></tr>
          </thead>
          <tbody>
            ${c.variants
              .map(
                (v) => `
              <tr>
                <td title="${escHtml(v.album)}">${escHtml(v.album)}</td>
                <td>${v.track_count}</td>
                <td>${v.tracks.join(", ")}</td>
              </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>
      ${c.gaps.length ? `<p class="mt-8">Missing track numbers: ${c.gaps.join(", ")}</p>` : ""}
      <div class="merge-controls flex-row mt-8">
        <select class="merge-select">${options}</select>
        <input class="merge-input" type="text" placeholder="or type a new album name…" style="flex:1">
        <button class="btn btn-primary btn-sm" data-action="merge" data-cluster="${ci}">Merge</button>
      </div>
    </div>`;
}

async function handleMerge(container, btn) {
  const ci = parseInt(btn.dataset.cluster, 10);
  const cluster = clusters[ci];
  const card = btn.closest(".card");
  const select = card.querySelector(".merge-select");
  const input = card.querySelector(".merge-input");
  const toAlbum = input.value.trim() || select.value;

  const sourceVariants = cluster.variants.filter((v) => v.album !== toAlbum);
  const fromAlbums = sourceVariants.map((v) => v.album);
  const songCount = sourceVariants.reduce((sum, v) => sum + v.track_count, 0);

  if (!fromAlbums.length) {
    showToast("Nothing to merge — pick a different target or type a new name", "error");
    return;
  }

  const ok = await showConfirm(
    `Merge ${fromAlbums.length} variant(s) — ${songCount} song(s) — into "${toAlbum}"?`
  );
  if (!ok) return;

  btn.disabled = true;
  try {
    const result = await api("POST", "/api/album-review/merge", {
      artist: cluster.artist,
      from_albums: fromAlbums,
      to_album: toAlbum,
    });
    showToast(`Merged (${result.changed} song(s) updated)`);

    if (result.changed !== songCount) {
      // Unexpected count — don't trust our local model, re-fetch from the server.
      render(container);
      return;
    }

    // All variants now share one album name. Track numbers are untouched by a
    // rename, so the union (and therefore any gaps) is unchanged — the cluster
    // fully resolves only if it had no gaps; otherwise it collapses to one
    // variant but stays in the list (US-04 AC4).
    const unionTracks = [...new Set(cluster.variants.flatMap((v) => v.tracks))].sort((a, b) => a - b);
    if (cluster.gaps.length === 0) {
      clusters = clusters.filter((_, i) => i !== ci);
    } else {
      clusters = clusters.map((c, i) =>
        i === ci
          ? { ...c, variants: [{ album: toAlbum, track_count: unionTracks.length, tracks: unionTracks }] }
          : c
      );
    }
    draw(container);
  } catch (err) {
    showToast(err.message, "error");
    btn.disabled = false;
  }
}

function escHtml(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
