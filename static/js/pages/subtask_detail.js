// Subtask detail: section-scoped AJAX + realtime refresh (via parent task live updates).
(function () {
  var root = document.getElementById("subtaskDetailPage");
  if (!root) return;

  var SUBTASK_ID = Number(root.dataset.subtaskId || 0);
  var TASK_ID = Number(root.dataset.taskId || 0);
  if (!SUBTASK_ID) return;

  var VALID_SECTIONS = ["subtask", "comments", "attachments", "issues", "activities"];
  var pendingSections = new Set();
  var refreshTimer;

  function qs(sel, base) {
    return (base || document).querySelector(sel);
  }

  function escapeHtml(text) {
    var div = document.createElement("div");
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
    var map = { Completed: "success", "In Progress": "primary", Pending: "secondary" };
    var cls = map[status] || "secondary";
    return "badge rounded-pill bg-" + cls;
  }

  function activityMeta(action) {
    var a = (action || "").toLowerCase();
    if (a.indexOf("comment") !== -1) return { dot: "hr-dot-comment", icon: "bi-chat-dots" };
    if (a.indexOf("upload") !== -1) return { dot: "hr-dot-upload", icon: "bi-paperclip" };
    if (a.indexOf("completed") !== -1) return { dot: "hr-dot-complete", icon: "bi-check2-circle" };
    if (a.indexOf("issue") !== -1) return { dot: "hr-dot-issue", icon: "bi-bug" };
    if (a.indexOf("moved") !== -1) return { dot: "hr-dot-move", icon: "bi-arrow-left-right" };
    return { dot: "hr-dot-default", icon: "bi-clock-history" };
  }

  function normalizeSections(sections) {
    if (!sections || !sections.length) return VALID_SECTIONS.slice();
    return sections.filter(function (section) { return VALID_SECTIONS.indexOf(section) !== -1; });
  }

  function currentActivityPage() {
    var wrap = qs("#live-subtask-activities-wrap");
    return Number((wrap && wrap.dataset.activityPage) || 1) || 1;
  }

  function setButtonLoading(form, isLoading) {
    var btn = qs('button[type="submit"]', form) || qs("button", form);
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
    var titleEl = qs("#live-subtask-title");
    if (titleEl) titleEl.textContent = s.title || "";

    var st = qs("#live-subtask-status");
    if (st) {
      st.textContent = tr(s.status || "");
      st.className = badgeForStatus(s.status);
    }

    var prog = qs("#live-subtask-progress-label");
    if (prog) {
      prog.innerHTML =
        '<span class="pct">' + escapeHtml(String(s.progress ?? "")) + "</span>% " + escapeHtml(tr("complete"));
    }
    var progressInput = qs("#live-subtask-progress-input");
    if (progressInput) progressInput.value = s.progress;

    var statusSelect = qs("[data-subtask-status-select]");
    if (statusSelect && statusSelect.value !== s.status) statusSelect.value = s.status;

    var assigned = qs("#live-subtask-assigned");
    var names = s.assigned_name && Array.isArray(s.assigned_name) ? s.assigned_name.join(", ") : (s.assigned_name || "");
    if (assigned) assigned.textContent = names ? tr("Assigned") + ": " + names : "";
  }

  function renderComments(comments) {
    var comm = qs("#live-subtask-comments");
    if (!comm) return;
    if (!comments || !comments.length) {
      comm.innerHTML = '<p class="text-muted mb-0">' + tr("No comments yet.") + "</p>";
      return;
    }
    comm.innerHTML = comments
      .map(function (c) {
        return (
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
        );
      })
      .join("");
  }

  function renderIssues(issues) {
    var iss = qs("#live-subtask-issues");
    if (!iss) return;
    if (!issues || !issues.length) {
      iss.innerHTML = '<p class="text-muted mb-0">' + tr("No issues reported.") + "</p>";
      return;
    }
    iss.innerHTML = issues
      .map(function (i) {
        var badge =
          i.status === "Resolved"
            ? '<span class="badge text-bg-success">' + tr("Resolved") + "</span>"
            : '<span class="badge text-bg-danger">' + tr("Open") + "</span>";
        var desc = i.description
          ? '<div class="mt-2 text-muted">' + escapeHtml(i.description).replace(/\n/g, "<br>") + "</div>"
          : "";
        var resolveForm =
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
    var ulAtt = qs("#live-subtask-attachments");
    var emptyAtt = qs("#live-subtask-attachments-empty");
    if (!ulAtt || !emptyAtt) return;
    ulAtt.innerHTML = "";
    if (!attachments || !attachments.length) {
      emptyAtt.classList.remove("d-none");
      return;
    }
    emptyAtt.classList.add("d-none");
    attachments.forEach(function (a) {
      var li = document.createElement("li");
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
    var meta = activityMeta(a.action);
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
    var itemFn = function (page, text, disabled, active) {
      return (
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
        "</a></li>"
      );
    };

    var html =
      '<nav class="mt-3" id="live-subtask-activity-pagination"><ul class="pagination pagination-sm">';
    html += itemFn(payload.prev_num || 1, tr("Prev"), !payload.has_prev, false);
    for (var page = 1; page <= payload.pages; page += 1) {
      html += itemFn(page, page, false, page === payload.page);
    }
    html += itemFn(payload.next_num || payload.pages, tr("Next"), !payload.has_next, false);
    html += "</ul></nav>";
    return html;
  }

  function renderActivities(payload, opts) {
    var wrap = qs("#live-subtask-activities-wrap");
    if (!wrap || !payload) return;
    var options = opts || {};
    wrap.dataset.activityPage = String(payload.page || 1);
    var items = payload.items || [];
    if (!items.length) {
      wrap.innerHTML = '<p class="text-muted mb-0">' + tr("No activity recorded.") + "</p>";
      return;
    }
    wrap.innerHTML =
      '<ul class="hr-timeline" id="live-subtask-activities">' +
      items.map(function (a, index) { return activityItemHtml(a, options.highlightFirst && index === 0); }).join("") +
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
    var params = new URLSearchParams();
    params.set("sections", normalizeSections(sections).join(","));
    if (options && options.activityPage) params.set("activity_page", String(options.activityPage));
    return fetch("/api/subtask/" + SUBTASK_ID + "/live?" + params.toString(), { credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("Fetch failed");
        return r.json();
      })
      .then(function (payload) {
        renderPayload(payload, options);
        return payload;
      });
  }

  function scheduleRefresh(sections) {
    try {
      normalizeSections(sections).forEach(function (section) { pendingSections.add(section); });
      clearTimeout(refreshTimer);
      refreshTimer = setTimeout(function () {
        try {
          var list = Array.from(pendingSections);
          pendingSections.clear();
          fetchSections(list, { activityPage: currentActivityPage(), highlightFirst: list.indexOf("activities") !== -1 }).catch(
            function () {}
          );
        } catch (e) {
          console.warn("subtask_detail refresh timer error:", e);
        }
      }, 220);
    } catch (e) {
      console.warn("subtask_detail scheduleRefresh error:", e);
    }
  }

  function clearSuccessfulForm(form) {
    if (form.matches('[data-success-sections*="comments"]')) {
      var content = qs('textarea[name="content"]', form);
      if (content) content.value = "";
    }
    if (form.matches('[data-success-sections*="issues"]') && form.action.indexOf("/resolve") === -1) {
      form.reset();
    }
  }

  document.addEventListener("submit", function (e) {
    try {
      var form = e.target;
      if (!(form instanceof HTMLFormElement) || !form.matches("[data-ajax-form]")) return;

      e.preventDefault();
      setButtonLoading(form, true);

      fetch(form.action, {
        method: form.method || "POST",
        body: new FormData(form),
        headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      })
        .then(function (r) {
          return r.json().then(function (data) {
            if (!r.ok) throw data;
            return data;
          });
        })
        .then(function () {
          scheduleRefresh(["subtask", "comments", "issues", "attachments", "activities"]);
          clearSuccessfulForm(form);
          toast(form.dataset.successMessage || tr("Saved."));
        })
        .catch(function (err) {
          toast((err && (err.error || err.message)) || tr("Unable to save changes."), "danger");
          scheduleRefresh(["subtask", "comments", "issues", "attachments", "activities"]);
        })
        .finally(function () { setButtonLoading(form, false); });
    } catch (e) {
      console.warn("subtask_detail submit error:", e);
    }
  });

  var statusForm = qs("[data-subtask-status-form]");
  if (statusForm) {
    statusForm.addEventListener("submit", function (e) {
      try {
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
          .then(async function (r) {
            var contentType = r.headers.get("Content-Type") || "";
            
            if (contentType.indexOf("application/json") === -1) {
              var text = await r.text();
              console.error("Server returned HTML:", text);
              throw { error: "Server returned invalid response." };
            }

            var data = await r.json();
            if (!r.ok) throw data;
            return data;
          })
          .then(function () {
            scheduleRefresh(["subtask", "comments", "issues", "attachments", "activities"]);
            toast(tr("Status updated."));
          })
          .catch(function (err) {
            toast((err && (err.error || err.message)) || tr("Unable to update status."), "danger");
          })
          .finally(function () { setButtonLoading(statusForm, false); });
      } catch (e) {
        console.warn("subtask_detail status form error:", e);
      }
    });
  }

  document.addEventListener("click", function (e) {
    try {
      var link = e.target.closest("[data-activity-page-link]");
      if (!link || (link.closest(".disabled"))) return;
      e.preventDefault();
      var page = Number(link.dataset.activityPageLink || 1) || 1;
      fetchSections(["activities"], { activityPage: page }).catch(function () { toast(tr("Unable to load activity history."), "danger"); });
    } catch (e) {
      console.warn("subtask_detail pagination click error:", e);
    }
  });

  // Realtime: listen to parent task updates and refresh this subtask sections.
  if (window.HR_LIVE && window.HR_LIVE.socket && TASK_ID) {
    try {
      var socket = window.HR_LIVE.socket;
      function joinTaskRoom() {
        try {
          socket.emit("join_task", { task_id: TASK_ID });
        } catch (e) {
          console.warn("subtask socket connect error:", e);
        }
      }
      socket.on("connect", function () {
        joinTaskRoom();
      });
      if (socket.connected) joinTaskRoom();
      socket.on("task_live_update", function (msg) {
        try {
          if (msg && msg.task_id === TASK_ID) scheduleRefresh(["subtask", "comments", "issues", "attachments", "activities"]);
        } catch (e) {
          console.warn("subtask socket task_live_update error:", e);
        }
      });
      socket.on("task_removed", function (msg) {
        try {
          if (msg && msg.task_id === TASK_ID) window.location.href = "/tasks";
        } catch (e) {
          console.warn("subtask socket task_removed error:", e);
        }
      });
      window.addEventListener("beforeunload", function () {
        try {
          socket.emit("leave_task", { task_id: TASK_ID });
        } catch (_) {}
      });
    } catch (e) {
      console.warn("subtask_detail socket init error:", e);
    }
  }

  // Also react to global bus (dashboard/tasks/kanban use this).
  if (window.HR_LIVE) {
    window.HR_LIVE.onGlobalChange(function () { scheduleRefresh(["subtask", "comments", "issues", "attachments", "activities"]); });
  }
})();
