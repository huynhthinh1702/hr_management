// Dashboard: summary + analytics charts (keeps existing endpoints & realtime bus)
(function () {
  const root = document.getElementById("dashboardPage");
  if (!root) return;

  const els = {
    total: document.getElementById("live-total-tasks"),
    completed: document.getElementById("live-completed-tasks"),
    pending: document.getElementById("live-pending-tasks"),
    openIssues: document.getElementById("live-open-issues"),
    issueRate: document.getElementById("live-issue-rate"),
    issueCount: document.getElementById("live-issue-count"),
    issueProgress: document.getElementById("live-issue-progress"),
    recentIssues: document.getElementById("live-recent-issues"),
    overduePill: document.getElementById("live-overdue-pill"),
    heatmapWrap: document.getElementById("heatmapWrap"),
  };

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
  }

  function tr(text) {
    return window.HR_UI && window.HR_UI.t ? window.HR_UI.t(text) : text;
  }

  // --- Charts
  const taskCtx = document.getElementById("taskChart");
  const prodCtx = document.getElementById("prodChart");
  const trendCtx = document.getElementById("trendChart");

  if (!window.Chart || !taskCtx || !prodCtx || !trendCtx) return;

  const liveChart = new Chart(taskCtx, {
    type: "bar",
    data: {
      labels: [tr("Completed Tasks"), tr("Pending Tasks"), tr("Resolved Issues"), tr("Open Issues")],
      datasets: [
        {
          label: tr("Quantity"),
          data: [
            Number(root.dataset.completed || 0),
            Number(root.dataset.pending || 0),
            Number(root.dataset.resolvedIssues || 0),
            Number(root.dataset.unresolvedIssues || 0),
          ],
          backgroundColor: ["#16a34a", "#f59e0b", "#2563eb", "#dc2626"],
          borderRadius: 10,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });

  const prodChart = new Chart(prodCtx, {
    type: "bar",
    data: {
      labels: [],
      datasets: [{ label: tr("Completed"), data: [], backgroundColor: "#2563eb", borderRadius: 10 }],
    },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
  });

  const trendChart = new Chart(trendCtx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        { label: tr("Created"), data: [], borderColor: "#0ea5e9", backgroundColor: "rgba(14,165,233,0.12)", tension: 0.35, fill: true },
        { label: tr("Completed"), data: [], borderColor: "#16a34a", backgroundColor: "rgba(22,163,74,0.12)", tension: 0.35, fill: true },
      ],
    },
    options: { responsive: true, scales: { y: { beginAtZero: true } } },
  });

  function renderDashboard(payload) {
    if (els.total) els.total.textContent = payload.total_tasks;
    if (els.completed) els.completed.textContent = payload.completed_tasks;
    if (els.pending) els.pending.textContent = payload.pending_tasks;
    if (els.openIssues) els.openIssues.textContent = payload.unresolved_issues;

    if (els.issueRate) els.issueRate.textContent = payload.issue_resolution_rate + "%";
    if (els.issueCount) {
      els.issueCount.textContent =
        payload.resolved_issues + " / " + payload.total_issues + " " + tr("issues resolved");
    }
    if (els.issueProgress) {
      els.issueProgress.style.width = payload.issue_resolution_rate + "%";
      els.issueProgress.parentElement &&
        els.issueProgress.parentElement.setAttribute("aria-valuenow", payload.issue_resolution_rate);
    }

    liveChart.data.datasets[0].data = [
      payload.completed_tasks,
      payload.pending_tasks,
      payload.resolved_issues,
      payload.unresolved_issues,
    ];
    liveChart.update();

    if (!els.recentIssues) return;
    const wrap = els.recentIssues;
    if (!payload.recent_issues || !payload.recent_issues.length) {
      wrap.innerHTML = '<p class="text-muted mb-0">' + tr("No issues recorded yet.") + '</p>';
      return;
    }
    wrap.innerHTML =
      '<ul class="list-group list-group-flush">' +
      payload.recent_issues
        .map((i) => {
          const badge =
            i.status === "Resolved"
              ? '<span class="badge text-bg-success">' + tr("Resolved") + '</span>'
              : '<span class="badge text-bg-danger">' + tr("Open") + '</span>';
          return (
            '<li class="list-group-item px-0 d-flex justify-content-between gap-3">' +
            '<div class="min-w-0">' +
            '<div class="fw-semibold text-truncate">' +
            escapeHtml(i.title) +
            "</div>" +
            '<small class="text-muted">' +
            escapeHtml(i.creator_name) +
            "</small></div>" +
            badge +
            "</li>"
          );
        })
        .join("") +
      "</ul>";
  }

  function renderHeatmap(h) {
    if (!els.heatmapWrap) return;
    if (!h || !h.matrix || !h.matrix.length) {
      els.heatmapWrap.innerHTML = '<div class="text-muted small">' + tr("No activity yet.") + '</div>';
      return;
    }

    const rawLabels = h.weekday_labels || ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const labels = rawLabels.map((lb) => tr(lb));
    const hours = h.hours || Array.from({ length: 24 }, (_, i) => i);
    const matrix = h.matrix;
    let max = 0;
    matrix.forEach((row) => row.forEach((v) => (max = Math.max(max, v || 0))));
    max = max || 1;

    // Simple responsive heatmap using CSS grid (no extra libs)
    const cell = (v) => {
      const a = Math.max(0.06, Math.min(1, (v || 0) / max));
      return 'style="background: rgba(37, 99, 235, ' + a.toFixed(2) + ');" title="' + (v || 0) + '"';
    };

    const header =
      '<div class="d-none d-md-grid" style="display:grid;grid-template-columns:60px repeat(24,1fr);gap:4px;margin-bottom:8px;align-items:center;">' +
      '<div class="text-muted small"> </div>' +
      hours.map((hhr) => '<div class="text-muted small text-center">' + hhr + "</div>").join("") +
      "</div>";

    const rows =
      '<div style="display:grid;grid-template-columns:60px repeat(24,1fr);gap:4px;align-items:center;">' +
      matrix
        .map((row, i) => {
          return (
            '<div class="text-muted small">' +
            escapeHtml(labels[i] || "") +
            "</div>" +
            row
              .map((v) => '<div class="rounded-2" ' + cell(v) + '>&nbsp;</div>')
              .join("")
          );
        })
        .join("") +
      "</div>";

    els.heatmapWrap.innerHTML = header + rows;
  }

  function refreshSummary() {
    fetch("/api/dashboard/summary", { credentials: "same-origin" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) renderDashboard(data);
      })
      .catch(() => {});
  }

  function refreshAnalytics() {
    fetch("/api/dashboard/analytics", { credentials: "same-origin" })
      .then((r) => (r.ok ? r.json() : null))
      .then((a) => {
        if (!a) return;
        const p = a.productivity || [];
        prodChart.data.labels = p.map((x) => x.username);
        prodChart.data.datasets[0].data = p.map((x) => x.completed);
        prodChart.update();

        const t = a.trend || { labels: [], created: [], completed: [] };
        trendChart.data.labels = t.labels || [];
        trendChart.data.datasets[0].data = t.created || [];
        trendChart.data.datasets[1].data = t.completed || [];
        trendChart.update();

        const o = a.overdue || { count: 0, total: 0, rate: 0 };
        if (els.overduePill) {
          els.overduePill.textContent = tr("Overdue") + ": " + o.count + "/" + o.total + " (" + o.rate + "%)";
        }

        renderHeatmap(a.heatmap);
      })
      .catch(() => {});
  }

  // initial load
  refreshAnalytics();

  if (window.HR_LIVE) {
    window.HR_LIVE.onGlobalChange(() => {
      refreshSummary();
      refreshAnalytics();
    });
  }
})();

