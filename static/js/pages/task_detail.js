// Task detail: per-task room updates + live payload rendering
(function () {
  const root = document.getElementById("taskDetailPage");
  if (!root) return;

  const TASK_ID = Number(root.dataset.taskId || 0);
  if (!TASK_ID) return;

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
  }

  const badgeForStatus = (status) => {
    const map = { Completed: "success", "In Progress": "primary", Pending: "secondary" };
    const cls = map[status] || "secondary";
    return "badge rounded-pill bg-" + cls;
  };

  function activityMeta(action) {
    const a = (action || "").toLowerCase();
    if (a.includes("comment")) return { dot: "hr-dot-comment", icon: "bi-chat-dots" };
    if (a.includes("upload")) return { dot: "hr-dot-upload", icon: "bi-paperclip" };
    if (a.includes("completed")) return { dot: "hr-dot-complete", icon: "bi-check2-circle" };
    if (a.includes("issue")) return { dot: "hr-dot-issue", icon: "bi-bug" };
    if (a.includes("moved")) return { dot: "hr-dot-move", icon: "bi-arrow-left-right" };
    return { dot: "hr-dot-default", icon: "bi-clock-history" };
  }

  function renderFromPayload(data) {
    const t = data.task;
    document.getElementById("live-task-title").textContent = t.title;
    document.getElementById("live-task-description").textContent = t.description;

    const st = document.getElementById("live-task-status");
    st.textContent = t.status;
    st.className = badgeForStatus(t.status);

    document.getElementById("live-task-progress-label").textContent = t.progress + "% complete";
    const pr = document.getElementById("live-task-priority");
    if (pr) pr.textContent = (t.priority || "") + (t.priority ? " priority" : "");

    // Subtasks
    const subBody = document.getElementById("live-subtasks-tbody");
    subBody.innerHTML = "";
    if (!data.subtasks.length) {
      subBody.innerHTML = '<tr><td colspan="5" class="text-muted">No subtasks yet.</td></tr>';
    } else {
      data.subtasks.forEach((s) => {
        const tr = document.createElement("tr");
        tr.innerHTML =
          "<td>" +
          s.id +
          "</td>" +
          "<td>" +
          escapeHtml(s.title) +
          "</td>" +
          "<td>" +
          escapeHtml(s.status) +
          "</td>" +
          "<td>" +
          s.progress +
          "%</td>" +
          "<td>" +
          '<a href="/update-subtask/' +
          s.id +
          '" class="btn btn-outline-primary btn-sm">Update</a> ' +
          '<form method="POST" action="/delete-subtask/' +
          s.id +
          '" class="d-inline">' +
          '<input type="hidden" name="csrf_token" value="' +
          escapeHtml(window.HR_CSRF || "") +
          '">' +
          '<button type="button" class="btn btn-outline-danger btn-sm" data-confirm="Delete this subtask?" data-confirm-ok="Delete" data-confirm-submit="1">Delete</button>' +
          "</form>" +
          "</td>";
        subBody.appendChild(tr);
      });
    }

    // Comments
    const comm = document.getElementById("live-comments");
    if (!data.comments.length) {
      comm.innerHTML = '<p class="text-muted mb-0">No comments yet.</p>';
    } else {
      comm.innerHTML = data.comments
        .map(
          (c) =>
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
        )
        .join("");
    }

    // Issues
    const iss = document.getElementById("live-issues");
    if (!data.issues.length) {
      iss.innerHTML = '<p class="text-muted mb-0">No issues reported.</p>';
    } else {
      iss.innerHTML = data.issues
        .map((i) => {
          const badge =
            i.status === "Resolved"
              ? '<span class="badge text-bg-success">Resolved</span>'
              : '<span class="badge text-bg-danger">Open</span>';
          const desc = i.description
            ? '<div class="mt-2 text-muted">' + escapeHtml(i.description).replace(/\n/g, "<br>") + "</div>"
            : "";
          const resolveForm =
            i.status !== "Resolved"
              ? '<form method="POST" action="/issues/' +
                i.id +
                '/resolve" class="mt-2">' +
                '<input type="hidden" name="csrf_token" value="' +
                escapeHtml(window.HR_CSRF || "") +
                '">' +
                '<button class="btn btn-outline-success btn-sm">Mark as Resolved</button></form>'
              : "";
          return (
            '<div class="border rounded-3 p-3 mb-2 bg-white">' +
            '<div class="d-flex justify-content-between align-items-start gap-3">' +
            '<div class="min-w-0">' +
            '<div class="fw-semibold text-truncate">' +
            escapeHtml(i.title) +
            "</div>" +
            '<small class="text-muted">by ' +
            escapeHtml(i.creator_name) +
            " - " +
            escapeHtml(i.created_at) +
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

    // Attachments
    const ulAtt = document.getElementById("live-attachments");
    const emptyAtt = document.getElementById("live-attachments-empty");
    ulAtt.innerHTML = "";
    if (!data.attachments.length) {
      emptyAtt.classList.remove("d-none");
    } else {
      emptyAtt.classList.add("d-none");
      data.attachments.forEach((a) => {
        const li = document.createElement("li");
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
          '" class="btn btn-outline-secondary btn-sm">Download</a>';
        ulAtt.appendChild(li);
      });
    }

    // Activities (live = only last 5)
    const note = document.getElementById("live-activity-sync-note");
    if (note) note.classList.remove("d-none");

    const actWrap = document.getElementById("live-activities-wrap");
    if (!data.activities.length) {
      actWrap.innerHTML = '<p class="text-muted mb-0">No activity recorded.</p>';
    } else {
      actWrap.innerHTML =
        '<ul class="hr-timeline" id="live-activities">' +
        data.activities
          .map((a) => {
            const meta = activityMeta(a.action);
            return (
              '<li class="hr-timeline-item">' +
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
              '<div class="small text-muted mt-1">by ' +
              escapeHtml(a.actor_name) +
              "</div>" +
              "</div>" +
              "</li>"
            );
          })
          .join("") +
        "</ul>";
    }
  }

  let refreshTimer;
  function scheduleRefresh() {
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(() => {
      fetch("/api/task/" + TASK_ID + "/live", { credentials: "same-origin" })
        .then((r) => {
          if (!r.ok) throw new Error("fetch failed");
          return r.json();
        })
        .then(renderFromPayload)
        .catch(() => {});
    }, 220);
  }

  // Join per-task room (keeps existing server handlers)
  if (window.io) {
    const socket = io({ transports: ["websocket", "polling"] });
    socket.on("connect", () => socket.emit("join_task", { task_id: TASK_ID }));
    socket.on("task_live_update", (msg) => {
      if (msg && msg.task_id === TASK_ID) scheduleRefresh();
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
})();

