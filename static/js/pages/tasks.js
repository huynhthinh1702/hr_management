// Tasks page: live refresh table (keeps existing /api/tasks/table)
(function () {
  const tbody = document.getElementById("live-task-rows");
  if (!tbody) return;

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
  }

  function tr(text) {
    return window.HR_UI && window.HR_UI.t ? window.HR_UI.t(text) : text;
  }

  function badgeStatus(status) {
    const map = {
      Pending: "secondary",
      "In Progress": "primary",
      Completed: "success",
    };
    const cls = map[status] || "secondary";
    return '<span class="badge text-bg-' + cls + ' tasks-pill">' + escapeHtml(tr(status)) + "</span>";
  }

  function badgePriority(priority) {
    const p = (priority || "Low").toLowerCase();
    const cls = p === "high" ? "danger" : p === "medium" ? "warning" : "info";
    return '<span class="badge text-bg-' + cls + ' tasks-pill">' + escapeHtml(tr(priority || "Low")) + "</span>";
  }

  function assignedUsers(users) {
    if (!users || !users.length) return '<span class="text-muted small">\u2014</span>';
    return users
      .map((u) => '<span class="badge text-bg-light border me-1">' + escapeHtml(u.full_name || u.username) + "</span>")
      .join("");
  }

  function renderRows(payload) {
    var allRows = [];

    // Render main tasks
    var tasks = payload.tasks || [];
    tasks.forEach(function (t) {
      var trClass = t.is_overdue ? ' class="table-danger"' : "";
      var deleteBadge = "";
      if (t.delete_request_status === "pending") {
        deleteBadge = '<span class="badge bg-warning ms-1"> ' + tr("Pending Delete Approval") + " </span>";
      }
      allRows.push(
        "<tr" + trClass + ">" +
        '<td class="col-sm-hide" data-label="ID">' + t.id + "</td>" +
        '<td data-label="Title">' + escapeHtml(t.title) + deleteBadge + "</td>" +
        '<td data-label="Status">' + badgeStatus(t.status) + "</td>" +
        '<td class="col-xs-hide" data-label="Priority">' + badgePriority(t.priority) + "</td>" +
        '<td class="col-sm-hide" data-label="Progress">' + (t.progress || 0) + "%</td>" +
        '<td class="col-sm-hide" data-label="Assigned To">' + assignedUsers(t.assigned_users) + "</td>" +
        '<td class="col-xs-hide" data-label="Deadline">' + escapeHtml(t.deadline || "") + "</td>" +
        '<td class="tasks-actions" data-label="Actions">' +
          '<a href="/task/' + t.id + '" class="btn btn-primary btn-sm">' + tr("View") + "</a>" +
          (t.can_delete
            ? ' <form method="POST" action="/delete-task/' + t.id + '" class="d-inline">' +
              '<input type="hidden" name="csrf_token" value="' + escapeHtml(window.HR_CSRF || "") + '">' +
              '<input type="text" name="reason" placeholder="' + escapeHtml(tr("Delete reason")) + '" class="form-control form-control-sm mb-1 d-none delete-reason-input">' +
              '<button type="button" class="btn btn-outline-danger btn-sm delete-toggle-btn" data-confirm="' + escapeHtml(tr("Send delete request?")) + '" data-confirm-ok="' + escapeHtml(tr("Send Request")) + '" data-confirm-submit="1">' + tr("Delete") + "</button>" +
              "</form>"
            : "") +
        "</td></tr>"
      );
    });

    // Render subtasks assigned to current user
    var subtasks = payload.subtasks || [];
    subtasks.forEach(function (s) {
      allRows.push(
        '<tr class="table-info">' +
        '<td class="col-sm-hide" data-label="ID">S-' + s.id + "</td>" +
        '<td data-label="Title">' + escapeHtml(s.title) + '<span class="badge bg-info ms-2">' + tr("Subtask") + "</span></td>" +
        '<td data-label="Status"><span class="badge text-bg-primary">' + escapeHtml(tr(s.status)) + "</span></td>" +
        '<td class="col-xs-hide" data-label="Priority">-</td>' +
        '<td class="col-sm-hide" data-label="Progress">' + (s.progress || 0) + "%</td>" +
        '<td class="col-sm-hide" data-label="Assigned To"><span class="badge text-bg-light border">' + escapeHtml(s.subtask_assigned_name || "") + "</span></td>" +
        '<td class="col-xs-hide" data-label="Deadline">-</td>' +
        '<td class="tasks-actions" data-label="Actions">' +
          '<a href="/subtask/' + s.id + '" class="btn btn-primary btn-sm">' + tr("View") + "</a>" +
          ' <a href="/update-subtask/' + s.id + '" class="btn btn-warning btn-sm">' + tr("Update") + "</a>" +
        "</td></tr>"
      );
    });

    if (!allRows.length) {
      allRows.push(
        '<tr><td colspan="9" class="text-muted py-4 text-center">' +
        '<div class="fw-semibold">' + tr("No tasks found") + "</div>" +
        '<div class="small">' + tr("Try changing filters or create a new task.") + "</div>" +
        "</td></tr>"
      );
    }

    tbody.innerHTML = allRows.join("");
  }

  function refresh() {
    try {
      var params = new URLSearchParams(window.location.search);
      fetch("/api/tasks/table?" + params.toString(), { credentials: "same-origin" })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (data) {
          if (data) {
            renderRows(data);
            if (window.HR_UI && window.HR_UI.applyI18n) window.HR_UI.applyI18n(tbody);
          }
        })
        .catch(function () {});
    } catch (e) {
      console.warn("tasks.js refresh error:", e);
    }
  }

  if (window.HR_LIVE) {
    window.HR_LIVE.onGlobalChange(refresh);
  }

  // Delete toggle: show/hide reason input on click
  document.addEventListener("click", function (e) {
    try {
      var btn = e.target.closest(".delete-toggle-btn");
      if (!btn) return;
      var form = btn.closest("form");
      if (!form) return;
      var input = form.querySelector(".delete-reason-input");
      if (!input) return;

      if (input.classList.contains("d-none")) {
        e.preventDefault();
        input.classList.remove("d-none");
        input.focus();
        return;
      }
    } catch (e) {
      console.warn("tasks.js click handler error:", e);
    }
  });
})();