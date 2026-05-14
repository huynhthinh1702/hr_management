(function () {
  const COLLAPSED_KEY = "hr.sidebar.collapsed";
  const DESKTOP_QUERY = window.matchMedia("(min-width: 992px)");
  let transitionTimer = null;

  function getStoredCollapsed() {
    try {
      return localStorage.getItem(COLLAPSED_KEY) === "1";
    } catch (_) {
      return false;
    }
  }

  function storeCollapsed(value) {
    try {
      localStorage.setItem(COLLAPSED_KEY, value ? "1" : "0");
    } catch (_) {}
  }

  function setTransitioning(active) {
    document.documentElement.classList.toggle("sidebar-transitioning", Boolean(active));
    clearTimeout(transitionTimer);
    if (active) {
      transitionTimer = setTimeout(() => {
        document.documentElement.classList.remove("sidebar-transitioning");
      }, 320);
    }
  }

  function applyLayoutMode(mode, collapsed, withTransition) {
    const html = document.documentElement;
    if (withTransition) setTransitioning(true);

    html.dataset.layoutMode = mode;
    html.classList.toggle("layout-mobile", mode === "mobile");
    html.classList.toggle("layout-desktop", mode === "desktop");
    html.classList.toggle("sidebar-collapsed", mode === "desktop" && Boolean(collapsed));

    if (mode === "desktop") {
      storeCollapsed(Boolean(collapsed));
    }

    window.dispatchEvent(
      new CustomEvent("hr:layoutchange", {
        detail: { mode: mode, collapsed: mode === "desktop" && Boolean(collapsed) },
      })
    );
  }

  function syncLayout(withTransition) {
    const isDesktop = DESKTOP_QUERY.matches;
    applyLayoutMode(isDesktop ? "desktop" : "mobile", isDesktop ? getStoredCollapsed() : false, withTransition);
  }

  function normalizePath(p) {
    if (!p) return "/";
    const path = String(p).split("?")[0].split("#")[0];
    if (path.length > 1 && path.endsWith("/")) return path.slice(0, -1);
    return path;
  }

  function markActiveLinks() {
    const current = normalizePath(window.location.pathname);
    const navLinks = document.querySelectorAll(".app-nav-link[href]");
    navLinks.forEach((a) => {
      const href = normalizePath(a.getAttribute("href"));
      const active =
        href === current ||
        (href !== "/" && current.startsWith(href + "/")) ||
        (href === "/tasks" && (current === "/task" || current.startsWith("/task/")));
      a.classList.toggle("is-active", Boolean(active));
    });
  }

  syncLayout(false);
  requestAnimationFrame(() => {
    document.documentElement.classList.add("sidebar-ready");
  });

  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-sidebar-toggle]");
    if (!btn || btn.getAttribute("data-sidebar-toggle") !== "collapse") return;
    if (!DESKTOP_QUERY.matches) return;
    applyLayoutMode("desktop", !document.documentElement.classList.contains("sidebar-collapsed"), true);
  });

  if (typeof DESKTOP_QUERY.addEventListener === "function") {
    DESKTOP_QUERY.addEventListener("change", () => syncLayout(true));
  } else if (typeof DESKTOP_QUERY.addListener === "function") {
    DESKTOP_QUERY.addListener(() => syncLayout(true));
  }

  window.addEventListener("resize", () => syncLayout(false), { passive: true });
  markActiveLinks();
})();
