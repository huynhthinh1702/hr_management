// Task detail: section-scoped AJAX + per-task realtime updates.
(function () {
  var root = document.getElementById("taskDetailPage");
  if (!root) return;

  var TASK_ID = Number(root.dataset.taskId || 0);
  if (!TASK_ID) return;

  var VALID_SECTIONS = ["task", "subtasks", "comments", "attachments", "issues", "activities"];
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
      window.HR_UI.toast(tr(message), { title: tr("Task Detail"), variant: variant || "success" });
    }
  }

  function badgeForStatus(status) {
    var map = { Completed: "success", "In Progress": "primary", Pending: "secondary" };
    var cls = map[status] || "secondary";
    return "badge rounded-pill bg-" + cls;
  }

  function activityMeta(action) {
    var a = (action || "").toLowerCase();
    if (a.includes("comment")) return { dot: "hr-dot-comment", icon: "bi-chat-dots" };
    if (a.includes("upload")) return { dot: "hr-dot-upload", icon: "bi-paperclip" };
    if (a.includes("completed")) return { dot: "hr-dot-complete", icon: "bi-check2-circle" };
    if (a.includes("issue")) return { dot: "hr-dot-issue", icon: "bi-bug" };
    if (a.includes("moved")) return { dot: "hr-dot-move", icon: "bi-arrow-left-right" };
    return { dot: "hr-dot-default", icon: "bi-clock-history" };
  }

  function normalizeSections(sections) {
    if (!sections || !sections.length) return VALID_SECTIONS.slice();
    return sections.filter(function (section) { return VALID_SECTIONS.indexOf(section) !== -1; });
  }

  function currentActivityPage() {
    var wrap = qs("#live-activities-wrap");
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

  function renderTask(t) {
    if (!t) return;
    var titleEl = qs("#live-task-title");
    if (titleEl) titleEl.textContent = t.title;

    var descEl = qs("#live-task-description");
    if (descEl) descEl.textContent = t.description;

    var st = qs("#live-task-status");
    if (st) {
      st.textContent = tr(t.status);
      st.className = badgeForStatus(t.status);
    }

    var progLabel = qs("#live-task-progress-label");
    if (progLabel) {
      progLabel.innerHTML =
        '<span class="pct">' +
        escapeHtml(String(t.progress ?? "")) +
        "</span>% " +
        escapeHtml(tr("complete"));
    }
    var progressInput = qs("#live-task-progress-input");
    if (progressInput) progressInput.value = t.progress;

    var pr = qs("#live-task-priority");
    if (pr) {
      if (t.priority) {
        pr.textContent = t.priority === "High" ? tr("High priority") : t.priority === "Medium" ? tr("Medium priority") : tr("Low priority");
      } else {
        pr.textContent = "";
      }
    }

    var statusSelect = qs("[data-task-status-select]");
    if (statusSelect && statusSelect.value !== t.status) statusSelect.value = t.status;
  }

  function renderSubtasks(subtasks) {
    var subBody = qs("#live-subtasks-tbody");
    if (!subBody) return;
    subBody.innerHTML = "";
    if (!subtasks || !subtasks.length) {
      subBody.innerHTML = '<tr><td colspan="6" class="text-muted">' + tr("No subtasks yet.") + "</td></tr>";
      return;
    }

    subtasks.forEach(function (s) {
      var row = document.createElement("tr");
      var assignedName = (s.assigned_names && s.assigned_names.join(", ")) || "";
      row.innerHTML =
        "<td>" +
        s.id +
        "</td>" +
        "<td>" +
        '<a href="/subtask/' + s.id + '" class="text-decoration-none">' + escapeHtml(s.title) + '</a>' +
        '<span class="badge bg-info ms-2">Subtask</span>' +
        "</td>" +
        "<td>" +
        escapeHtml(tr(s.status)) +
        "</td>" +
        "<td>" +
        s.progress +
        "%</td>" +
        "<td>" +
        escapeHtml(assignedName) +
        "</td>" +
        "<td>" +
        '<a href="/subtask/' +
        s.id +
        '" class="btn btn-primary btn-sm">' +
        tr("View") +
        "</a> " +
        '<a href="/update-subtask/' +
        s.id +
        '" class="btn btn-warning btn-sm">' +
        tr("Update") +
        "</a> " +
        '<form method="POST" action="/delete-subtask/' +
        s.id +
        '" class="d-inline">' +
        '<input type="hidden" name="csrf_token" value="' +
        escapeHtml(window.HR_CSRF || "") +
        '">' +
        '<button type="button" class="btn btn-danger btn-sm" data-confirm="' +
        escapeHtml(tr("Delete this subtask?")) +
        '" data-confirm-ok="' +
        escapeHtml(tr("Delete")) +
        '" data-confirm-submit="1">' +
        tr("Delete") +
        "</button>" +
        "</form>" +
        "</td>";
      subBody.appendChild(row);
    });
  }

  function renderComments(comments) {
    var comm = qs("#live-comments");
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
          escapeHtml(c.created_at) +
          "</small>" +
          "</div>" +
          '<div class="mt-2">' +
          escapeHtml(c.content).replace(/\n/g, "<br>") +
          "</div>" +
          "</div>"
        );
      })
      .join("");
  }

  function renderIssues(issues) {
    var iss = qs("#live-issues");
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
          escapeHtml(i.creator_name) +
          " - " +
          escapeHtml(i.created_at) +
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
    var ulAtt = qs("#live-attachments");
    var emptyAtt = qs("#live-attachments-empty");
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
        '<small class="text-muted">by ' +
        escapeHtml(a.uploader_name) +
        "</small></div>" +
        '<a href="/uploads/' +
        escapeHtml(a.file_path) +
        '" class="btn btn-outline-secondary btn-sm">' + tr("Download") + "</a>";
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
      escapeHtml(a.action) +
      "</div>" +
      '<small class="text-muted text-nowrap">' +
      escapeHtml(a.created_at) +
      "</small>" +
      "</div>" +
      '<div class="text-muted">' +
      escapeHtml(a.details).replace(/\n/g, "<br>") +
      "</div>" +
      '<div class="small text-muted mt-1">' +
      tr("by") +
      " " +
      escapeHtml(a.actor_name) +
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
        '<a class="page-link" href="/task/' +
        TASK_ID +
        "?activity_page=" +
        page +
        '" data-activity-page-link="' +
        page +
        '">' +
        text +
        "</a></li>"
      );
    };
    var html = '<nav class="mt-3" id="live-activity-pagination"><ul class="pagination pagination-sm">';
    html += itemFn(payload.prev_num || 1, tr("Prev"), !payload.has_prev, false);
    for (var page = 1; page <= payload.pages; page += 1) {
      html += itemFn(page, page, false, page === payload.page);
    }
    html += itemFn(payload.next_num || payload.pages, tr("Next"), !payload.has_next, false);
    html += "</ul></nav>";
    return html;
  }

  function renderActivities(payload, opts) {
    var wrap = qs("#live-activities-wrap");
    if (!wrap || !payload) return;

    var options = opts || {};
    wrap.dataset.activityPage = String(payload.page || 1);

    var items = payload.items || [];
    if (!items.length) {
      wrap.innerHTML =
        '<p class="text-muted mb-0" id="live-activities-empty">' + tr("No activity recorded.") + "</p>";
      return;
    }

    wrap.innerHTML =
      '<ul class="hr-timeline" id="live-activities">' +
      items.map(function (a, index) { return activityItemHtml(a, options.highlightFirst && index === 0); }).join("") +
      "</ul>" +
      renderActivityPagination(payload);
  }

  function renderPayload(data, opts) {
    if (!data) return;
    if (data.task) renderTask(data.task);
    if (data.subtasks) renderSubtasks(data.subtasks);
    if (data.comments) renderComments(data.comments);
    if (data.issues) renderIssues(data.issues);
    if (data.attachments) renderAttachments(data.attachments);
    if (data.activities) renderActivities(data.activities, opts);
  }

  function fetchSections(sections, options) {
    var params = new URLSearchParams();
    params.set("sections", normalizeSections(sections).join(","));
    if (options && options.activityPage) params.set("activity_page", String(options.activityPage));

    return fetch("/api/task/" + TASK_ID + "/live?" + params.toString(), { credentials: "same-origin" })
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

          if (list.indexOf("activities") !== -1 && currentActivityPage() !== 1) {
            var note = qs("#live-activity-new-note");
            if (note) note.classList.remove("d-none");
            var otherSections = list.filter(function (section) { return section !== "activities"; });
            if (!otherSections.length) return;
            fetchSections(otherSections).catch(function () {});
            return;
          }

          fetchSections(list, { activityPage: currentActivityPage(), highlightFirst: list.indexOf("activities") !== -1 }).catch(
            function () {}
          );
        } catch (e) {
          console.warn("task_detail refresh timer error:", e);
        }
      }, 220);
    } catch (e) {
      console.warn("task_detail scheduleRefresh error:", e);
    }
  }

  function clearSuccessfulForm(form) {
    if (form.matches('[data-success-sections*="comments"]')) {
      var content = qs('textarea[name="content"]', form);
      if (content) content.value = "";
    }
    if (form.matches('[data-success-sections*="issues"]') && form.action.indexOf("/issues") !== -1 && form.action.indexOf("/resolve") === -1) {
      form.reset();
    }
  }

  document.addEventListener("submit", function (e) {
    try {
      var form = e.target;
      if (!(form instanceof HTMLFormElement) || !form.matches("[data-ajax-form]")) return;

      e.preventDefault();
      setButtonLoading(form, true);

      var sections = (form.dataset.successSections || "").split(",").map(function (s) { return s.trim(); }).filter(Boolean);
      fetch(form.action, {
        method: form.method || "POST",
        body: new FormData(form),
        headers: {
          Accept: "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
        credentials: "same-origin",
      })
        .then(function (r) {
          return r.json().then(function (data) {
            if (!r.ok) throw data;
            return data;
          });
        })
        .then(function (data) {
          renderPayload(data.payload || {}, { activityPage: 1, highlightFirst: true });
          clearSuccessfulForm(form);
          var note = qs("#live-activity-new-note");
          if (note) note.classList.add("d-none");
          toast(data.message || form.dataset.successMessage || tr("Saved."));
        })
        .catch(function (err) {
          toast((err && (err.error || err.message)) || tr("Unable to save changes."), "danger");
          if (sections.length) scheduleRefresh(sections);
        })
        .finally(function () { setButtonLoading(form, false); });
    } catch (e) {
      console.warn("task_detail submit error:", e);
    }
  });

  var statusForm = qs("[data-task-status-form]");
  if (statusForm) {
    statusForm.addEventListener("submit", function (e) {
      try {
        e.preventDefault();
        e.stopPropagation();
        var statusSelect = qs("[data-task-status-select]", statusForm);
        var status = statusSelect ? statusSelect.value : "";
        setButtonLoading(statusForm, true);

        fetch("/update-status/" + TASK_ID, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": window.HR_CSRF || "",
            Accept: "application/json",
            "X-Requested-With": "XMLHttpRequest",
          },
          body: JSON.stringify({ status: status }),
          credentials: "same-origin",
        })
          .then(function (r) {
            return r.json().then(function (data) {
              if (!r.ok) throw data;
              return data;
            });
          })
          .then(function (data) {
            renderPayload(data.payload || {}, { activityPage: 1, highlightFirst: true });
            var note = qs("#live-activity-new-note");
            if (note) note.classList.add("d-none");
            toast(tr("Status updated."));
          })
          .catch(function (err) {
            toast((err && (err.error || err.message)) || tr("Unable to update status."), "danger");
          })
          .finally(function () { setButtonLoading(statusForm, false); });
      } catch (e) {
        console.warn("task_detail status form error:", e);
      }
    });
  }

  document.addEventListener("click", function (e) {
    try {
      var link = e.target.closest("[data-activity-page-link]");
      if (!link || (link.closest(".disabled"))) return;

      e.preventDefault();
      var page = Number(link.dataset.activityPageLink || 1) || 1;
      fetchSections(["activities"], { activityPage: page }).catch(function () {
        toast(tr("Unable to load activity history."), "danger");
      });
    } catch (e) {
      console.warn("task_detail pagination click error:", e);
    }
  });

  var newActivityNote = qs("#live-activity-new-note");
  if (newActivityNote) {
    newActivityNote.addEventListener("click", function () {
      try {
        fetchSections(["activities"], { activityPage: 1, highlightFirst: true })
          .then(function () { newActivityNote.classList.add("d-none"); })
          .catch(function () { toast(tr("Unable to load latest activity."), "danger"); });
      } catch (e) {
        console.warn("task_detail activity note error:", e);
      }
    });
  }

  // Realtime socket with error boundary
  if (window.io) {
    try {
      var socket = io({ transports: ["websocket", "polling"] });
      socket.on("connect", function () {
        try {
          socket.emit("join_task", { task_id: TASK_ID });
        } catch (e) {
          console.warn("socket join_task error:", e);
        }
      });
      socket.on("task_live_update", function (msg) {
        try {
          if (msg && msg.task_id === TASK_ID) scheduleRefresh(msg.sections);
        } catch (e) {
          console.warn("socket task_live_update error:", e);
        }
      });
      socket.on("task_removed", function (msg) {
        try {
          if (msg && msg.task_id === TASK_ID) window.location.href = "/tasks";
        } catch (e) {
          console.warn("socket task_removed error:", e);
        }
      });
      window.addEventListener("beforeunload", function () {
        try {
          socket.emit("leave_task", { task_id: TASK_ID });
        } catch (_) {}
      });
    } catch (e) {
      console.warn("task_detail socket init error:", e);
    }
  }
})();