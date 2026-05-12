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
    if (!users || !users.length) return '<span class="text-muted small">—</span>';
    return users
      .map((u) => '<span class="badge text-bg-light border me-1">' + escapeHtml(u.full_name || u.username) + "</span>")
      .join("");
  }

  function renderRows(payload) {
    if (!payload.tasks || !payload.tasks.length) {
      tbody.innerHTML =
        '<tr><td colspan="9" class="text-muted py-4 text-center">' +
        '<div class="fw-semibold">' +
        tr("No tasks found") +
        "</div>" +
        '<div class="small">' +
        tr("Try changing filters or create a new task.") +
        "</div>" +
        "</td></tr>";
      return;
    }

    tbody.innerHTML = payload.tasks
      .map((t) => {
        const trClass = t.is_overdue ? ' class="table-danger"' : "";

        let deleteBadge ="";
        if (t.delete_request_status === "pending") {
          deleteBadge = '<span class="badge bg-warning ms-1"> ' + tr("Pending Delete Approval") + " </span>";
        }
        return (
          "<tr" +
          trClass +
          ">" +
          '<td class="col-sm-hide" data-label="ID">' +
          t.id +
          "</td>" +
          '<td data-label="Title">' +
          escapeHtml(t.title) + deleteBadge +
          "</td>" +
          '<td data-label="Status">' +
          badgeStatus(t.status) +
          "</td>" +
          '<td class="col-xs-hide" data-label="Priority">' +
          badgePriority(t.priority) +
          "</td>" +
          '<td class="col-sm-hide" data-label="Progress">' +
          (t.progress || 0) +
          "%</td>" +
          '<td class="col-sm-hide" data-label="Assigned To">' +
          assignedUsers(t.assigned_users) +
          "</td>" +
          '<td class="col-xs-hide" data-label="Deadline">' +
          escapeHtml(t.deadline || "") +
          "</td>" +
          '<td class="tasks-actions" data-label="Actions">' +
          '<a href="/update-task/' +
          t.id +
          '" class="btn btn-outline-primary btn-sm">' +
          tr("Update") +
          "</a> " +
          '<form method="POST" action="/delete-task/' +
          t.id +
          '" class="d-inline">' +
          '<input type="hidden" name="csrf_token" value="' +
          escapeHtml(window.HR_CSRF || "") +
          '">' +
          '<input type="text" name="reason" placeholder="' +
          escapeHtml(tr("Delete reason")) +
          '" class="form-control form-control-sm mb-1">' +
          '<button type="button" class="btn btn-outline-danger btn-sm" data-confirm="' +
          escapeHtml(tr("Send delete request?")) +
          '" data-confirm-ok="' +
          escapeHtml(tr("Send Request")) +
          '" data-confirm-submit="1">' +
          tr("Delete") +
          "</button>" +
          "</form> " +
          '<a href="/task/' +
          t.id +
          '" class="btn btn-primary btn-sm">' +
          tr("View") +
          "</a>" +
          "</td>" +
          "</tr>"
        );
      })
      .join("");
  }

  function refresh() {
    const params = new URLSearchParams(window.location.search);
    fetch("/api/tasks/table?" + params.toString(), { credentials: "same-origin" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) {
          renderRows(data);
          if (window.HR_UI && window.HR_UI.applyI18n) window.HR_UI.applyI18n(tbody);
        }
      })
      .catch(() => {});
  }

  if (window.HR_LIVE) {
    window.HR_LIVE.onGlobalChange(refresh);
  }

})();

