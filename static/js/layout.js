// Layout: sidebar collapse (desktop) + active link highlighting
(function () {
  const SIDEBAR_ID = "appSidebar";
  const COLLAPSED_KEY = "hr.sidebar.collapsed";
  let isTransitioning = false;

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function applyCollapsed(isCollapsed) {
    if (isTransitioning) return;
    isTransitioning = true;

    const html = document.documentElement;
    // Add transition lock class to prevent reflow jank
    html.classList.add("sidebar-transitioning");
    html.classList.toggle("sidebar-collapsed", Boolean(isCollapsed));
    
    try {
      localStorage.setItem(COLLAPSED_KEY, isCollapsed ? "1" : "0");
    } catch (_) {}

    // Remove lock after transition completes
    setTimeout(() => {
      html.classList.remove("sidebar-transitioning");
      isTransitioning = false;
    }, 350);
  }

  function getCollapsed() {
    try {
      return localStorage.getItem(COLLAPSED_KEY) === "1";
    } catch (_) {
      return false;
    }
  }

  // On first load, enable transitions after a short delay to prevent flash animation
  setTimeout(() => {
    document.documentElement.classList.add("sidebar-ready");
  }, 50);

  // The collapsed class is already applied inline in base.html <head>,
  // so we don't need to do it again here.

  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-sidebar-toggle]");
    if (!btn) return;
    const mode = btn.getAttribute("data-sidebar-toggle");
    if (mode !== "collapse") return;
    applyCollapsed(!document.documentElement.classList.contains("sidebar-collapsed"));
  });

  // Active link styling
  function normalizePath(p) {
    if (!p) return "/";
    // Remove query/hash, trailing slash (except root)
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

  markActiveLinks();
})();

