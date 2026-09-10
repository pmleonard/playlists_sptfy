export const PAGE_SIZE_OPTIONS = [25, 50, 100, 200, "all"];
export const DEFAULT_PAGE_SIZE = 50;

const STORAGE_PREFIX = "pw-page-size:";

export function getPageSize(tabKey) {
  try {
    const raw = window.localStorage.getItem(STORAGE_PREFIX + tabKey);
    if (raw === null) return DEFAULT_PAGE_SIZE;
    if (raw === "all") return "all";
    const n = parseInt(raw, 10);
    return PAGE_SIZE_OPTIONS.includes(n) ? n : DEFAULT_PAGE_SIZE;
  } catch (_) {
    return DEFAULT_PAGE_SIZE;
  }
}

export function setPageSize(tabKey, size) {
  try {
    window.localStorage.setItem(STORAGE_PREFIX + tabKey, String(size));
  } catch (_) {
    /* localStorage unavailable — page size just won't persist */
  }
}

/**
 * Slices `items` for the given page/pageSize. Clamps `page` into range and
 * returns the clamped value so callers can store it back into their state.
 */
export function paginate(items, page, pageSize) {
  if (pageSize === "all") {
    return { slice: items, totalPages: 1, page: 1 };
  }
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  const clampedPage = Math.min(Math.max(1, page), totalPages);
  const start = (clampedPage - 1) * pageSize;
  return { slice: items.slice(start, start + pageSize), totalPages, page: clampedPage };
}

/**
 * Renders the pagination control bar markup. `state` is `{page, pageSize}`;
 * `total` is the count of items being paginated over (post filter/sort).
 */
export function paginationBarHtml(state, total) {
  const { totalPages, page } = paginate(new Array(total), state.page, state.pageSize);
  const options = PAGE_SIZE_OPTIONS.map(
    (n) =>
      `<option value="${n}" ${state.pageSize === n ? "selected" : ""}>${n === "all" ? "All" : n}</option>`
  ).join("");

  return `
    <div class="pagination-bar">
      <label class="flex-row" style="gap:6px">
        Rows per page:
        <select class="page-size-select">${options}</select>
      </label>
      <button class="btn btn-secondary btn-sm page-prev-btn" ${page <= 1 ? "disabled" : ""}>◀ Prev</button>
      <span>Page ${page} of ${totalPages}</span>
      <button class="btn btn-secondary btn-sm page-next-btn" ${page >= totalPages ? "disabled" : ""}>Next ▶</button>
    </div>`;
}

/**
 * Wires the pagination bar's controls. `bar` is the element containing the
 * markup from `paginationBarHtml`. `state` is mutated in place; `onChange`
 * is called after any state change so the caller can re-render.
 */
export function bindPaginationBar(bar, tabKey, state, onChange) {
  const select = bar.querySelector(".page-size-select");
  const prevBtn = bar.querySelector(".page-prev-btn");
  const nextBtn = bar.querySelector(".page-next-btn");

  select.addEventListener("change", () => {
    const val = select.value === "all" ? "all" : parseInt(select.value, 10);
    state.pageSize = val;
    state.page = 1;
    setPageSize(tabKey, val);
    onChange();
  });

  prevBtn.addEventListener("click", () => {
    state.page = Math.max(1, state.page - 1);
    onChange();
  });

  nextBtn.addEventListener("click", () => {
    state.page = state.page + 1;
    onChange();
  });
}
