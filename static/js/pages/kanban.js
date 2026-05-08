// Kanban page: Sortable + live refresh (keeps existing endpoints/events)
(function () {
  const pending = document.getElementById("pending-list");
  const progress = document.getElementById("progress-list");
  const completed = document.getElementById("completed-list");

  if (!pending || !progress || !completed) return;

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
  }

  function renderCard(t, badgeClass) {
    return (
      '<div class="task-card" data-task-id="' +
      t.id +
      '">' +
      "<h5>" +
      escapeHtml(t.title) +
      "</h5>" +
      "<p>" +
      escapeHtml(t.description || "") +
      "</p>" +
      '<div class="d-flex justify-content-between align-items-center">' +
      '<span class="badge ' +
      badgeClass +
      '">' +
      (t.progress || 0) +
      "%</span>" +
      '<a href="/task/' +
      t.id +
      '" class="btn btn-sm btn-primary">View</a>' +
      "</div>" +
      "</div>"
    );
  }

  function refresh() {
    fetch("/api/kanban/columns", { credentials: "same-origin" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!data) return;
        pending.innerHTML = (data.pending || [])
          .map((t) => renderCard(t, "bg-secondary"))
          .join("");
        progress.innerHTML = (data.progress || [])
          .map((t) => renderCard(t, "bg-info"))
          .join("");
        completed.innerHTML = (data.completed || [])
          .map((t) => renderCard(t, "bg-success"))
          .join("");
      })
      .catch(() => {});
  }

  function postStatus(taskId, statusName) {
    fetch("/update-status/" + taskId, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.HR_CSRF || "",
      },
      body: JSON.stringify({ status: statusName }),
      credentials: "same-origin",
    })
      .then(() => {
        if (window.HR_UI && typeof window.HR_UI.toast === "function") {
          window.HR_UI.toast("Moved task to " + statusName + ".", { title: "Kanban", variant: "success" });
        }
      })
      .catch(() => {});
  }

  function initSortable(el, statusName) {
    if (!window.Sortable) return;
    // eslint-disable-next-line no-new
    new Sortable(el, {
      group: "tasks",
      animation: 150,
      onAdd(evt) {
        const taskId = evt.item && evt.item.dataset ? evt.item.dataset.taskId : null;
        if (taskId) postStatus(taskId, statusName);
      },
    });
  }

  initSortable(pending, "Pending");
  initSortable(progress, "In Progress");
  initSortable(completed, "Completed");

  if (window.HR_LIVE) {
    window.HR_LIVE.onGlobalChange(refresh);
  }
})();

