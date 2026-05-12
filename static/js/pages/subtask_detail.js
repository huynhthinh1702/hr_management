// Subtask detail: section-scoped AJAX + realtime refresh (via parent task live updates).
(function () {
  const root = document.getElementById("subtaskDetailPage");
  if (!root) return;

  const SUBTASK_ID = Number(root.dataset.subtaskId || 0);
  const TASK_ID = Number(root.dataset.taskId || 0);
  if (!SUBTASK_ID) return;

  const VALID_SECTIONS = ["subtask", "comments", "attachments", "issues", "activities"];
  const pendingSections = new Set();
  let refreshTimer;

  function qs(sel, base) {
    return (base || document).querySelector(sel);
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
  }

  function tr(text) {
    return window.HR_UI && window.HR_UI.t ? window.HR_UI.t(text) : text;
  }

  function toast(message, variant) {
    if (window.HR_UI && typeof window.HR_UI.toast === "function") {
      window.HR_UI.toast(tr(message), { title: tr("Subtask Detail"), variant: variant || "success" });
    }
  }

  function badgeForStatus(status) {
    const map = { Completed: "success", "In Progress": "primary", Pending: "secondary" };
    const cls = map[status] || "secondary";
    return "badge rounded-pill bg-" + cls;
  }

  function activityMeta(action) {
    const a = (action || "").toLowerCase();
    if (a.includes("comment")) return { dot: "hr-dot-comment", icon: "bi-chat-dots" };
    if (a.includes("upload")) return { dot: "hr-dot-upload", icon: "bi-paperclip" };
    if (a.includes("completed")) return { dot: "hr-dot-complete", icon: "bi-check2-circle" };
    if (a.includes("issue")) return { dot: "hr-dot-issue", icon: "bi-bug" };
    if (a.includes("moved")) return { dot: "hr-dot-move", icon: "bi-arrow-left-right" };
    return { dot: "hr-dot-default", icon: "bi-clock-history" };
  }

  function normalizeSections(sections) {
    if (!sections || !sections.length) return VALID_SECTIONS.slice();
    return sections.filter((section) => VALID_SECTIONS.includes(section));
  }

  function currentActivityPage() {
    const wrap = qs("#live-subtask-activities-wrap");
    return Number((wrap && wrap.dataset.activityPage) || 1) || 1;
  }

  function setButtonLoading(form, isLoading) {
    const btn = qs('button[type="submit"]', form) || qs("button", form);
    if (!btn) return;

    if (isLoading) {
      btn.disabled = true;
      if (!btn.dataset.hrOriginalHtml) btn.dataset.hrOriginalHtml = btn.innerHTML;
      btn.innerHTML =
        '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>' +
        "<span>" +
        tr("Loading...") +
        "</span>";
    } else {
      btn.disabled = false;
      if (btn.dataset.hrOriginalHtml) {
        btn.innerHTML = btn.dataset.hrOriginalHtml;
        delete btn.dataset.hrOriginalHtml;
      }
    }
  }

  function renderSubtask(s) {
    if (!s) return;
    const titleEl = qs("#live-subtask-title");
    if (titleEl) titleEl.textContent = s.title || "";

    const st = qs("#live-subtask-status");
    if (st) {
      st.textContent = tr(s.status || "");
      st.className = badgeForStatus(s.status);
    }

    const prog = qs("#live-subtask-progress-label");
    if (prog) {
      prog.innerHTML =
        '<span class="pct">' + escapeHtml(String(s.progress ?? "")) + "</span>% " + escapeHtml(tr("complete"));
    }
    const progressInput = qs("#live-subtask-progress-input");
    if (progressInput) progressInput.value = s.progress;

    const statusSelect = qs("[data-subtask-status-select]");
    if (statusSelect && statusSelect.value !== s.status) statusSelect.value = s.status;

    const assigned = qs("#live-subtask-assigned");
    if (assigned) assigned.textContent = s.assigned_name ? tr("Assigned") + ": " + s.assigned_name : "";
  }

  function renderComments(comments) {
    const comm = qs("#live-subtask-comments");
    if (!comm || !comments) return;
    if (!comments.length) {
      comm.innerHTML = '<p class="text-muted mb-0">' + tr("No comments yet.") + "</p>";
      return;
    }
    comm.innerHTML = comments
      .map(
        (c) =>
          '<div class="border rounded-3 p-3 mb-2 bg-light">' +
          '<div class="d-flex justify-content-between gap-3">' +
          "<strong>" +
          escapeHtml(c.author_name) +
          "</strong>" +
          '<small class="text-muted text-nowrap">' +
          escapeHtml(c.created_at || "") +
          "</small>" +
          "</div>" +
          '<div class="mt-2">' +
          escapeHtml(c.content || "").replace(/\n/g, "<br>") +
          "</div>" +
          "</div>"
      )
      .join("");
  }

  function renderIssues(issues) {
    const iss = qs("#live-subtask-issues");
    if (!iss || !issues) return;
    if (!issues.length) {
      iss.innerHTML = '<p class="text-muted mb-0">' + tr("No issues reported.") + "</p>";
      return;
    }
    iss.innerHTML = issues
      .map((i) => {
        const badge =
          i.status === "Resolved"
            ? '<span class="badge text-bg-success">' + tr("Resolved") + "</span>"
            : '<span class="badge text-bg-danger">' + tr("Open") + "</span>";
        const desc = i.description
          ? '<div class="mt-2 text-muted">' + escapeHtml(i.description).replace(/\n/g, "<br>") + "</div>"
          : "";
        const resolveForm =
          i.status !== "Resolved"
            ? '<form method="POST" action="/issues/' +
              i.id +
              '/resolve" class="mt-2" data-ajax-form data-success-sections="issues,activities" data-success-message="' +
              escapeHtml(tr("Issue resolved.")) +
              '">' +
              '<input type="hidden" name="csrf_token" value="' +
              escapeHtml(window.HR_CSRF || "") +
              '">' +
              '<button class="btn btn-outline-success btn-sm">' +
              tr("Mark as Resolved") +
              "</button></form>"
            : "";
        return (
          '<div class="border rounded-3 p-3 mb-2 bg-white">' +
          '<div class="d-flex justify-content-between align-items-start gap-3">' +
          '<div class="min-w-0">' +
          '<div class="fw-semibold text-truncate">' +
          escapeHtml(i.title) +
          "</div>" +
          '<small class="text-muted">' +
          tr("by") +
          " " +
          escapeHtml(i.creator_name || "") +
          " - " +
          escapeHtml(i.created_at || "") +
          " - " +
          escapeHtml(tr(i.severity || "Normal")) +
          "</small>" +
          "</div>" +
          badge +
          "</div>" +
          desc +
          resolveForm +
          "</div>"
        );
      })
      .join("");
  }

  function renderAttachments(attachments) {
    const ulAtt = qs("#live-subtask-attachments");
    const emptyAtt = qs("#live-subtask-attachments-empty");
    if (!ulAtt || !emptyAtt || !attachments) return;
    ulAtt.innerHTML = "";
    if (!attachments.length) {
      emptyAtt.classList.remove("d-none");
      return;
    }
    emptyAtt.classList.add("d-none");
    attachments.forEach((a) => {
      const li = document.createElement("li");
      li.className = "list-group-item d-flex justify-content-between align-items-center px-0";
      li.innerHTML =
        '<div class="min-w-0">' +
        '<div class="fw-semibold text-truncate">' +
        escapeHtml(a.original_filename) +
        "</div>" +
        '<small class="text-muted">' +
        tr("by") +
        " " +
        escapeHtml(a.uploader_name || "") +
        "</small></div>" +
        '<a href="/uploads/' +
        escapeHtml(a.file_path || "") +
        '" class="btn btn-outline-secondary btn-sm">' +
        tr("Download") +
        "</a>";
      ulAtt.appendChild(li);
    });
  }

  function activityItemHtml(a, isNew) {
    const meta = activityMeta(a.action);
    return (
      '<li class="hr-timeline-item' +
      (isNew ? " hr-timeline-item-new" : "") +
      '">' +
      '<div class="hr-timeline-dot ' +
      meta.dot +
      '"><i class="bi ' +
      meta.icon +
      '"></i></div>' +
      '<div class="hr-timeline-body">' +
      '<div class="d-flex justify-content-between align-items-start gap-3">' +
      '<div class="fw-semibold">' +
      escapeHtml(a.action || "") +
      "</div>" +
      '<small class="text-muted text-nowrap">' +
      escapeHtml(a.created_at || "") +
      "</small>" +
      "</div>" +
      '<div class="text-muted">' +
      escapeHtml(a.details || "").replace(/\n/g, "<br>") +
      "</div>" +
      '<div class="small text-muted mt-1">' +
      tr("by") +
      " " +
      escapeHtml(a.actor_name || "") +
      "</div>" +
      "</div>" +
      "</li>"
    );
  }

  function renderActivityPagination(payload) {
    if (!payload || payload.pages <= 1) return "";
    const item = (page, text, disabled, active) =>
      '<li class="page-item ' +
      (disabled ? "disabled " : "") +
      (active ? "active" : "") +
      '">' +
      '<a class="page-link" href="/subtask/' +
      SUBTASK_ID +
      "?activity_page=" +
      page +
      '" data-activity-page-link="' +
      page +
      '">' +
      text +
      "</a></li>";

    let html =
      '<nav class="mt-3" id="live-subtask-activity-pagination"><ul class="pagination pagination-sm">';
    html += item(payload.prev_num || 1, tr("Prev"), !payload.has_prev, false);
    for (let page = 1; page <= payload.pages; page += 1) {
      html += item(page, page, false, page === payload.page);
    }
    html += item(payload.next_num || payload.pages, tr("Next"), !payload.has_next, false);
    html += "</ul></nav>";
    return html;
  }

  function renderActivities(payload, opts) {
    const wrap = qs("#live-subtask-activities-wrap");
    if (!wrap || !payload) return;
    const options = opts || {};
    wrap.dataset.activityPage = String(payload.page || 1);
    const items = payload.items || [];
    if (!items.length) {
      wrap.innerHTML = '<p class="text-muted mb-0">' + tr("No activity recorded.") + "</p>";
      return;
    }
    wrap.innerHTML =
      '<ul class="hr-timeline" id="live-subtask-activities">' +
      items.map((a, index) => activityItemHtml(a, options.highlightFirst && index === 0)).join("") +
      "</ul>" +
      renderActivityPagination(payload);
  }

  function renderPayload(data, opts) {
    if (!data) return;
    if (data.subtask) renderSubtask(data.subtask);
    if (data.comments) renderComments(data.comments);
    if (data.issues) renderIssues(data.issues);
    if (data.attachments) renderAttachments(data.attachments);
    if (data.activities) renderActivities(data.activities, opts);
  }

  function fetchSections(sections, options) {
    const params = new URLSearchParams();
    params.set("sections", normalizeSections(sections).join(","));
    if (options && options.activityPage) params.set("activity_page", String(options.activityPage));
    return fetch("/api/subtask/" + SUBTASK_ID + "/live?" + params.toString(), { credentials: "same-origin" })
      .then((r) => {
        if (!r.ok) throw new Error("Fetch failed");
        return r.json();
      })
      .then((payload) => {
        renderPayload(payload, options);
        return payload;
      });
  }

  function scheduleRefresh(sections) {
    normalizeSections(sections).forEach((section) => pendingSections.add(section));
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(() => {
      const list = Array.from(pendingSections);
      pendingSections.clear();
      fetchSections(list, { activityPage: currentActivityPage(), highlightFirst: list.includes("activities") }).catch(
        () => {}
      );
    }, 220);
  }

  function clearSuccessfulForm(form) {
    if (form.matches('[data-success-sections*="comments"]')) {
      const content = qs('textarea[name="content"]', form);
      if (content) content.value = "";
    }
    if (form.matches('[data-success-sections*="issues"]') && !form.action.includes("/resolve")) {
      form.reset();
    }
  }

  document.addEventListener("submit", (e) => {
    const form = e.target;
    if (!(form instanceof HTMLFormElement) || !form.matches("[data-ajax-form]")) return;

    e.preventDefault();
    setButtonLoading(form, true);

    fetch(form.action, {
      method: form.method || "POST",
      body: new FormData(form),
      headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    })
      .then((r) =>
        r.json().then((data) => {
          if (!r.ok) throw data;
          return data;
        })
      )
      .then(() => {
        scheduleRefresh(["subtask", "comments", "issues", "attachments", "activities"]);
        clearSuccessfulForm(form);
        toast(form.dataset.successMessage || tr("Saved."));
      })
      .catch((err) => {
        toast((err && (err.error || err.message)) || tr("Unable to save changes."), "danger");
        scheduleRefresh(["subtask", "comments", "issues", "attachments", "activities"]);
      })
      .finally(() => setButtonLoading(form, false));
  });

  const statusForm = qs("[data-subtask-status-form]");
  if (statusForm) {
    statusForm.addEventListener("submit", (e) => {
      // Keep default POST route working, but prefer AJAX.
      e.preventDefault();
      e.stopPropagation();
      setButtonLoading(statusForm, true);
      fetch(statusForm.action, {
        method: statusForm.method || "POST",
        body: new FormData(statusForm),
        headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      })
        .then(async (r) => {
         const contentType =
            r.headers.get("Content-Type") || "";
          if (contentType.includes("application/json")) {
            const text = await r.text();
            console.error("Server returned HTML:", text);
            throw { error:"Server returned invalid response." };
          }

          const data = await r.json();
          if (!r.ok) throw data;
          return data;
        })

  document.addEventListener("click", (e) => {
    const link = e.target.closest("[data-activity-page-link]");
    if (!link || link.closest(".disabled")) return;
    e.preventDefault();
    const page = Number(link.dataset.activityPageLink || 1) || 1;
    fetchSections(["activities"], { activityPage: page }).catch(() => toast(tr("Unable to load activity history."), "danger"));
  });

  // Realtime: listen to parent task updates and refresh this subtask sections.
  if (window.io && TASK_ID) {
    const socket = io({ transports: ["websocket", "polling"] });
    socket.on("connect", () => socket.emit("join_task", { task_id: TASK_ID }));
    socket.on("task_live_update", (msg) => {
      if (msg && msg.task_id === TASK_ID) scheduleRefresh(["subtask", "comments", "issues", "attachments", "activities"]);
    });
    socket.on("task_removed", (msg) => {
      if (msg && msg.task_id === TASK_ID) window.location.href = "/tasks";
    });
    window.addEventListener("beforeunload", () => {
      try {
        socket.emit("leave_task", { task_id: TASK_ID });
      } catch (_) {}
    });
  }

  // Also react to global bus (dashboard/tasks/kanban use this).
  if (window.HR_LIVE) {
    window.HR_LIVE.onGlobalChange(() => scheduleRefresh(["subtask", "comments", "issues", "attachments", "activities"]));
  }
})();

