// Bootstrap modal confirm + form loading spinner
(function () {
  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  // CSRF token (for fetch/drag&drop updates)
  window.HR_CSRF =
    qs('meta[name="csrf-token"]')?.getAttribute("content") || window.HR_CSRF || "";

  // -------- Confirm modal --------
  const modalEl = qs("#hrConfirmModal");
  let modal;
  let pendingAction = null;

  function ensureModal() {
    if (!modalEl || !window.bootstrap) return null;
    if (!modal) modal = new bootstrap.Modal(modalEl);
    return modal;
  }

  function openConfirm({ title, message, okText, variant }, onOk) {
    const m = ensureModal();
    if (!m) return false;

    qs("[data-hr-confirm-title]", modalEl).textContent = title || "Confirm";
    qs("[data-hr-confirm-message]", modalEl).textContent = message || "Are you sure?";
    const okBtn = qs("[data-hr-confirm-ok]", modalEl);
    okBtn.textContent = okText || "Yes, continue";
    okBtn.className = "btn " + (variant || "btn-danger");

    pendingAction = onOk;
    m.show();
    return true;
  }

  if (modalEl) {
    modalEl.addEventListener("hidden.bs.modal", () => {
      pendingAction = null;
    });
    const ok = qs("[data-hr-confirm-ok]", modalEl);
    if (ok) {
      ok.addEventListener("click", () => {
        const fn = pendingAction;
        pendingAction = null;
        if (fn) fn();
        const m = ensureModal();
        if (m) m.hide();
      });
    }
  }

  document.addEventListener("click", (e) => {
    const a = e.target.closest("a[data-confirm]");
    if (!a) return;

    e.preventDefault();
    const msg = a.getAttribute("data-confirm") || "Are you sure?";
    const okText = a.getAttribute("data-confirm-ok") || "Delete";
    const variant = a.getAttribute("data-confirm-variant") || "btn-danger";
    const title = a.getAttribute("data-confirm-title") || "Confirm action";

    const didOpen = openConfirm({ title, message: msg, okText, variant }, () => {
      window.location.href = a.href;
    });

    // Fallback if bootstrap missing
    if (!didOpen) {
      // eslint-disable-next-line no-alert
      if (confirm(msg)) window.location.href = a.href;
    }
  });

  document.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-confirm][data-confirm-submit]");
    if (!btn) return;
    const form = btn.closest("form");
    if (!form) return;

    e.preventDefault();
    const msg = btn.getAttribute("data-confirm") || "Are you sure?";
    const okText = btn.getAttribute("data-confirm-ok") || "Continue";
    const variant = btn.getAttribute("data-confirm-variant") || "btn-danger";
    const title = btn.getAttribute("data-confirm-title") || "Confirm action";

    const didOpen = openConfirm({ title, message: msg, okText, variant }, () => {
      form.submit();
    });

    if (!didOpen) {
      // eslint-disable-next-line no-alert
      if (confirm(msg)) form.submit();
    }
  });

  // -------- Loading spinner on submit --------
  document.addEventListener("submit", (e) => {
    const form = e.target;
    if (!(form instanceof HTMLFormElement)) return;

    const btn =
      qs('button[type="submit"]', form) || qs('input[type="submit"]', form);
    if (!btn) return;

    btn.setAttribute("disabled", "disabled");
    const original = btn.innerHTML;
    btn.setAttribute("data-hr-original-html", original);
    btn.innerHTML =
      '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>' +
      "<span>Loading...</span>";
  });

  // -------- Toast notifications --------
  function toast(message, opts) {
    const container = qs("#hrToastContainer");
    if (!container || !window.bootstrap) return;
    const o = opts || {};
    const title = o.title || "Notification";
    const variant = o.variant || "primary"; // primary|success|warning|danger|info|secondary
    const delay = typeof o.delay === "number" ? o.delay : 2600;

    const el = document.createElement("div");
    el.className = "toast align-items-center text-bg-" + variant + " border-0";
    el.setAttribute("role", "status");
    el.setAttribute("aria-live", "polite");
    el.setAttribute("aria-atomic", "true");
    el.innerHTML =
      '<div class="d-flex">' +
      '<div class="toast-body">' +
      '<div class="fw-semibold mb-1">' +
      title +
      "</div>" +
      "<div>" +
      (message == null ? "" : String(message)) +
      "</div>" +
      "</div>" +
      '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>' +
      "</div>";

    container.appendChild(el);
    const t = new bootstrap.Toast(el, { delay });
    el.addEventListener("hidden.bs.toast", () => el.remove());
    t.show();
  }

  window.HR_UI = window.HR_UI || {};
  window.HR_UI.toast = toast;
})();

