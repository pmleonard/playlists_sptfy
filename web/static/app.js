const tabModules = {
  songs: () => import("/static/tabs/songs.js"),
  update: () => import("/static/tabs/update.js"),
  import: () => import("/static/tabs/import.js"),
  export: () => import("/static/tabs/export.js"),
  genres: () => import("/static/tabs/genre_review.js"),
  tags: () => import("/static/tabs/tag_review.js"),
  albums: () => import("/static/tabs/album_review.js"),
  grouped_songs: () => import("/static/tabs/grouped_songs.js"),
  ignore_duplicates: () => import("/static/tabs/ignore_duplicates.js"),
  possible_duplicates: () => import("/static/tabs/possible_duplicates.js"),
  config: () => import("/static/tabs/config.js"),
  settings: () => import("/static/tabs/settings.js"),
};

export async function api(method, path, body) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

export function showToast(message, type = "success") {
  const container = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

export function showConfirm(message) {
  return Promise.resolve(window.confirm(message));
}

async function activateTab(name) {
  const content = document.getElementById("content");
  content.innerHTML = `<p class="loading">Loading…</p>`;

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === name);
  });

  try {
    const mod = await tabModules[name]();
    await mod.render(content);
  } catch (err) {
    content.innerHTML = `<p class="error-msg">Failed to load tab: ${err.message}</p>`;
  }
}

document.getElementById("tabs").addEventListener("click", (e) => {
  const btn = e.target.closest(".tab-btn");
  if (btn) activateTab(btn.dataset.tab);
});

activateTab("songs");
