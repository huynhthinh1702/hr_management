// Bootstrap modal confirm + form loading spinner + VI strings
(function () {
  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  window.HR_CSRF =
    qs('meta[name="csrf-token"]')?.getAttribute("content") || window.HR_CSRF || "";

  const I18N = {
    vi: {
      "Home": "Trang chủ",
      "Login": "Đăng nhập",
      "Register": "Đăng ký",
      "Logout": "Đăng xuất",
      "Sidebar": "Thanh sidebar",
      "Navigation": "Điều hướng",
      "Welcome": "Chào mừng",
      "Dashboard": "Bảng điều khiển",
      "Tasks": "Công việc",
      "Task List": "Danh sách công việc",
      "Create Task": "Tạo công việc",
      "+ Create Task": "+ Tạo công việc",
      "+ New Task": "+ Công việc mới",
      "New Task": "Công việc mới",
      "Archived Tasks": "Công việc lưu trữ",
      "Kanban Board": "Bảng Kanban",
      "Admin Users": "Quản lý người dùng",
      "Profile": "Hồ sơ",
      "User Guide": "Hướng dẫn",
      "Notifications": "Thông báo",
      "Notification": "Thông báo",
      "No notifications.": "Không có thông báo.",
      "Mark read": "Đánh dấu đã đọc",
      "Email": "Email",
      "Password": "Mật khẩu",
      "Forgot password?": "Quên mật khẩu?",
      "Full Name": "Họ và tên",
      "Username": "Tên đăng nhập",
      "Confirm": "Xác nhận",
      "Cancel": "Hủy",
      "Continue": "Tiếp tục",
      "Close": "Đóng",
      "Apply": "Áp dụng",
      "Reset": "Đặt lại",
      "Search task...": "Tìm công việc...",
      "All Status": "Tất cả trạng thái",
      "Pending": "Đang chờ",
      "In Progress": "Đang xử lý",
      "Completed": "Hoàn thành",
      "Update": "Cập nhật",
      "Delete": "Xóa",
      "View": "Xem",
      "Delete reason": "Lý do xóa",
      "Title": "Tiêu đề",
      "Status": "Trạng thái",
      "Actions": "Thao tác",
      "Priority": "Ưu tiên",
      "Progress": "Tiến độ",
      "Assigned To": "Người phụ trách",
      "Deadline": "Hạn chót",
      "Overview tasks and issue resolution progress.": "Tổng quan công việc và tiến độ xử lý vấn đề.",
      "Total Tasks": "Tổng công việc",
      "Open Issues": "Vấn đề đang có",
      "Task & Issue Statistics": "Thống kê công việc và vấn đề",
      "Issue Resolution": "Xử lý vấn đề",
      "Recent Issues": "Vấn đề gần đây",
      "Productivity by Employee": "Hiệu suất theo nhân viên",
      "Task Trend (Last 30 days)": "Xu hướng công việc (30 ngày)",
      "Average": "Trung bình",
      "Median": "Trung vị",
      "Activity Heatmap": "Bản đồ hoạt động",
      "No issues recorded yet.": "Chưa có vấn đề nào.",
      "No activity yet.": "Chưa có hoạt động.",
      "Invalid Login": "Đăng nhập không thành công",
      "The email or password is incorrect. Please try again.": "Email hoặc mật khẩu không đúng. Vui lòng thử lại.",
      "Account Locked": "Tài khoản bị khóa",
      "Your account is locked. Please contact an administrator.": "Tài khoản của bạn đang bị khóa. Vui lòng liên hệ quản trị viên.",
      "Loading...": "Đang tải...",
      "Select employees": "Chọn nhân viên",
      "Completed Tasks": "Công việc đã hoàn thành",
      "Pending Tasks": "Công việc đang chờ",
      "Resolved Issues": "Vấn đề đã xử lý",
      "Quantity": "Số lượng",
      "Created": "Đã tạo",
      "Resolved": "Đã xử lý",
      "Open": "Đang mở",
      "issues resolved": "vấn đề đã xử lý",
      "Overdue": "Quá hạn",
      "days": "ngày",
      "Based on": "Dựa trên",
      "completed tasks with activity logs.": "công việc đã hoàn thành có nhật ký hoạt động.",
      "Are you sure?": "Bạn có chắc không?",
      "Yes, continue": "Có, tiếp tục",
      "Confirm action": "Xác nhận thao tác",
      "Assign Employees": "Nhân viên phụ trách",
      "Search user by name...": "Tìm nhân viên theo tên...",
      "Description": "Mô tả",
      "Low": "Thấp",
      "Medium": "Trung bình",
      "High": "Cao",
      "Update Task": "Cập nhật công việc",
      "Progress (%)": "Tiến độ (%)",
      "Create Subtask": "Tạo công việc con",
      "Subtask Title": "Tiêu đề công việc con",
      "Update Subtask": "Cập nhật công việc con",
      "Drag & drop tasks between columns.": "Kéo thả công việc giữa các cột.",
      "Live updates enabled": "Cập nhật trực tiếp đã bật",
      "No pending tasks.": "Không có công việc đang chờ.",
      "No tasks in progress.": "Không có công việc đang xử lý.",
      "No completed tasks.": "Không có công việc hoàn thành.",
      "Top 12": "Top 12",
      "By weekday/hour": "Theo ngày trong tuần/giờ",
      "Task Detail": "Chi tiết công việc",
      "complete": "hoàn thành",
      "Low priority": "Ưu tiên thấp",
      "Medium priority": "Ưu tiên trung bình",
      "High priority": "Ưu tiên cao",
      "Add Subtask": "Thêm công việc con",
      "Subtasks": "Công việc con",
      "Action": "Thao tác",
      "Update Status": "Cập nhật trạng thái",
      "Request Update": "Yêu cầu cập nhật",
      "Optional update request note": "Ghi chú yêu cầu cập nhật (tuỳ chọn)",
      "Task Comments": "Bình luận công việc",
      "Write your comment...": "Viết bình luận...",
      "Post Comment": "Gửi bình luận",
      "No comments yet.": "Chưa có bình luận.",
      "Bug / Issue Tracker": "Theo dõi lỗi / sự cố",
      "Normal": "Bình thường",
      "Critical": "Nghiêm trọng",
      "Describe this bug or problem": "Mô tả lỗi hoặc vấn đề",
      "Report Issue": "Báo cáo sự cố",
      "by": "bởi",
      "Issue title": "Tiêu đề sự cố",
      "Mark as Resolved": "Đánh dấu đã xử lý",
      "No issues reported.": "Chưa có sự cố nào được báo.",
      "File Upload": "Tải tệp lên",
      "Upload File": "Tải lên",
      "No files uploaded.": "Chưa có tệp nào.",
      "Download": "Tải xuống",
      "Activity History": "Lịch sử hoạt động",
      "No activity recorded.": "Chưa có hoạt động.",
      "Prev": "Trước",
      "Next": "Sau",
      "No subtasks yet.": "Chưa có công việc con.",
      "Delete this subtask?": "Xóa công việc con này?",
      "Delete this task?": "Xóa công việc này?",
      "Send delete request?": "Gửi yêu cầu xóa?",
      "Send Request": "Gửi yêu cầu",
      "Pending Delete Approval": "Đang chờ duyệt xóa",
      "No tasks found": "Không tìm thấy công việc",
      "Try changing filters or create a new task.": "Thử đổi bộ lọc hoặc tạo công việc mới.",
      "Previous": "Trước",
      "Manage your account, avatar, and security settings.": "Quản lý tài khoản, ảnh đại diện và bảo mật.",
      "Update avatar": "Cập nhật ảnh đại diện",
      "Save Avatar": "Lưu ảnh đại diện",
      "Personal Information": "Thông tin cá nhân",
      "Public profile": "Hồ sơ công khai",
      "Bio": "Giới thiệu",
      "Save Changes": "Lưu thay đổi",
      "Security": "Bảo mật",
      "Current Password": "Mật khẩu hiện tại",
      "New Password": "Mật khẩu mới",
      "Confirm Password": "Xác nhận mật khẩu",
      "Update Password": "Đổi mật khẩu",
      "At least 8 characters with uppercase, lowercase, number, and special character.": "Ít nhất 8 ký tự gồm chữ hoa, chữ thường, số và ký tự đặc biệt.",
      "Forgot Password": "Quên mật khẩu",
      "Back to login": "Quay lại đăng nhập",
      "Deleted By": "Người xóa",
      "Deleted At": "Thời điểm xóa",
      "Reason": "Lý do",
      "Got it": "Đã hiểu",
      "Saved.": "Đã lưu.",
      "Unable to save changes.": "Không thể lưu thay đổi.",
      "Status updated.": "Đã cập nhật trạng thái.",
      "Unable to update status.": "Không thể cập nhật trạng thái.",
      "Unable to load activity history.": "Không thể tải lịch sử hoạt động.",
      "Unable to load latest activity.": "Không thể tải hoạt động mới nhất.",
      "New activity available": "Có hoạt động mới",
      "Comment added.": "Đã thêm bình luận.",
      "Issue reported.": "Đã báo cáo sự cố.",
      "Issue resolved.": "Đã xử lý sự cố.",
      "Task moved successfully.": "Đã di chuyển công việc.",
      "Kanban": "Kanban",
      "Sun": "CN",
      "Mon": "T2",
      "Tue": "T3",
      "Wed": "T4",
      "Thu": "T5",
      "Fri": "T6",
      "Sat": "T7",
      "HR Management System": "Hệ thống quản lý nhân sự",
      "Home - HR Management": "Trang chủ - Quản lý nhân sự",
      "Upgrade the interface and work management tools for the entire team.": "Nâng cấp giao diện và công cụ quản lý công việc cho toàn bộ đội ngũ.",
      "Username already exists.": "Tên đăng nhập đã tồn tại.",
      "Email already exists.": "Email đã tồn tại.",
      "Password must be at least 8 characters.": "Mật khẩu phải có ít nhất 8 ký tự.",
      "Password must include an uppercase letter.": "Mật khẩu phải có ít nhất một chữ hoa.",
      "Password must include a lowercase letter.": "Mật khẩu phải có ít nhất một chữ thường.",
      "Password must include a number.": "Mật khẩu phải có ít nhất một chữ số.",
      "Password must include a special character.": "Mật khẩu phải có ít nhất một ký tự đặc biệt.",
      "Registration successful. Your account role is employee.": "Đăng ký thành công. Vai trò tài khoản của bạn là nhân viên.",
      "Full name and email do not match an existing account.": "Họ tên và email không khớp với tài khoản hiện có.",
      "Password reset request sent to admin.": "Đã gửi yêu cầu đặt lại mật khẩu tới quản trị viên.",
      "Invalid role.": "Vai trò không hợp lệ.",
      "User updated.": "Đã cập nhật người dùng.",
      "You cannot lock your own account.": "Bạn không thể khóa tài khoản của chính mình.",
      "Account status updated.": "Đã cập nhật trạng thái tài khoản.",
      "You cannot delete your own account.": "Bạn không thể xóa tài khoản của chính mình.",
      "User deleted.": "Đã xóa người dùng.",
      "Update request sent.": "Đã gửi yêu cầu cập nhật.",
      "Edit": "Sửa",
      "Lock": "Khóa",
      "Unlock": "Mở khóa",
      "Reset Password": "Đặt lại mật khẩu",
      "Comment content is required.": "Vui lòng nhập nội dung bình luận.",
      "Issue title is required.": "Vui lòng nhập tiêu đề sự cố.",
    },
  };

  function tr(text) {
    const lang = document.documentElement.lang || "en";
    const dict = I18N[lang] || {};
    return dict[text] || text;
  }

  window.HR_UI = window.HR_UI || {};
  window.HR_UI.t = tr;

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

    qs("[data-hr-confirm-title]", modalEl).textContent = tr(title || "Confirm");
    qs("[data-hr-confirm-message]", modalEl).textContent = tr(message || "Are you sure?");
    const okBtn = qs("[data-hr-confirm-ok]", modalEl);
    okBtn.textContent = tr(okText || "Yes, continue");
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
    const msg = a.getAttribute("data-confirm") || tr("Are you sure?");
    const okText = a.getAttribute("data-confirm-ok") || tr("Delete");
    const variant = a.getAttribute("data-confirm-variant") || "btn-danger";
    const title = a.getAttribute("data-confirm-title") || tr("Confirm action");

    const didOpen = openConfirm({ title, message: msg, okText, variant }, () => {
      window.location.href = a.href;
    });

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
    const msg = btn.getAttribute("data-confirm") || tr("Are you sure?");
    const okText = btn.getAttribute("data-confirm-ok") || tr("Continue");
    const variant = btn.getAttribute("data-confirm-variant") || "btn-danger";
    const title = btn.getAttribute("data-confirm-title") || tr("Confirm action");

    const didOpen = openConfirm({ title, message: msg, okText, variant }, () => {
      form.submit();
    });

    if (!didOpen) {
      // eslint-disable-next-line no-alert
      if (confirm(msg)) form.submit();
    }
  });

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
      "<span>" +
      tr("Loading...") +
      "</span>";
  });

  function toast(message, opts) {
    const container = qs("#hrToastContainer");
    if (!container || !window.bootstrap) return;
    const o = opts || {};
    const title = o.title || tr("Notification");
    const variant = o.variant || "primary";
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
      '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="' +
      tr("Close") +
      '"></button>' +
      "</div>";

    container.appendChild(el);
    const bsToast = new bootstrap.Toast(el, { delay });
    el.addEventListener("hidden.bs.toast", () => el.remove());
    bsToast.show();
  }

  window.HR_UI.toast = toast;

  function applyI18n(root) {
    const lang = document.documentElement.lang || "en";
    if (lang === "en") return;
    const scope = root || document.body;
    scope.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if (key && I18N[lang]?.[key]) el.textContent = I18N[lang][key];
    });
    scope.querySelectorAll("input[placeholder], textarea[placeholder]").forEach((el) => {
      const key = el.getAttribute("placeholder");
      if (key && I18N[lang]?.[key]) el.setAttribute("placeholder", I18N[lang][key]);
    });
    scope.querySelectorAll("[data-label]").forEach((el) => {
      const key = el.getAttribute("data-label");
      if (key && I18N[lang]?.[key]) el.setAttribute("data-label", I18N[lang][key]);
    });
    const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        const parent = node.parentElement;
        if (!parent || ["SCRIPT", "STYLE", "TEXTAREA"].includes(parent.tagName)) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      const raw = node.nodeValue;
      const trimmed = raw.trim();
      if (I18N[lang]?.[trimmed]) {
        node.nodeValue = raw.replace(trimmed, I18N[lang][trimmed]);
      }
    });
  }

  window.HR_UI.applyI18n = applyI18n;
  applyI18n();

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
  }

  function renderNotifications(data) {
    const menu = qs("#notificationMenu");
    if (!menu || !data) return;
    let badge = qs("#notificationBadge");
    const toggle = qs("#notificationDropdown");
    if (data.unread_count > 0 && toggle && !badge) {
      badge = document.createElement("span");
      badge.id = "notificationBadge";
      badge.className = "position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger";
      toggle.appendChild(badge);
    }
    if (badge) {
      if (data.unread_count > 0) badge.textContent = data.unread_count;
      else badge.remove();
    }

    const header = menu.querySelector(".border-bottom");
    let readBtn = qs("[data-notifications-read]", menu);
    if (data.unread_count > 0 && !readBtn && header) {
      readBtn = document.createElement("button");
      readBtn.className = "btn btn-link btn-sm p-0 text-decoration-none";
      readBtn.type = "button";
      readBtn.setAttribute("data-notifications-read", "");
      readBtn.setAttribute("data-i18n", "Mark read");
      readBtn.textContent = tr("Mark read");
      header.appendChild(readBtn);
    } else if (data.unread_count === 0 && readBtn) {
      readBtn.remove();
    }

    const body = data.items && data.items.length
      ? '<div class="notification-list" id="notificationList">' +
        data.items.map((item) => (
          '<a href="' + escapeHtml(item.url || "#") + '" class="dropdown-item notification-item ' + (!item.is_read ? "is-unread" : "") + '">' +
          '<div class="d-flex justify-content-between gap-2">' +
          '<div class="fw-semibold text-wrap">' + escapeHtml(item.title) + '</div>' +
          '<small class="text-muted text-nowrap">' + escapeHtml(item.created_at || "") + '</small>' +
          '</div>' +
          '<div class="small text-muted text-wrap">' + escapeHtml(item.message) + '</div>' +
          '</a>'
        )).join("") +
        '</div>'
      : '<div class="px-3 py-4 text-center text-muted small" id="notificationEmpty" data-i18n="No notifications.">' + tr("No notifications.") + '</div>';

    Array.from(menu.children).forEach((child) => {
      if (!child.classList.contains("border-bottom")) child.remove();
    });
    menu.insertAdjacentHTML("beforeend", body);
    applyI18n(menu);
  }

  function refreshNotifications({ showToast } = {}) {
    if (!qs("#notificationMenu")) return Promise.resolve();
    return fetch("/api/notifications", { credentials: "same-origin" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!data) return;
        const previous = Number(qs("#notificationBadge")?.textContent || 0);
        renderNotifications(data);
        if (showToast && data.unread_count > previous && data.items && data.items[0]) {
          toast(data.items[0].message, { title: data.items[0].title, variant: "info" });
        }
      })
      .catch(() => {});
  }

  document.addEventListener("click", (e) => {
    const readNotifications = e.target.closest("[data-notifications-read]");
    if (readNotifications) {
      fetch("/api/notifications/read", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": window.HR_CSRF || "",
          "Content-Type": "application/json",
        },
        body: "{}",
      }).then((r) => {
        if (!r.ok) return;
        qs("#notificationBadge")?.remove();
        document.querySelectorAll(".notification-item.is-unread").forEach((el) => {
          el.classList.remove("is-unread");
        });
        readNotifications.remove();
        refreshNotifications();
      });
    }
  });

  if (window.HR_LIVE) {
    window.HR_LIVE.onGlobalChange(() => refreshNotifications({ showToast: true }));
  }

  const guideEl = qs("#userGuideModal");
  if (guideEl && window.bootstrap) {
    const markGuideSeen = () => {
      if (guideEl.getAttribute("data-guide-marked") === "1") return;
      guideEl.setAttribute("data-guide-marked", "1");
      fetch("/user-guide/seen", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": window.HR_CSRF || "",
          "Content-Type": "application/json",
        },
        body: "{}",
      }).catch(() => {});
    };
    guideEl.addEventListener("hidden.bs.modal", markGuideSeen);
    if (guideEl.getAttribute("data-auto-show-guide") === "1") {
      const guideModal = new bootstrap.Modal(guideEl);
      guideModal.show();
    }
  }

  const loginErrorEl = qs("#loginErrorModal");
  if (loginErrorEl && window.bootstrap && loginErrorEl.getAttribute("data-auto-show-login-error") === "1") {
    new bootstrap.Modal(loginErrorEl).show();
  }

  document.querySelectorAll("[data-assign-picker]").forEach((picker) => {
    const search = qs("[data-assign-search]", picker);
    const summary = qs("[data-assign-summary]", picker);
    const checks = Array.from(picker.querySelectorAll('input[type="checkbox"][name="assigned_to"]'));
    const options = Array.from(picker.querySelectorAll("[data-assign-option]"));

    function updateSummary() {
      const selected = checks.filter((c) => c.checked).map((c) => c.getAttribute("data-user-label"));
      summary.textContent = selected.length ? selected.join(", ") : tr("Select employees");
    }

    checks.forEach((check) => check.addEventListener("change", updateSummary));
    if (search) {
      search.addEventListener("input", () => {
        const q = search.value.trim().toLowerCase();
        options.forEach((option) => {
          const name = option.getAttribute("data-user-name") || "";
          option.classList.toggle("d-none", q && !name.includes(q));
        });
      });
    }
    updateSummary();
  });
})();
