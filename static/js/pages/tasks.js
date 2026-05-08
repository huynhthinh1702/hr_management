// Tasks page: live refresh table (keeps existing /api/tasks/table)
(function () {
  const tbody = document.getElementById("live-task-rows");
  if (!tbody) return;

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
  }

  function badgeStatus(status) {
    const map = {
      Pending: "secondary",
      "In Progress": "primary",
      Completed: "success",
    };
    const cls = map[status] || "secondary";
    return '<span class="badge text-bg-' + cls + ' tasks-pill">' + escapeHtml(status) + "</span>";
  }

  function badgePriority(priority) {
    const p = (priority || "Low").toLowerCase();
    const cls = p === "high" ? "danger" : p === "medium" ? "warning" : "info";
    return '<span class="badge text-bg-' + cls + ' tasks-pill">' + escapeHtml(priority || "Low") + "</span>";
  }

  function assignedUsers(users) {
    if (!users || !users.length) return '<span class="text-muted small">—</span>';
    return users
      .map((u) => '<span class="badge text-bg-light border me-1">' + escapeHtml(u.username) + "</span>")
      .join("");
  }

  function renderRows(payload) {
    if (!payload.tasks || !payload.tasks.length) {
      tbody.innerHTML =
        '<tr><td colspan="9" class="text-muted py-4 text-center">' +
        '<div class="fw-semibold">No tasks found</div>' +
        '<div class="small">Try changing filters or create a new task.</div>' +
        "</td></tr>";
      return;
    }

    tbody.innerHTML = payload.tasks
      .map((t) => {
        const trClass = t.is_overdue ? ' class="table-danger"' : "";
        return (
          "<tr" +
          trClass +
          ">" +
          '<td class="col-sm-hide">' +
          t.id +
          "</td>" +
          "<td>" +
          escapeHtml(t.title) +
          "</td>" +
          "<td>" +
          badgeStatus(t.status) +
          "</td>" +
          '<td class="col-xs-hide">' +
          badgePriority(t.priority) +
          "</td>" +
          '<td class="col-sm-hide">' +
          (t.progress || 0) +
          "%</td>" +
          '<td class="col-sm-hide">' +
          assignedUsers(t.assigned_users) +
          "</td>" +
          '<td class="col-xs-hide">' +
          escapeHtml(t.deadline || "") +
          "</td>" +
          '<td class="tasks-actions">' +
          '<a href="/update-task/' +
          t.id +
          '" class="btn btn-outline-primary btn-sm">Update</a> ' +
          '<form method="POST" action="/delete-task/' +
          t.id +
          '" class="d-inline">' +
          '<input type="hidden" name="csrf_token" value="' +
          escapeHtml(window.HR_CSRF || "") +
          '">' +
          '<button type="button" class="btn btn-outline-danger btn-sm" data-confirm="Delete this task?" data-confirm-ok="Delete" data-confirm-submit="1">Delete</button>' +
          "</form> " +
          '<a href="/task/' +
          t.id +
          '" class="btn btn-primary btn-sm">View</a>' +
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
        if (data) renderRows(data);
      })
      .catch(() => {});
  }

  if (window.HR_LIVE) {
    window.HR_LIVE.onGlobalChange(refresh);
  }
})();

