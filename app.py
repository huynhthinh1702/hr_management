import os
import re
from datetime import datetime, date
from zoneinfo import ZoneInfo

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func, inspect, or_, text
from sqlalchemy.orm import selectinload
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from services.realtime import (
    emit_global,
    emit_task_live,
    emit_task_removed,
    init_socketio,
    join_global_if_authenticated,
    join_task_room,
    leave_task_room,
)

from models.user import ROLE_HIERARCHY
from database import db
from models.activity_log import ActivityLog
from models.comment import Comment
from models.issue import Issue
from models.notification import Notification
from models.subtask import SubTask
from models.task import Task, task_users
from models.task_attachment import TaskAttachment
from models.user import User

app = Flask(__name__)
app.secret_key = "secret123"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "pdf", "doc", "docx", "xls", "xlsx", "txt", "zip"
}

ALLOWED_AVATAR_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "attachments"), exist_ok=True)
os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "avatars"), exist_ok=True)

db.init_app(app)

csrf = CSRFProtect(app)

socketio = init_socketio(app)

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
DEFAULT_RESET_PASSWORD = "Hr@12345"
VALID_ROLES = {"employee", "manager", "admin", "team_lead", "qa", "director"}
SUPPORTED_LANGUAGES = {"en", "vi"}

UI_TRANSLATIONS = {
    "en": {
        "Notifications": "Notifications",
        "No notifications.": "No notifications.",
        "Mark read": "Mark read",
        "Sidebar": "Sidebar",
        "Logout": "Logout",
        "Login": "Login",
        "Register": "Register",
        "Navigation": "Navigation",
        "Welcome": "Welcome",
        "Dashboard": "Dashboard",
        "Task & Issue Statistics": "Task & Issue Statistics",
        "Issue Resolution": "Issue Resolution",
        "Recent Issues": "Recent Issues",
        "Productivity by Employee": "Productivity by Employee",
        "Task Trend (Last 30 days)": "Task Trend (Last 30 days)",
        "Activity Heatmap": "Activity Heatmap",
        "Top 12": "Top 12",
        "By weekday/hour": "By weekday/hour",
        "Edit": "Edit",
        "Lock": "Lock",
        "Unlock": "Unlock",
        "Reset Password": "Reset Password",
        "Tasks": "Tasks",
        "Create Task": "Create Task",
        "Archived Tasks": "Archived Tasks",
        "Kanban Board": "Kanban Board",
        "Admin Users": "Admin Users",
        "Profile": "Profile",
        "User Guide": "User Guide",
        "Invalid Login": "Invalid Login",
        "The email or password is incorrect. Please try again.": "The email or password is incorrect. Please try again.",
        "Close": "Close",
        "Account Locked": "Account Locked",
        "Your account is locked. Please contact an administrator.": "Your account is locked. Please contact an administrator.",
        "Email": "Email",
        "Password": "Password",
        "Forgot password?": "Forgot password?",
        "Username already exists.": "Username already exists.",
        "Email already exists.": "Email already exists.",
        "Password must be at least 8 characters.": "Password must be at least 8 characters.",
        "Password must include an uppercase letter.": "Password must include an uppercase letter.",
        "Password must include a lowercase letter.": "Password must include a lowercase letter.",
        "Password must include a number.": "Password must include a number.",
        "Password must include a special character.": "Password must include a special character.",
        "Registration successful.": "Registration successful.",
        "Full name and email do not match an existing account.": "Full name and email do not match an existing account.",
        "Password reset request sent to admin.": "Password reset request sent to admin.",
        "Invalid role.": "Invalid role.",
        "User updated.": "User updated.",
        "You cannot lock your own account.": "You cannot lock your own account.",
        "Account status updated.": "Account status updated.",
        "You cannot delete your own account.": "You cannot delete your own account.",
        "User deleted.": "User deleted.",
        "Update request sent.": "Update request sent.",
        "Home - HR Management": "Home - HR Management",
        "Forgot Password": "Forgot Password",
        "Task List": "Task List",
        "Update Task": "Update Task",
        "Task Detail": "Task Detail",
        "Create Subtask": "Create Subtask",
        "Update Subtask": "Update Subtask",
        "Got it": "Got it",
        "At least 8 characters with uppercase, lowercase, number, and special character.": "At least 8 characters with uppercase, lowercase, number, and special character.",
        "Send Request": "Send Request",
        "Back to login": "Back to login",
        "Delete this user account?": "Delete this user account?",
        "Delete this task?": "Delete this task?",
        "Delete this subtask?": "Delete this subtask?",
        "Send delete request?": "Send delete request?",
        "Delete": "Delete",
        "Comment added.": "Comment added.",
        "Issue reported.": "Issue reported.",
        "Issue resolved.": "Issue resolved.",
        "Password reset request": "Password reset request",
        "requested a reset to the default password.": "requested a reset to the default password.",
        "Task assigned": "Task assigned",
        "You were assigned to '{task.title}'.": "You were assigned to '{task.title}'.",
        "Task completed": "Task completed",
        "was marked completed.": "was marked completed.",
        "Serious issue created": "Serious issue created",
        "issue on": "issue on",
        "Task overdue": "Task overdue",
        "is past its deadline": "is past its deadline",
        "Critical": "Critical",
        "High": "High",
        "Task": "Task",
        "created": "created",
        "updated": "updated",
        "archived": "archived",
        "deleted": "deleted",
        "Subtask": "Subtask",
    },
    "vi": {
        "Notifications": "Thông báo",
        "No notifications.": "Không có thông báo.",
        "Mark read": "Đánh dấu đã đọc",
        "Sidebar": "Thanh sidebar",
        "Logout": "Đăng xuất",
        "Login": "Đăng nhập",
        "Register": "Đăng ký",
        "Navigation": "Điều hướng",
        "Welcome": "Chào mừng",
        "Dashboard": "Bảng điều khiển",
        "Task & Issue Statistics": "Thống kê công việc và vấn đề",
        "Issue Resolution": "Xử lý vấn đề",
        "Recent Issues": "Vấn đề gần đây",
        "Productivity by Employee": "Hiệu suất theo nhân viên",
        "Task Trend (Last 30 days)": "Xu hướng công việc (30 ngày)",
        "Activity Heatmap": "Bản đồ hoạt động",
        "Top 12": "Top 12",
        "By weekday/hour": "Theo ngày trong tuần/giờ",
        "Edit": "Sửa",
        "Lock": "Khóa",
        "Unlock": "Mở khóa",
        "Reset Password": "Đặt lại mật khẩu",
        "Tasks": "Công việc",
        "Create Task": "Tạo công việc",
        "Archived Tasks": "Công việc lưu trữ",
        "Kanban Board": "Bảng Kanban",
        "Admin Users": "Quản lý người dùng",
        "Profile": "Hồ sơ",
        "User Guide": "Hướng dẫn",
        "Invalid Login": "Đăng nhập không thành công",
        "The email or password is incorrect. Please try again.": "Email hoặc mật khẩu không đúng. Vui lòng thử lại.",
        "Close": "Đóng",
        "Account Locked": "Tài khoản bị khóa",
        "Your account is locked. Please contact an administrator.": "Tài khoản của bạn đang bị khóa. Vui lòng liên hệ quản trị viên.",
        "Email": "Email",
        "Password": "Mật khẩu",
        "Forgot password?": "Quên mật khẩu?",
        "Username already exists.": "Tên đăng nhập đã tồn tại.",
        "Email already exists.": "Email đã tồn tại.",
        "Password must be at least 8 characters.": "Mật khẩu phải có ít nhất 8 ký tự.",
        "Password must include an uppercase letter.": "Mật khẩu phải có ít nhất một chữ hoa.",
        "Password must include a lowercase letter.": "Mật khẩu phải có ít nhất một chữ thường.",
        "Password must include a number.": "Mật khẩu phải có ít nhất một chữ số.",
        "Password must include a special character.": "Mật khẩu phải có ít nhất một ký tự đặc biệt.",
        "Registration successful.": "Đăng ký thành công.",
        "Full name and email do not match an existing account.": "Họ tên và email không khớp với tài khoản hiện có.",
        "Password reset request sent to admin.": "Đã gửi yêu cầu đặt lại mật khẩu tới quản trị viên.",
        "Invalid role.": "Vai trò không hợp lệ.",
        "User updated.": "Đã cập nhật người dùng.",
        "You cannot lock your own account.": "Bạn không thể khóa tài khoản của chính mình.",
        "Account status updated.": "Đã cập nhật trạng thái tài khoản.",
        "You cannot delete your own account.": "Bạn không thể xóa tài khoản của chính mình.",
        "User deleted.": "Đã xóa người dùng.",
        "Update request sent.": "Đã gửi yêu cầu cập nhật.",
        "Home - HR Management": "Trang chủ - Quản lý nhân sự",
        "Forgot Password": "Quên mật khẩu",
        "Task List": "Danh sách công việc",
        "Update Task": "Cập nhật công việc",
        "Task Detail": "Chi tiết công việc",
        "Create Subtask": "Tạo công việc con",
        "Update Subtask": "Cập nhật công việc con",
        "Got it": "Đã hiểu",
        "At least 8 characters with uppercase, lowercase, number, and special character.": "Ít nhất 8 ký tự gồm chữ hoa, chữ thường, số và ký tự đặc biệt.",
        "Send Request": "Gửi yêu cầu",
        "Back to login": "Quay lại đăng nhập",
        "Delete this user account?": "Xóa tài khoản người dùng này?",
        "Delete this task?": "Xóa công việc này?",
        "Delete this subtask?": "Xóa công việc con này?",
        "Send delete request?": "Gửi yêu cầu xóa?",
        "Delete": "Xóa",
        "Comment added.": "Đã thêm bình luận.",
        "Issue reported.": "Đã báo cáo sự cố.",
        "Issue resolved.": "Đã xử lý sự cố.",
        "Password reset request": "Yêu cầu đặt lại mật khẩu",
        "requested a reset to the default password.": "đã yêu cầu đặt lại về mật khẩu mặc định.",
        "Task assigned": "Công việc được giao",
        "You were assigned to '{task.title}'.": "Bạn đã được giao công việc '{task.title}'.",
        "Task completed": "Công việc đã hoàn thành",
        "was marked completed.": "đã được đánh dấu hoàn thành.",
        "Serious issue created": "Vấn đề nghiêm trọng đã được tạo",
        "issue on": "Xuất hiện vấn đề",
        "Task overdue": "Công việc quá hạn",
        "is past its deadline": "đã quá hạn",
        "Critical": "Nghiêm trọng",
        "High": "Cao",
        "Task": "Công việc",
        "created": "được tạo",
        "updated": "được cập nhật",
        "archived": "được lưu trữ",
        "deleted": "được xóa",
        "Subtask": "Công việc con",
    },
}


def current_language():
    lang = session.get("lang", "vi")
    return lang if lang in SUPPORTED_LANGUAGES else "vi"


def translate_ui(text):
    return UI_TRANSLATIONS.get(current_language(), UI_TRANSLATIONS["en"]).get(text, text)


def validate_password_strength(password):
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must include an uppercase letter.")
    if not re.search(r"[a-z]", password):
        errors.append("Password must include a lowercase letter.")
    if not re.search(r"\d", password):
        errors.append("Password must include a number.")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("Password must include a special character.")
    return errors


def username_exists(username, exclude_user_id=None):
    query = User.query.filter(func.lower(User.username) == username.lower())
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)
    return query.first() is not None


def email_exists(email, exclude_user_id=None):
    query = User.query.filter(func.lower(User.email) == email.lower())
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)
    return query.first() is not None


def as_vn_time(dt):
    """Convert naive UTC or aware datetime into aware VN datetime."""
    if not dt:
        return None
    if dt.tzinfo is None:
        # Existing DB stores naive UTC (datetime.utcnow). Treat as UTC.
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(VN_TZ)


def fmt_vn(dt, fmt="%Y-%m-%d %H:%M"):
    vndt = as_vn_time(dt)
    return vndt.strftime(fmt) if vndt else None


def parse_deadline(value):
    """Parse stored deadline string (YYYY-MM-DD) into date."""
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def is_overdue_task(task, today=None):
    if not task or not getattr(task, "deadline", None):
        return False
    if getattr(task, "status", None) == "Completed":
        return False
    d = parse_deadline(task.deadline)
    if not d:
        return False
    today = today or datetime.now(VN_TZ).date()
    return d < today


def notify_task_live(task_id, sections=None):
    emit_task_live(socketio, task_id, sections=sections)


def notify_task_removed(task_id):
    emit_task_removed(socketio, task_id)


def notify_global_change(kind="data_changed", task_id=None):
    emit_global(socketio, kind=kind, task_id=task_id)


def wants_json_response():
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
    )


def serialize_activity_page(task_id, page=1, per_page=5):
    pagination = ActivityLog.query.filter_by(task_id=task_id, subtask_id=None).order_by(
        ActivityLog.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return {
        "page": pagination.page,
        "pages": pagination.pages,
        "has_prev": pagination.has_prev,
        "has_next": pagination.has_next,
        "prev_num": pagination.prev_num,
        "next_num": pagination.next_num,
        "items": [
            {
                "action": a.action,
                "details": a.details,
                "actor_name": a.actor_name,
                "created_at": fmt_vn(a.created_at),
            }
            for a in pagination.items
        ],
    }


def serialize_task_live(task_id, sections=None, activity_page=1):
    task = Task.query.get(task_id)
    if not task:
        return None
    selected = set(sections or ["task", "subtasks", "comments", "attachments", "issues", "activities"])

    def dt_iso(dt):
        return fmt_vn(dt)

    payload = {}

    if "task" in selected:
        payload["task"] = {
            "id": task.id,
            "title": task.title,
            "description": task.description or "",
            "status": task.status,
            "progress": task.progress,
            "deadline": task.deadline,
            "priority": task.priority,
        }

    if "subtasks" in selected:
        subtasks = SubTask.query.filter_by(task_id=task_id).order_by(SubTask.id).all()
        payload["subtasks"] = [
            {
                "id": s.id,
                "title": s.title,
                "status": s.status,
                "progress": s.progress,
                "assigned_to": s.assigned_to,
                "assigned_name": (s.assigned_user.full_name or s.assigned_user.username) if s.assigned_user else "Unassigned",
            }
            for s in subtasks
        ]

    if "comments" in selected:
        comments = Comment.query.filter_by(task_id=task_id, subtask_id=None).order_by(Comment.created_at.desc()).all()
        payload["comments"] = [
            {
                "author_name": c.author_name,
                "content": c.content,
                "created_at": dt_iso(c.created_at),
            }
            for c in comments
        ]

    if "issues" in selected:
        issues = Issue.query.filter_by(task_id=task_id, subtask_id=None).order_by(Issue.created_at.desc()).all()
        payload["issues"] = [
            {
                "id": i.id,
                "title": i.title,
                "description": i.description or "",
                "severity": getattr(i, "severity", "Normal"),
                "status": i.status,
                "creator_name": i.creator_name,
                "created_at": dt_iso(i.created_at),
            }
            for i in issues
        ]

    if "attachments" in selected:
        attachments = TaskAttachment.query.filter_by(task_id=task_id, subtask_id=None).order_by(TaskAttachment.created_at.desc()).all()
        payload["attachments"] = [
            {
                "file_path": a.file_path,
                "original_filename": a.original_filename,
                "uploader_name": a.uploader_name,
            }
            for a in attachments
        ]

    if "activities" in selected:
        payload["activities"] = serialize_activity_page(task_id, page=activity_page)

    return payload


def serialize_subtask_live(subtask_id, sections=None, activity_page=1):
    subtask = SubTask.query.get(subtask_id)
    if not subtask:
        return None

    selected = set(sections or ["subtask", "comments", "attachments", "issues", "activities"])

    payload = {"task_id": subtask.task_id, "subtask_id": subtask.id}

    if "subtask" in selected:
        assigned = subtask.assigned_user
        payload["subtask"] = {
            "id": subtask.id,
            "task_id": subtask.task_id,
            "title": subtask.title,
            "status": subtask.status,
            "progress": subtask.progress,
            "assigned_to": subtask.assigned_to,
            "assigned_name": (assigned.full_name or assigned.username) if assigned else None,
        }

    if "comments" in selected:
        comments = (
            Comment.query.filter_by(task_id=subtask.task_id, subtask_id=subtask.id)
            .order_by(Comment.created_at.desc())
            .all()
        )
        payload["comments"] = [
            {
                "id": c.id,
                "author_name": c.author_name,
                "created_at": fmt_vn(c.created_at),
                "content": c.content,
            }
            for c in comments
        ]

    if "attachments" in selected:
        attachments = (
            TaskAttachment.query.filter_by(task_id=subtask.task_id, subtask_id=subtask.id)
            .order_by(TaskAttachment.created_at.desc())
            .all()
        )
        payload["attachments"] = [
            {
                "id": a.id,
                "original_filename": a.original_filename,
                "file_path": a.file_path,
                "uploader_name": a.uploader_name,
                "created_at": fmt_vn(a.created_at),
            }
            for a in attachments
        ]

    if "issues" in selected:
        issues = (
            Issue.query.filter_by(task_id=subtask.task_id, subtask_id=subtask.id)
            .order_by(Issue.created_at.desc())
            .all()
        )
        payload["issues"] = [
            {
                "id": i.id,
                "title": i.title,
                "description": i.description or "",
                "severity": i.severity,
                "status": i.status,
                "creator_name": i.creator_name,
                "created_at": fmt_vn(i.created_at),
            }
            for i in issues
        ]

    if "activities" in selected:
        pagination = (
            ActivityLog.query.filter_by(task_id=subtask.task_id, subtask_id=subtask.id)
            .order_by(ActivityLog.created_at.desc())
            .paginate(page=activity_page, per_page=5, error_out=False)
        )
        payload["activities"] = {
            "page": pagination.page,
            "pages": pagination.pages,
            "has_prev": pagination.has_prev,
            "has_next": pagination.has_next,
            "prev_num": pagination.prev_num,
            "next_num": pagination.next_num,
            "items": [
                {
                    "action": a.action,
                    "details": a.details,
                    "actor_name": a.actor_name,
                    "created_at": fmt_vn(a.created_at),
                }
                for a in pagination.items
            ],
        }

    return payload


def get_current_user():
    if "user_id" not in session:
        return None
    return User.query.get(session["user_id"])


def display_user_name(user):
    if not user:
        return ""
    return user.full_name or user.username


def create_notification(user_id, type_, title, message, task_id=None, url=None, actor_id=None, dedupe=False):
    if not user_id:
        return None
    if dedupe:
        exists = Notification.query.filter_by(
            user_id=user_id,
            type=type_,
            task_id=task_id,
        ).first()
        if exists:
            return exists
    notification = Notification(
        user_id=user_id,
        actor_id=actor_id,
        task_id=task_id,
        type=type_,
        title=title,
        message=message,
        url=url,
    )
    db.session.add(notification)
    return notification


def notify_task_assigned(task, users):
    actor_id = session.get("user_id")
    for user in users:
        if user.id == actor_id:
            continue
        create_notification(
            user.id,
            "task_assigned",
            translate_ui("Task assigned"),
            translate_ui("You were assigned to '{task.title}'.").format(task=task),
            task_id=task.id,
            url=f"/task/{task.id}",
            actor_id=actor_id,
            dedupe=True,
        )


def notify_task_completed(task):
    actor_id = session.get("user_id")
    recipient_ids = {u.id for u in (task.assigned_users or [])}
    if actor_id:
        recipient_ids.discard(actor_id)
    managers = User.query.filter(User.role.in_(["manager", "admin"])).all()
    recipient_ids.update(u.id for u in managers if u.id != actor_id)
    for user_id in recipient_ids:
        create_notification(
            user_id,
            "task_completed",
            translate_ui("Task completed"),
            translate_ui("'{task.title}' was marked completed.").format(task=task),
            task_id=task.id,
            url=f"/task/{task.id}",
            actor_id=actor_id,
            dedupe=True,
        )


def notify_serious_issue(task, issue):
    actor_id = session.get("user_id")
    recipient_ids = {u.id for u in (task.assigned_users or [])}
    managers = User.query.filter(User.role.in_(["manager", "admin"])).all()
    recipient_ids.update(u.id for u in managers)
    if actor_id:
        recipient_ids.discard(actor_id)
    for user_id in recipient_ids:
        create_notification(
            user_id,
            "serious_issue",
            translate_ui("Serious issue created"),
            f"{translate_ui(issue.severity)} issue on '{task.title}': {issue.title}",
            task_id=task.id,
            url=f"/task/{task.id}",
            actor_id=actor_id,
        )


def notify_overdue_tasks_for_user(user):
    if not user:
        return
    today = datetime.now(VN_TZ).date()
    if user.role in ["manager", "admin"]:
        tasks = Task.query.filter_by(is_deleted=False).options(selectinload(Task.assigned_users)).all()
    else:
        tasks = (
            Task.query.filter_by(is_deleted=False)
            .join(task_users)
            .filter(task_users.c.user_id == user.id)
            .options(selectinload(Task.assigned_users))
            .all()
        )
    for task in tasks:
        if is_overdue_task(task, today=today):
            create_notification(
                user.id,
                "task_overdue",
                translate_ui("Task overdue"),
                translate_ui("'{task.title}' is past its deadline ({task.deadline}).").format(task=task),
                task_id=task.id,
                url=f"/task/{task.id}",
                dedupe=True,
            )


def get_notification_summary(user_id):
    if not user_id:
        return {"unread_count": 0, "items": []}
    unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    items = (
        Notification.query.filter_by(user_id=user_id)
        .order_by(Notification.created_at.desc())
        .limit(8)
        .all()
    )
    return {"unread_count": unread_count, "items": items}


def serialize_notification(notification):
    return {
        "id": notification.id,
        "title": notification.title,
        "message": notification.message,
        "url": notification.url or "#",
        "is_read": bool(notification.is_read),
        "created_at": fmt_vn(notification.created_at),
    }


def ensure_schema():
    db.create_all()

    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    def column_names(table_name):
        if table_name not in tables:
            return set()
        return {column["name"] for column in inspector.get_columns(table_name)}

    user_columns = column_names("user")

    subtask_columns = column_names("sub_task")
    comment_columns = column_names("comment")
    issue_columns = column_names("issue")
    attachment_columns = column_names("task_attachment")
    activity_columns = column_names("activity_log")

    if "assigned_to" not in subtask_columns:
        db.session.execute(
            text(
                "ALTER TABLE sub_task ADD COLUMN assigned_to INTEGER"
            )
        )

    if "created_by" not in subtask_columns:
        db.session.execute(
            text(
                "ALTER TABLE sub_task ADD COLUMN created_by INTEGER"
            )
        )

    if "subtask_id" not in comment_columns:
        db.session.execute(
            text(
                "ALTER TABLE comment ADD COLUMN subtask_id INTEGER"
            )
        )

    if "subtask_id" not in issue_columns:
        db.session.execute(
            text(
                "ALTER TABLE issue ADD COLUMN subtask_id INTEGER"
            )
        )

    if "subtask_id" not in attachment_columns:
        db.session.execute(
            text(
                "ALTER TABLE task_attachment ADD COLUMN subtask_id INTEGER"
            )
        )

    if "subtask_id" not in activity_columns:
        db.session.execute(
            text(
                "ALTER TABLE activity_log ADD COLUMN subtask_id INTEGER"
            )
        )

    if "is_locked" not in user_columns:
        db.session.execute(
            text('ALTER TABLE "user" ADD COLUMN is_locked BOOLEAN DEFAULT 0')
        )

    if "has_seen_guide" not in user_columns:
        db.session.execute(
            text('ALTER TABLE "user" ADD COLUMN has_seen_guide BOOLEAN DEFAULT 0')
        )

    if "severity" not in issue_columns:
        db.session.execute(
            text(
                "ALTER TABLE issue ADD COLUMN severity VARCHAR(30) DEFAULT 'Normal' NOT NULL"
            )
        )

    # =========================
    # CREATE DEFAULT ADMIN
    # =========================

    admin_exists = User.query.filter_by(
        username="admin"
    ).first()

    if not admin_exists:

        admin = User(
            username="admin",
            full_name="admin",
            email="admin@gmail.com",
            password=generate_password_hash("Admin@123"),
            role="admin"
        )

        db.session.add(admin)

    db.session.commit()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_avatar_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_AVATAR_EXTENSIONS


def is_allowed_mimetype(mimetype, allowed_set):
    return bool(mimetype) and mimetype in allowed_set


def log_activity(task_id, action, details):
    if "user_id" not in session:
        return
    activity = ActivityLog(
        task_id=task_id,
        subtask_id=None,
        user_id=session["user_id"],
        actor_name=session.get("username", "Unknown"),
        action=action,
        details=details
    )
    db.session.add(activity)


def log_subtask_activity(task_id, subtask_id, action, details):
    if "user_id" not in session:
        return
    activity = ActivityLog(
        task_id=task_id,
        subtask_id=subtask_id,
        user_id=session["user_id"],
        actor_name=session.get("username", "Unknown"),
        action=action,
        details=details,
    )
    db.session.add(activity)


@app.context_processor
def inject_global_data():
    current_user = get_current_user()
    if current_user:
        notify_overdue_tasks_for_user(current_user)
        db.session.commit()
    return {
        "current_user": current_user,
        "fmt_vn": fmt_vn,
        "is_overdue_task": is_overdue_task,
        "display_user_name": display_user_name,
        "notification_summary": get_notification_summary(current_user.id if current_user else None),
        "show_user_guide": bool(current_user and not current_user.has_seen_guide),
        "current_lang": current_language(),
        "supported_languages": SUPPORTED_LANGUAGES,
        "_": translate_ui,
    }


@app.template_filter("vn_time")
def vn_time_filter(dt, fmt="%Y-%m-%d %H:%M"):
    return fmt_vn(dt, fmt=fmt)


def scoped_task_query():
    base_query = Task.query.filter_by(is_deleted=False)

    if session.get("role") in ["manager", "admin", "director", "team_lead", "qa"]:
        return base_query
    current_user = User.query.get(session["user_id"])
    return base_query.join(task_users).filter(
        task_users.c.user_id == current_user.id
    )


def task_accessible_for_session(task_id):
    if "user_id" not in session:
        return False
    return scoped_task_query().filter(Task.id == task_id).first() is not None


def subtask_accessible_for_session(subtask_id):
    if "user_id" not in session:
        return False
    subtask = SubTask.query.get(subtask_id)
    if not subtask:
        return False
    # Users who can access the parent task can access its subtasks.
    if task_accessible_for_session(subtask.task_id):
        return True
    # Assigned user can always access their subtask.
    if subtask.assigned_to and int(subtask.assigned_to) == int(session.get("user_id")):
        return True
    # Subtask creator can always access it.
    if subtask.created_by and int(subtask.created_by) == int(session.get("user_id")):
        return True
    return False


def admin_required():
    return "user_id" in session and session.get("role") == "admin"


@socketio.on("join_task")
def on_join_task(data):
    task_id = (data or {}).get("task_id")
    if not task_id:
        return
    if not task_accessible_for_session(task_id):
        return
    join_task_room(task_id)


@socketio.on("leave_task")
def on_leave_task(data):
    task_id = (data or {}).get("task_id")
    if task_id:
        leave_task_room(task_id)


@socketio.on("connect")
def on_connect():
    # Only authenticated sessions can join global room.
    join_global_if_authenticated(session)


@app.route("/api/task/<int:task_id>/live", methods=["GET"])
def api_task_live(task_id):
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401
    if not task_accessible_for_session(task_id):
        return jsonify({"error": "not found"}), 404
    section_arg = request.args.get("sections", "")
    allowed_sections = {"task", "subtasks", "comments", "attachments", "issues", "activities"}
    sections = [
        s.strip()
        for s in section_arg.split(",")
        if s.strip() in allowed_sections
    ] or None
    activity_page = request.args.get("activity_page", 1, type=int)
    payload = serialize_task_live(task_id, sections=sections, activity_page=activity_page)
    if payload is None:
        return jsonify({"error": "not found"}), 404
    if not section_arg and isinstance(payload.get("activities"), dict):
        payload["activities"] = payload["activities"].get("items", [])
    return jsonify(payload)


@app.route("/api/subtask/<int:subtask_id>/live", methods=["GET"])
def api_subtask_live(subtask_id):
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401
    if not subtask_accessible_for_session(subtask_id):
        return jsonify({"error": "not found"}), 404

    section_arg = request.args.get("sections", "")
    allowed_sections = {"subtask", "comments", "attachments", "issues", "activities"}
    sections = [s.strip() for s in section_arg.split(",") if s.strip() in allowed_sections] or None
    activity_page = request.args.get("activity_page", 1, type=int)

    payload = serialize_subtask_live(subtask_id, sections=sections, activity_page=activity_page)
    if payload is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(payload)


@app.route("/api/dashboard/summary", methods=["GET"])
def api_dashboard_summary():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401
    
    current_user_id = session["user_id"]
    
    # TASKS

    tasks = scoped_task_query().all()
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == "Completed")
    pending_tasks = total_tasks - completed_tasks

    # SUBTASKS (only active ones, parent task not deleted)

    subtasks = SubTask.query.filter(
        SubTask.assigned_to == current_user_id
    ).all()
    subtasks = [s for s in subtasks if Task.query.get(s.task_id) and not Task.query.get(s.task_id).is_deleted]

    subtask_total = len(subtasks)
    subtask_completed = sum(1 for s in subtasks if s.status == "Completed")
    subtask_pending = subtask_total - subtask_completed

    # FINAL TASK COUNTS

    total_tasks = total_tasks + subtask_total
    completed_tasks = completed_tasks + subtask_completed
    pending_tasks = pending_tasks + subtask_pending

    # ISSUES (only from existing tasks/subtasks, exclude orphaned)

    task_ids = [t.id for t in tasks]
    subtask_ids = [s.id for s in subtasks]
    if task_ids or subtask_ids:
        issue_query = Issue.query.filter(
            db.or_(
                Issue.task_id.in_(task_ids) if task_ids else False,
                Issue.subtask_id.in_(subtask_ids) if subtask_ids else False  
            )
        )
        total_issues = issue_query.count()
        resolved_issues = issue_query.filter(
            Issue.status == "Resolved"
        ).count()
        recent_issues = (
            issue_query.order_by(Issue.created_at.desc())
            .limit(6)
            .all()
        )
    else:
        total_issues = 0
        resolved_issues = 0
        recent_issues = []

    unresolved_issues = total_issues - resolved_issues
    issue_resolution_rate = int((resolved_issues / total_issues) * 100) if total_issues else 0

    return jsonify({
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "total_issues": total_issues,
        "resolved_issues": resolved_issues,
        "unresolved_issues": unresolved_issues,
        "issue_resolution_rate": issue_resolution_rate,
        "recent_issues": [
            {
                "id": i.id,
                "title": i.title,
                "status": i.status,
                "creator_name": i.creator_name,
            }
            for i in recent_issues
        ]
    })


@app.route("/api/dashboard/analytics", methods=["GET"])
def api_dashboard_analytics():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    tasks = scoped_task_query().options(selectinload(Task.assigned_users)).all()
    today_date = datetime.now(VN_TZ).date()
    total = len(tasks)
    overdue = sum(1 for t in tasks if is_overdue_task(t, today=today_date))
    overdue_rate = int((overdue / total) * 100) if total else 0

    # Also fetch all subtasks to include subtask assignee productivity
    all_subtasks = SubTask.query.all()
    active_subtasks = [s for s in all_subtasks if Task.query.get(s.task_id) and not Task.query.get(s.task_id).is_deleted]

    # Productivity by employee (assigned tasks completed)
    prod = {}
    for t in tasks:
        for u in (t.assigned_users or []):
            label = display_user_name(u)
            prod.setdefault(label, {"username": label, "completed": 0, "total": 0})
            prod[label]["total"] += 1
            if t.status == "Completed":
                prod[label]["completed"] += 1

    # Also count subtask assignee productivity
    for s in active_subtasks:
        if s.assigned_user:
            label = display_user_name(s.assigned_user)
            prod.setdefault(label, {"username": label, "completed": 0, "total": 0})
            prod[label]["total"] += 1
            if s.status == "Completed":
                prod[label]["completed"] += 1

    productivity = sorted(prod.values(), key=lambda x: (-x["completed"], -x["total"], x["username"]))[:12]

    # Task trend by day (based on ActivityLog)
    task_ids = [t.id for t in tasks]
    if task_ids:
        created_logs = ActivityLog.query.filter(
            ActivityLog.task_id.in_(task_ids),
            ActivityLog.action == "Created task",
        ).all()
        moved_logs = ActivityLog.query.filter(
            ActivityLog.task_id.in_(task_ids),
            ActivityLog.action.in_(["Updated task", "Moved task on kanban"]),
        ).all()
    else:
        created_logs = []
        moved_logs = []

    def day_key(dt):
        return dt.strftime("%Y-%m-%d")

    created_per_day = {}
    completed_per_day = {}
    for log in created_logs:
        k = day_key(log.created_at)
        created_per_day[k] = created_per_day.get(k, 0) + 1
    for log in moved_logs:
        if "Completed" in (log.details or ""):
            k = day_key(log.created_at)
            completed_per_day[k] = completed_per_day.get(k, 0) + 1

    all_days = sorted(set(created_per_day.keys()) | set(completed_per_day.keys()))
    trend = {
        "labels": all_days[-30:],
        "created": [created_per_day.get(d, 0) for d in all_days[-30:]],
        "completed": [completed_per_day.get(d, 0) for d in all_days[-30:]],
    }

    # Heatmap: activities count by weekday and hour
    heat = [[0 for _ in range(24)] for _ in range(7)]
    logs = []
    if task_ids:
        logs = ActivityLog.query.filter(ActivityLog.task_id.in_(task_ids)).all()
    for log in logs:
        wd = int(log.created_at.strftime("%w"))  # 0=Sun..6=Sat
        hr = int(log.created_at.strftime("%H"))
        heat[wd][hr] += 1

    return jsonify({
        "overdue": {"count": overdue, "total": total, "rate": overdue_rate},
        "productivity": productivity,
        "trend": trend,
        "heatmap": {
            "weekday_labels": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            "hours": list(range(24)),
            "matrix": heat,
        },
    })


@app.route("/api/kanban/columns", methods=["GET"])
def api_kanban_columns():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    if session["role"] in ["manager", "admin", "director", "team_lead", "qa"]:
        pending_tasks = Task.query.filter_by(status="Pending").all()
        progress_tasks = Task.query.filter_by(status="In Progress").all()
        completed_tasks = Task.query.filter_by(status="Completed").all()
    else:
        current_user = User.query.get(session["user_id"])
        pending_tasks = Task.query.join(task_users).filter(
            task_users.c.user_id == current_user.id,
            Task.status == "Pending"
        ).all()
        progress_tasks = Task.query.join(task_users).filter(
            task_users.c.user_id == current_user.id,
            Task.status == "In Progress"
        ).all()
        completed_tasks = Task.query.join(task_users).filter(
            task_users.c.user_id == current_user.id,
            Task.status == "Completed"
        ).all()

    def serialize_task_card(t):
        return {
            "id": t.id,
            "title": t.title or "",
            "description": t.description or "",
            "progress": t.progress or 0,
            "status": t.status,
        }

    return jsonify({
        "pending": [serialize_task_card(t) for t in pending_tasks],
        "progress": [serialize_task_card(t) for t in progress_tasks],
        "completed": [serialize_task_card(t) for t in completed_tasks],
    })


@app.route("/api/tasks/table", methods=["GET"])
def api_tasks_table():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    search = request.args.get("search", "")
    status = request.args.get("status", "")
    page = request.args.get("page", 1, type=int)

    query = scoped_task_query()
    if search:
        query = query.filter(Task.title.ilike(f"%{search}%"))
    if status:
        query = query.filter(Task.status == status)

    pagination = (
        query.options(selectinload(Task.assigned_users))
        .order_by(Task.id.desc())
        .paginate(page=page, per_page=8, error_out=False)
    )
    tasks = pagination.items
    today = datetime.now(VN_TZ).date()

    current_user_role = session.get("role")
    current_user_id = session.get("user_id")

    def can_update_task(task_obj):
        role = current_user_role
        if role in ["admin", "manager", "director", "team_lead"]:
            return True
        if role == "qa":
            return True
        return False

    def can_delete_task(task_obj):
        role = current_user_role
        if role in ["admin", "manager", "director", "team_lead"]:
            return True
        return False

    def serialize_row(t):
        d = parse_deadline(t.deadline)
        return {
            "id": t.id,
            "title": t.title or "",
            "status": t.status,
            "priority": t.priority,
            "progress": t.progress or 0,
            "deadline": d.strftime("%Y-%m-%d") if d else (t.deadline or ""),
            "is_overdue": is_overdue_task(t, today=today),
            "delete_request_status": t.delete_request_status,
            "can_update": can_update_task(t),
            "can_delete": can_delete_task(t),
            "assigned_users": [{"username": u.username, "full_name": display_user_name(u)} for u in (t.assigned_users or [])],
            "is_subtask": False,
            "subtask_id": None,
            "subtask_assigned_name": None,
        }

    # Also fetch subtasks assigned to current user (matching server-side /tasks behavior)
    # IMPORTANT: exclude subtasks whose parent task is deleted (archived)
    assigned_subtasks = SubTask.query.filter_by(
        assigned_to=session.get("user_id")
    ).options(selectinload(SubTask.assigned_user)).all()
    active_subtask_ids = []
    for s in assigned_subtasks:
        pt = Task.query.get(s.task_id)
        if pt and not pt.is_deleted:
            active_subtask_ids.append(s.id)
    assigned_subtasks = [s for s in assigned_subtasks if s.id in active_subtask_ids]

    subtask_rows = []
    for s in assigned_subtasks:
        parent_task = Task.query.get(s.task_id)
        subtask_rows.append({
            "id": s.id,
            "title": s.title,
            "status": s.status,
            "priority": "",
            "progress": s.progress or 0,
            "deadline": "",
            "is_overdue": False,
            "delete_request_status": None,
            "can_update": True,
            "can_delete": False,
            "assigned_users": [{"username": s.assigned_user.username if s.assigned_user else "", "full_name": (s.assigned_user.full_name or s.assigned_user.username) if s.assigned_user else ""}],
            "is_subtask": True,
            "subtask_id": s.id,
            "subtask_assigned_name": (s.assigned_user.full_name or s.assigned_user.username) if s.assigned_user else "Unassigned",
        })

    return jsonify({
        "today": today.strftime("%Y-%m-%d"),
        "page": pagination.page,
        "pages": pagination.pages,
        "has_prev": pagination.has_prev,
        "has_next": pagination.has_next,
        "tasks": [serialize_row(t) for t in tasks],
        "subtasks": subtask_rows,
    })


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/language/<lang>", methods=["POST"])
def set_language(lang):
    if lang not in SUPPORTED_LANGUAGES:
        abort(404)
    session["lang"] = lang
    if wants_json_response():
        return jsonify({"language": lang})
    return redirect(request.referrer or url_for("home"))


@app.route("/api/notifications", methods=["GET"])
def api_notifications():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401
    summary = get_notification_summary(session["user_id"])
    return jsonify({
        "unread_count": summary["unread_count"],
        "items": [serialize_notification(item) for item in summary["items"]],
    })

# Đăng ký
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        if username_exists(username):
            flash("Username already exists.")
            return render_template("register.html")
        if email_exists(email):
            flash("Email already exists.")
            return render_template("register.html")
        password_errors = validate_password_strength(password)
        if password_errors:
            for error in password_errors:
                flash(error)
            return render_template("register.html")

        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            role="employee",
            full_name=full_name
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful")
        return redirect("/login")
    return render_template("register.html")

# Đăng nhập
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            if user.is_locked:
                return render_template("login.html", login_error="locked")
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role

            return redirect("/dashboard")
        return render_template("login.html", login_error="invalid")

    return render_template("login.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        user = User.query.filter(func.lower(User.email) == email.lower()).first()

        if not user or (user.full_name or "").strip().lower() != full_name.lower():
            flash("Full name and email do not match an existing account.")
            return render_template("forgot_password.html")

        admins = User.query.filter_by(role="admin").all()
        for admin_user in admins:
            create_notification(
                admin_user.id,
                "password_reset_request",
                translate_ui("Password reset request"),
                f"{user.full_name or user.username} ({user.email}) {translate_ui('requested a reset to the default password.')}",
                url="/admin/users",
                actor_id=user.id,
            )
        db.session.commit()
        notify_global_change(kind="notification_created")
        flash("Password reset request sent to admin.")
        return redirect("/login")

    return render_template("forgot_password.html")


# Đăng xuất
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# Dashboard
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    current_user_id = session["user_id"]

    # TASKS

    tasks = scoped_task_query().options(
        selectinload(Task.assigned_users)
    ).all()

    task_total = len(tasks)

    task_completed = sum(
        1 for t in tasks
        if t.status == "Completed"
    )

    task_pending = task_total - task_completed

    # SUBTASKS (only active ones, parent task not deleted)

    subtasks = SubTask.query.filter(
        SubTask.assigned_to == current_user_id
    ).all()
    subtasks = [s for s in subtasks if Task.query.get(s.task_id) and not Task.query.get(s.task_id).is_deleted]

    subtask_total = len(subtasks)

    subtask_completed = sum(
        1 for s in subtasks
        if s.status == "Completed"
    )

    subtask_pending = subtask_total - subtask_completed

    # FINAL COUNTS

    total_tasks = task_total + subtask_total
    completed_tasks = task_completed + subtask_completed
    pending_tasks = task_pending + subtask_pending

    # ISSUES (only from existing tasks/subtasks, exclude orphaned)

    task_ids = [t.id for t in tasks]
    subtask_ids = [s.id for s in subtasks]

    if task_ids or subtask_ids:
        issue_query = Issue.query.filter(
            db.or_(
                Issue.task_id.in_(task_ids) if task_ids else False,
                Issue.subtask_id.in_(subtask_ids) if subtask_ids else False
            )
        )

        total_issues = issue_query.count()

        resolved_issues = issue_query.filter(
            Issue.status == "Resolved"
        ).count()

        recent_issues = (
            issue_query
            .order_by(Issue.created_at.desc())
            .limit(6)
            .all()
        )
        # Also filter recent issues: exclude issues belonging to deleted subtasks
        recent_issues = [i for i in recent_issues if not i.subtask_id or (SubTask.query.get(i.subtask_id) is not None and Task.query.get(i.task_id) and not Task.query.get(i.task_id).is_deleted)]
    else:
        total_issues = 0
        resolved_issues = 0
        recent_issues = []

    unresolved_issues = total_issues - resolved_issues
    issue_resolution_rate = (
        int((resolved_issues / total_issues) * 100)
        if total_issues else 0
    )

    return render_template(
        "dashboard.html",
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        total_issues=total_issues,
        resolved_issues=resolved_issues,
        unresolved_issues=unresolved_issues,
        issue_resolution_rate=issue_resolution_rate,
        recent_issues=recent_issues
    )


# admin
@app.route("/admin")
def admin():
    if "user_id" not in session:
        return redirect("/login")
    if session["role"] != "admin":
        return "Access Deinied"
    return redirect("/admin/users")


@app.route("/admin/users")
def admin_users():
    if "user_id" not in session:
        return redirect("/login")
    
    if not admin_required():
        return "Access Deinied"

    search = request.args.get("search", "").strip()
    role = request.args.get("role", "").strip()
    status = request.args.get("status", "").strip()
    page = request.args.get("page", 1, type=int)
    query = User.query

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                User.full_name.ilike(pattern),
                User.username.ilike(pattern),
                User.email.ilike(pattern),
            )
        )
    if role:
        query = query.filter(User.role == role)
    if status == "locked":
        query = query.filter(User.is_locked.is_(True))
    elif status == "active":
        query = query.filter(or_(User.is_locked.is_(False), User.is_locked.is_(None)))

    pagination = query.order_by(User.id.desc()).paginate(page=page, per_page=10, error_out=False)

    users = pagination.items
    return render_template("admin_users.html", users=users, pagination=pagination)


@app.route("/admin/users/<int:user_id>/edit", methods=["POST"])
def admin_edit_user(user_id):
    if "user_id" not in session:
        return redirect("/login")
    if not admin_required():
        return "Access Deinied"
    user = User.query.get_or_404(user_id)
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    role = request.form.get("role", user.role)

    if username_exists(username, exclude_user_id=user.id):
        flash("Username already exists.")
        return redirect(request.referrer or "/admin/users")
    if email_exists(email, exclude_user_id=user.id):
        flash("Email already exists.")
        return redirect(request.referrer or "/admin/users")
    if role not in VALID_ROLES:
        flash("Invalid role.")
        return redirect(request.referrer or "/admin/users")

    user.full_name = request.form.get("full_name", "").strip()
    user.username = username
    user.email = email
    user.role = role
    db.session.commit()
    flash("User updated.")
    return redirect(request.referrer or "/admin/users")


@app.route("/admin/users/<int:user_id>/toggle-lock", methods=["POST"])
def admin_toggle_lock_user(user_id):
    if "user_id" not in session:
        return redirect("/login")
    if not admin_required():
        return "Access Deinied"
    user = User.query.get_or_404(user_id)
    if user.id == session["user_id"]:
        flash("You cannot lock your own account.")
        return redirect("/admin/users")
    user.is_locked = not bool(user.is_locked)
    db.session.commit()
    flash("Account status updated.")
    return redirect(request.referrer or "/admin/users")


@app.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
def admin_reset_user_password(user_id):
    if "user_id" not in session:
        return redirect("/login")
    if not admin_required():
        return "Access Deinied"
    user = User.query.get_or_404(user_id)
    user.password = generate_password_hash(DEFAULT_RESET_PASSWORD)
    db.session.commit()
    flash(f"Password reset for {user.username}. Default password: {DEFAULT_RESET_PASSWORD}")
    return redirect(request.referrer or "/admin/users")


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
def admin_delete_user(user_id):
    if "user_id" not in session:
        return redirect("/login")
    if not admin_required():
        return "Access Deinied"
    user = User.query.get_or_404(user_id)
    if user.id == session["user_id"]:
        flash("You cannot delete your own account.")
        return redirect("/admin/users")
    db.session.delete(user)
    db.session.commit()
    flash("User deleted.")
    return redirect("/admin/users")

# Tạo task
@app.route("/create-task", methods=["GET", "POST"])
def create_task():
    if "user_id" not in session:
        return redirect("/login")
    if session["role"] not in ["manager", "director","team_lead"]:
        return "Access Denied"

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        assigned_user_ids = request.form.getlist("assigned_to")
        deadline = request.form["deadline"]
        priority = request.form["priority"]

        new_task = Task(
            title=title,
            description=description,
            status="Pending",
            progress=0,
            deadline=deadline,
            priority=priority
        )

        users = User.query.filter(
            User.id.in_(assigned_user_ids)
        ).all()

        new_task.assigned_users = users

        db.session.add(new_task)
        db.session.flush()
        notify_task_assigned(new_task, users)
        log_activity(
            task_id=new_task.id,
            action=translate_ui("Created task"),
            details=f"{translate_ui('Task')} '{new_task.title}' {translate_ui('created')}"
        )
        db.session.commit()
        notify_task_live(new_task.id)
        notify_global_change(kind="task_created", task_id=new_task.id)

        return redirect(f"/task/{new_task.id}")

    current_role = session.get("role")

    users = [
        user for user in User.query.all()
        if ROLE_HIERARCHY.get(current_role, 0) 
        > ROLE_HIERARCHY.get(user.role, 0)
    ]

    return render_template("create_task.html", users=users)

# task detail
@app.route("/task/<int:id>")
def task_detail(id):
    if "user_id" not in session:
        return redirect("/login")

    task = scoped_task_query().filter(Task.id == id).first()
    if not task:
        return redirect("/tasks")

    subtasks = SubTask.query.filter_by(task_id=id).all()
    comments = Comment.query.filter_by(task_id=id, subtask_id=None).order_by(Comment.created_at.desc()).all()
    activity_page = request.args.get("activity_page", 1, type=int)
    activity_pagination = ActivityLog.query.filter_by(task_id=id, subtask_id=None).order_by(
        ActivityLog.created_at.desc()
    ).paginate(page=activity_page, per_page=5, error_out=False)
    attachments = TaskAttachment.query.filter_by(task_id=id, subtask_id=None).order_by(TaskAttachment.created_at.desc()).all()
    issues = Issue.query.filter_by(task_id=id, subtask_id=None).order_by(Issue.created_at.desc()).all()

    return render_template(
        "task_detail.html",
        task=task,
        subtasks=subtasks,
        comments=comments,
        activities=activity_pagination.items,
        activity_pagination=activity_pagination,
        attachments=attachments,
        issues=issues
    )

@app.route("/task/<int:task_id>/comment", methods=["POST"])
def add_comment(task_id):
    if "user_id" not in session:
        if wants_json_response():
            return jsonify({"error": "unauthorized"}), 401
        return redirect("/login")
    if not task_accessible_for_session(task_id):
        if wants_json_response():
            return jsonify({"error": "not found"}), 404
        return redirect("/tasks")

    content = request.form["content"].strip()
    if not content:
        if wants_json_response():
            return jsonify({"error": "Comment content is required."}), 400
        return redirect(f"/task/{task_id}")

    comment = Comment(
        task_id=task_id,
        subtask_id=None,
        user_id=session["user_id"],
        author_name=session["username"],
        content=content
    )
    db.session.add(comment)
    log_activity(task_id,  translate_ui("Added comment"), content[:120])
    db.session.commit()
    sections = ["comments", "activities"]
    notify_task_live(task_id, sections=sections)
    notify_global_change(kind="task_updated", task_id=task_id)
    if wants_json_response():
        return jsonify({
            "message": "Comment added.",
            "sections": sections,
            "payload": serialize_task_live(task_id, sections=sections),
        })
    return redirect(f"/task/{task_id}")


@app.route("/task/<int:task_id>/issues", methods=["POST"])
def create_issue(task_id):
    if "user_id" not in session:
        if wants_json_response():
            return jsonify({"error": "unauthorized"}), 401
        return redirect("/login")
    if not task_accessible_for_session(task_id):
        if wants_json_response():
            return jsonify({"error": "not found"}), 404
        return redirect("/tasks")

    title = request.form["title"].strip()
    description = request.form["description"].strip()
    severity = request.form.get("severity", "Normal")
    if not title:
        if wants_json_response():
            return jsonify({"error": "Issue title is required."}), 400
        return redirect(f"/task/{task_id}")

    issue = Issue(
        title=title,
        description=description,
        severity=severity,
        status="Open",
        task_id=task_id,
        subtask_id=None,
        created_by=session["user_id"],
        creator_name=session["username"]
    )
    db.session.add(issue)
    log_activity(task_id, translate_ui("Created issue"), title)
    task = Task.query.get(task_id)
    if task and severity in ["High", "Critical"]:
        notify_serious_issue(task, issue)
    db.session.commit()
    sections = ["issues", "activities"]
    notify_task_live(task_id, sections=sections)
    notify_global_change(kind="task_updated", task_id=task_id)
    if wants_json_response():
        return jsonify({
            "message": "Issue reported.",
            "sections": sections,
            "payload": serialize_task_live(task_id, sections=sections),
        })
    return redirect(f"/task/{task_id}")


@app.route("/issues/<int:issue_id>/resolve", methods=["POST"])
def resolve_issue(issue_id):
    if "user_id" not in session:
        if wants_json_response():
            return jsonify({"error": "unauthorized"}), 401
        return redirect("/login")
    issue = Issue.query.get(issue_id)
    if not issue:
        if wants_json_response():
            return jsonify({"error": "not found"}), 404
        return redirect("/tasks")
    if issue.subtask_id:
        if not subtask_accessible_for_session(issue.subtask_id):
            if wants_json_response():
                return jsonify({"error": "not found"}), 404
            return redirect("/tasks")
    elif not task_accessible_for_session(issue.task_id):
        if wants_json_response():
            return jsonify({"error": "not found"}), 404
        return redirect("/tasks")

    issue.status = "Resolved"
    issue.resolved_at = datetime.utcnow()
    log_activity(issue.task_id, translate_ui("Resolved issue"), issue.title)
    db.session.commit()
    socketio.emit("global_changed", {"type": "issue_resolved"})
    sections = ["issues", "activities"]
    notify_task_live(issue.task_id, sections=sections)
    notify_global_change(kind="task_updated", task_id=issue.task_id)
    if wants_json_response():
        return jsonify({
            "message": "Issue resolved.",
            "sections": sections,
            "payload": serialize_task_live(issue.task_id, sections=sections),
        })
    return redirect(f"/task/{issue.task_id}")


@app.route("/task/<int:task_id>/upload", methods=["POST"])
def upload_task_file(task_id):
    if "user_id" not in session:
        return redirect("/login")
    if not task_accessible_for_session(task_id):
        return redirect("/tasks")

    if "file" not in request.files:
        return redirect(f"/task/{task_id}")

    uploaded_file = request.files["file"]
    if not uploaded_file.filename:
        return redirect(f"/task/{task_id}")

    if not allowed_file(uploaded_file.filename):
        return "File type is not supported"

    # Size check (MAX_CONTENT_LENGTH already enforced globally)
    if request.content_length and request.content_length > app.config.get("MAX_CONTENT_LENGTH", 0):
        return "File too large"

    allowed_mimes = {
        "image/png",
        "image/jpeg",
        "image/gif",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain",
        "application/zip",
        "application/x-zip-compressed",
    }
    if not is_allowed_mimetype(uploaded_file.mimetype, allowed_mimes):
        return "File type is not supported"

    safe_name = secure_filename(uploaded_file.filename)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    stored_name = f"{task_id}_{timestamp}_{safe_name}"
    absolute_path = os.path.join(app.config["UPLOAD_FOLDER"], "attachments", stored_name)
    uploaded_file.save(absolute_path)

    attachment = TaskAttachment(
        task_id=task_id,
        subtask_id=None,
        uploaded_by=session["user_id"],
        uploader_name=session["username"],
        original_filename=safe_name,
        stored_filename=stored_name,
        file_path=f"attachments/{stored_name}",
        file_size=os.path.getsize(absolute_path),
        mime_type=uploaded_file.mimetype
    )
    db.session.add(attachment)
    log_activity(task_id, translate_ui("Uploaded file"), safe_name)
    db.session.commit()
    notify_task_live(task_id)
    notify_global_change(kind="task_updated", task_id=task_id)

    return redirect(f"/task/{task_id}")


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    if "user_id" not in session:
        return redirect("/login")

    # Protect uploads from URL guessing:
    # - attachments: must belong to a task the current session can access
    # - avatars: only allow current user avatar
    if filename.startswith("attachments/"):
        attachment = TaskAttachment.query.filter(TaskAttachment.file_path == filename).first()
        if not attachment:
            abort(404)
        if attachment.subtask_id:
            if not subtask_accessible_for_session(int(attachment.subtask_id)):
                abort(403)
        else:
            if not task_accessible_for_session(attachment.task_id):
                abort(403)
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)

    if filename.startswith("avatars/"):
        user = get_current_user()
        if not user or user.avatar_path != filename:
            abort(403)
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=False)

    abort(404)


@app.route("/profile/avatar", methods=["POST"])
def upload_avatar():
    if "user_id" not in session:
        return redirect("/login")

    if "avatar" not in request.files:
        return redirect("/dashboard")
    avatar = request.files["avatar"]
    if not avatar.filename:
        return redirect("/dashboard")
    if not allowed_avatar_file(avatar.filename):
        return "Avatar type is not supported"

    allowed_avatar_mimes = {"image/png", "image/jpeg", "image/gif"}
    if not is_allowed_mimetype(avatar.mimetype, allowed_avatar_mimes):
        return "Avatar type is not supported"

    extension = secure_filename(avatar.filename).rsplit(".", 1)[1].lower()
    stored_name = f"user_{session['user_id']}.{extension}"
    avatar_path = os.path.join(app.config["UPLOAD_FOLDER"], "avatars", stored_name)
    avatar.save(avatar_path)

    user = User.query.get(session["user_id"])
    user.avatar_path = f"avatars/{stored_name}"
    db.session.commit()
    return redirect("/profile")


@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()

        if username_exists(username, exclude_user_id=user.id):
            flash("Username already exists.")
            return redirect("/profile")
        if email_exists(email, exclude_user_id=user.id):
            flash("Email already exists.")
            return redirect("/profile")

        user.username = username
        user.email = email
        user.full_name = request.form.get("full_name", "").strip()
        user.bio = request.form.get("bio", "").strip()
        session["username"] = user.username
        db.session.commit()
        return redirect("/profile")

    return render_template("profile.html", user=user)


@app.route("/profile/password", methods=["POST"])
def update_password():
    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])
    current_password = request.form["current_password"]
    new_password = request.form["new_password"]
    confirm_password = request.form["confirm_password"]

    if not check_password_hash(user.password, current_password):
        return "Current password is incorrect"
    if new_password != confirm_password:
        return "Password confirmation does not match"
    password_errors = validate_password_strength(new_password)
    if password_errors:
        return " ".join(password_errors)

    user.password = generate_password_hash(new_password)
    db.session.commit()
    return redirect("/profile")


# tạo subtask
@app.route("/create-subtask/<int:task_id>", methods=["GET", "POST"])
def create_subtask(task_id):
    if "user_id" not in session:
        return redirect("/login")
    if not task_accessible_for_session(task_id):
        return redirect("/tasks")

    current_role = session.get("role")

    users = [
        user for user in User.query.all()
        if ROLE_HIERARCHY.get(current_role, 0) 
        > ROLE_HIERARCHY.get(user.role, 0)
    ]

    if request.method == "POST":
        title = request.form["title"]
        assigned_to = request.form.get("assigned_to")
        assigned_user = User.query.get(int(assigned_to)) if assigned_to else None
        if assigned_user and ROLE_HIERARCHY.get(current_role, 0) <= ROLE_HIERARCHY.get(assigned_user.role, 0):
            return "Access Denied"

        new_subtask = SubTask(
            title=title,
            status="Pending",
            progress=0,
            task_id=task_id,
            created_by=session.get("user_id"),
            assigned_to=assigned_user.id if assigned_user else None,
        )
        db.session.add(new_subtask)
        log_activity(task_id, translate_ui("Created subtask"), title)
        db.session.commit()
        socketio.emit("global_changed", {"type":"subtask_created"})
        notify_task_live(task_id)
        notify_global_change(kind="task_updated", task_id=task_id)

        return redirect(f"/task/{task_id}")
    return render_template("create_subtask.html", task_id=task_id, users=users)


@app.route("/subtask/<int:id>")
def subtask_detail(id):
    if "user_id" not in session:
        return redirect("/login")
    if not subtask_accessible_for_session(id):
        return redirect("/tasks")

    subtask = SubTask.query.get_or_404(id)
    parent_task = Task.query.get(subtask.task_id)

    comments = (
        Comment.query.filter_by(task_id=subtask.task_id, subtask_id=subtask.id)
        .order_by(Comment.created_at.desc())
        .all()
    )
    attachments = (
        TaskAttachment.query.filter_by(task_id=subtask.task_id, subtask_id=subtask.id)
        .order_by(TaskAttachment.created_at.desc())
        .all()
    )
    issues = (
        Issue.query.filter_by(task_id=subtask.task_id, subtask_id=subtask.id)
        .order_by(Issue.created_at.desc())
        .all()
    )
    activity_page = request.args.get("activity_page", 1, type=int)
    activity_pagination = (
        ActivityLog.query.filter_by(task_id=subtask.task_id, subtask_id=subtask.id)
        .order_by(ActivityLog.created_at.desc())
        .paginate(page=activity_page, per_page=5, error_out=False)
    )

    return render_template(
        "subtask_detail.html",
        subtask=subtask,
        parent_task=parent_task,
        comments=comments,
        attachments=attachments,
        issues=issues,
        activities=activity_pagination.items,
        activity_pagination=activity_pagination,
    )


@app.route("/subtask/<int:subtask_id>/comment", methods=["POST"])
def add_subtask_comment(subtask_id):
    if "user_id" not in session:
        if wants_json_response():
            return jsonify({"error": "unauthorized"}), 401
        return redirect("/login")
    if not subtask_accessible_for_session(subtask_id):
        if wants_json_response():
            return jsonify({"error": "not found"}), 404
        return redirect("/tasks")

    subtask = SubTask.query.get_or_404(subtask_id)
    content = request.form["content"].strip()
    if not content:
        if wants_json_response():
            return jsonify({"error": "Comment content is required."}), 400
        return redirect(f"/subtask/{subtask_id}")

    comment = Comment(
        task_id=subtask.task_id,
        subtask_id=subtask.id,
        user_id=session["user_id"],
        author_name=session["username"],
        content=content,
    )
    db.session.add(comment)
    log_subtask_activity(subtask.task_id, subtask.id, translate_ui("Added comment (subtask)"), content[:120])
    db.session.commit()
    notify_task_live(subtask.task_id)
    notify_global_change(kind="task_updated", task_id=subtask.task_id)
    if wants_json_response():
        return jsonify({"message": "Comment added."})
    return redirect(f"/subtask/{subtask_id}")


@app.route("/subtask/<int:subtask_id>/issues", methods=["POST"])
def create_subtask_issue(subtask_id):
    if "user_id" not in session:
        if wants_json_response():
            return jsonify({"error": "unauthorized"}), 401
        return redirect("/login")
    if not subtask_accessible_for_session(subtask_id):
        if wants_json_response():
            return jsonify({"error": "not found"}), 404
        return redirect("/tasks")

    subtask = SubTask.query.get_or_404(subtask_id)
    title = request.form["title"].strip()
    description = request.form["description"].strip()
    severity = request.form.get("severity", "Normal")
    if not title:
        if wants_json_response():
            return jsonify({"error": "Issue title is required."}), 400
        return redirect(f"/subtask/{subtask_id}")

    issue = Issue(
        title=title,
        description=description,
        severity=severity,
        status="Open",
        task_id=subtask.task_id,
        subtask_id=subtask.id,
        created_by=session["user_id"],
        creator_name=session["username"],
    )
    db.session.add(issue)
    log_subtask_activity(subtask.task_id, subtask.id, translate_ui("Created issue (subtask)"), title)
    db.session.commit()
    socketio.emit("global_changed",{"type":"issue_created"})
    notify_task_live(subtask.task_id)
    notify_global_change(kind="task_updated", task_id=subtask.task_id)
    if wants_json_response():
        return jsonify({"message": "Issue reported."})
    return redirect(f"/subtask/{subtask_id}")


@app.route("/subtask/<int:subtask_id>/upload", methods=["POST"])
def upload_subtask_file(subtask_id):
    if "user_id" not in session:
        return redirect("/login")
    if not subtask_accessible_for_session(subtask_id):
        return redirect("/tasks")

    subtask = SubTask.query.get_or_404(subtask_id)

    if "file" not in request.files:
        return redirect(f"/subtask/{subtask_id}")

    uploaded_file = request.files["file"]
    if not uploaded_file.filename:
        return redirect(f"/subtask/{subtask_id}")
    if not allowed_file(uploaded_file.filename):
        return "File type is not supported"

    allowed_mimes = {
        "image/png",
        "image/jpeg",
        "image/gif",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain",
        "application/zip",
        "application/x-zip-compressed",
    }
    if not is_allowed_mimetype(uploaded_file.mimetype, allowed_mimes):
        return "File type is not supported"

    safe_name = secure_filename(uploaded_file.filename)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    stored_name = f"subtask_{subtask_id}_{timestamp}_{safe_name}"
    absolute_path = os.path.join(app.config["UPLOAD_FOLDER"], "attachments", stored_name)
    uploaded_file.save(absolute_path)

    attachment = TaskAttachment(
        task_id=subtask.task_id,
        subtask_id=subtask.id,
        uploaded_by=session["user_id"],
        uploader_name=session["username"],
        original_filename=safe_name,
        stored_filename=stored_name,
        file_path=f"attachments/{stored_name}",
        file_size=os.path.getsize(absolute_path),
        mime_type=uploaded_file.mimetype,
    )
    db.session.add(attachment)
    log_subtask_activity(subtask.task_id, subtask.id, translate_ui("Uploaded file (subtask)"), safe_name)
    db.session.commit()
    notify_task_live(subtask.task_id)
    notify_global_change(kind="task_updated", task_id=subtask.task_id)

    return redirect(f"/subtask/{subtask_id}")


# Update subtask
@app.route("/update-subtask/<int:id>", methods=["GET", "POST"])
def update_subtask(id):
    if "user_id" not in session:
        return redirect("/login")

    subtask = SubTask.query.get(id)
    if not subtask:
        return redirect("/tasks")
    if not subtask_accessible_for_session(subtask.id):
        return redirect("/tasks")

    if request.method == "POST":
        subtask.status = request.form["status"]
        subtask.progress = int(request.form["progress"])
        db.session.commit()
        socketio.emit("global_changed", {"type":"subtask_updated"})

        subtasks = SubTask.query.filter_by(task_id=subtask.task_id).all()

        total_progress = sum(s.progress or 0 for s in subtasks)

        average_progress = int(total_progress / len(subtasks)) if subtasks else 0

        parent_task = Task.query.get(subtask.task_id)
        if not parent_task:
            return jsonify({
                "success": False,
                "error": "Parent task not found."
            }), 404

        parent_task.progress = average_progress

        if average_progress == 100:
            parent_task.status = "Completed"
        elif average_progress > 0:
            parent_task.status = "In Progress"
        else:
            parent_task.status = "Pending"

        log_activity(
            subtask.task_id,
            translate_ui("Updated subtask"),
            f"{subtask.title}: {translate_ui(subtask.status)} ({subtask.progress}%)"
        )
        db.session.commit()
        notify_task_live(subtask.task_id)
        notify_global_change(kind="task_updated", task_id=subtask.task_id)

        if wants_json_response():
            return jsonify({
                "success": True,
                "message": "Subtask updated successfully.",
            })
        
        return redirect(f"/subtask/{subtask.id}")

    return render_template("update_subtask.html", subtask=subtask)

# Xóa subtask
@app.route("/delete-subtask/<int:id>", methods=["POST"])
def delete_subtask(id):
    if "user_id" not in session:
        return redirect("/login")

    subtask = SubTask.query.get(id)
    if not subtask:
        return redirect("/tasks")
    # Only the creator or users with access to parent task can delete.
    if not task_accessible_for_session(subtask.task_id) and int(subtask.created_by or 0) != int(session.get("user_id") or 0):
        return redirect("/tasks")

    task_id = subtask.task_id

    db.session.delete(subtask)
    log_activity(task_id, translate_ui("Deleted subtask"), subtask.title)
    db.session.commit()
    notify_task_live(task_id)
    notify_global_change(kind="task_updated", task_id=task_id)

    return redirect(f"/task/{task_id}")

# task list
@app.route("/tasks")
def tasks():
    if "user_id" not in session:
        return redirect("/login")

    search = request.args.get("search", "")
    status = request.args.get("status", "")

    query = scoped_task_query()
    assigned_subtasks = SubTask.query.filter_by(
        assigned_to=session.get("user_id")
    ).all()
    # Filter out subtasks whose parent task is deleted (archived)
    assigned_subtasks = [s for s in assigned_subtasks if Task.query.get(s.task_id) and not Task.query.get(s.task_id).is_deleted]

    if search:
        query = query.filter(Task.title.ilike(f"%{search}%"))

    if status:
        query = query.filter(Task.status == status)

    page = request.args.get("page", 1, type=int)
    pagination = (
        query.options(selectinload(Task.assigned_users))
        .order_by(Task.id.desc())
        .paginate(page=page, per_page=8, error_out=False)
    )
    all_tasks = pagination.items
    today = datetime.now(VN_TZ).date()

    return render_template(
        "tasks.html",
        tasks=all_tasks,
        today=today,
        pagination=pagination,
        subtasks=assigned_subtasks
    )

# update task
@app.route("/update-task/<int:id>", methods=["GET", "POST"])
def update_task(id):
    if "user_id" not in session:
        return redirect("/login")

    task = scoped_task_query().filter(Task.id == id).first()
    if not task:
        return redirect("/tasks")

    if request.method == "POST":
        old_status = task.status
        task.status = request.form["status"]
        task.progress = int(request.form["progress"])

        log_activity(task.id, translate_ui("Updated task"), f"{translate_ui('Status')}: {translate_ui(task.status)}, {translate_ui('Progress')}: {task.progress}%")
        if old_status != "Completed" and task.status == "Completed":
            notify_task_completed(task)
        db.session.commit()
        notify_task_live(task.id)
        notify_global_change(kind="task_updated", task_id=task.id)

        return redirect(f"/task/{task.id}")

    return render_template("update_task.html", task=task)


# Xóa task
@app.route("/delete-task/<int:id>", methods=["POST"])
def delete_task(id):

    if "user_id" not in session:
        return redirect("/login")

    task = Task.query.get(id)

    if not task:
        return redirect("/tasks")

    current_role = session.get("role")
    current_username = session.get("username")

    reason = request.form.get("reason", "").strip()

    if current_role == "employee":
        task.delete_request_status = "pending"
        task.delete_requested_by = current_username
        task.delete_requested_at = datetime.utcnow()
        task.delete_reason = reason
        log_activity(
            task.id,
            translate_ui("Delete request submitted"),
            f"{current_username} requested task deletion"
        )

        db.session.commit()
        notify_task_live(task.id)
        notify_global_change(
            kind="task_delete_requested",
            task_id=task.id
        )

        return redirect(f"/task/{task.id}")

    # manager delete
    if current_role in ["manager" , "admin", "director", "team_lead", "qa"]:
        task.is_deleted = True
        task.deleted_at = datetime.utcnow()
        task.deleted_by = current_username
        task.delete_request_status = "approved"
        log_activity(
            task.id,
            translate_ui("Task archived"),
            f"{translate_ui('Task')} {translate_ui('deleted')} by {current_username}"
        )
        db.session.commit()
        notify_global_change(
            kind="task_deleted",
            task_id=task.id
        )
        return redirect("/tasks")
    return redirect("/tasks")

@app.route("/approve-delete/<int:id>", methods=["POST"])
def approve_delete(id):
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") not in ["manager", "admin"]:
        return redirect("/tasks")

    task = Task.query.get(id)

    if not task:
        return redirect("/tasks")

    if session.get("role") not in ["manager", "admin", "director", "team_lead", "qa"]:
        return redirect("/tasks")

    task.is_deleted = True
    task.deleted_at = datetime.utcnow()
    task.deleted_by = session.get("username")
    task.delete_request_status = "approved"
    log_activity(
        task.id,
        translate_ui("Delete approved"),
        f"{translate_ui('Task')} {translate_ui('deleted')} by {session.get('username')}"
    )
    db.session.commit()

    notify_global_change(
        kind="task_deleted",
        task_id=task.id
    )
    return redirect("/tasks")

# Reject delete
@app.route("/reject-delete/<int:id>", methods=["POST"])
def reject_delete(id):
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") not in ["manager", "admin", "director", "team_lead", "qa"]:
        return redirect("/tasks")

    task = Task.query.get(id)

    if not task:
        return redirect("/tasks")

    task.delete_request_status = "rejected"
    log_activity(
        task.id,
        translate_ui("Delete rejected"),
        f"{translate_ui('Delete request')} {translate_ui('rejected')} by {session.get('username')}"
    )
    db.session.commit()
    notify_task_live(task.id)
    return redirect(f"/task/{task.id}")

# Lưu trữ task
@app.route("/archived-tasks")
def archive_task():
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") not in ["manager", "admin", "director", "team_lead", "qa"]:
        return redirect("/tasks")

    tasks = Task.query.filter_by(
        is_deleted=True,
    ).order_by(Task.deleted_at.desc()).all()

    return render_template(
        "archived_tasks.html",
        tasks=tasks
    )

# Xóa task trong lưu trữ
@app.route("/permanently-delete-task/<int:id>", methods=["POST"])
def permanently_delete_task(id):
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "director":
        return redirect("/archived-tasks")

    task = Task.query.get(id)

    if not task or not task.is_deleted:
        return redirect("/archived-tasks")

    # Xóa toàn bộ dữ liệu liên quan
    Comment.query.filter_by(task_id=task.id).delete()
    Issue.query.filter_by(task_id=task.id).delete()
    ActivityLog.query.filter_by(task_id=task.id).delete()
    TaskAttachment.query.filter_by(task_id=task.id).delete()

    subtasks = SubTask.query.filter_by(task_id=task.id).all()
    for subtask in subtasks:
        Comment.query.filter_by(subtask_id=subtask.id).delete()
        Issue.query.filter_by(subtask_id=subtask.id).delete()
        ActivityLog.query.filter_by(subtask_id=subtask.id).delete()
        TaskAttachment.query.filter_by(subtask_id=subtask.id).delete()

        db.session.delete(subtask)
        
    db.session.delete(task)
    db.session.commit()
    notify_global_change(
        kind="task_permanently_deleted",
        task_id=task.id
    )
    return redirect("/archived-tasks")

@app.route("/kanban")
def kanban():
    if "user_id" not in session:
        return redirect("/login")

    if session["role"] in ["manager", "admin", "director", "team_lead", "qa"]:
        pending_tasks = Task.query.filter_by(status="Pending", is_deleted=False).all()
        progress_tasks = Task.query.filter_by(status="In Progress", is_deleted=False).all()
        completed_tasks = Task.query.filter_by(status="Completed", is_deleted=False).all()
    else:
        current_user = User.query.get(session["user_id"])

        pending_tasks = Task.query.join(task_users).filter(
            task_users.c.user_id == current_user.id,
            Task.status == "Pending"
        ).all()

        progress_tasks = Task.query.join(task_users).filter(
            task_users.c.user_id == current_user.id,
            Task.status == "In Progress"
        ).all()

        completed_tasks = Task.query.join(task_users).filter(
            task_users.c.user_id == current_user.id,
            Task.status == "Completed"
        ).all()

    return render_template(
        "kanban.html",
        pending_tasks=pending_tasks,
        progress_tasks=progress_tasks,
        completed_tasks=completed_tasks
    )

# cập nhật status
@app.route("/update-status/<int:id>", methods=["POST"])
def update_status(id):
    if "user_id" not in session:
        return jsonify({"message": "unauthorized"}), 401
    task = scoped_task_query().filter(Task.id == id).first()
    if not task:
        return jsonify({"message": "not found"}), 404

    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in ["Pending", "In Progress", "Completed"]:
        return jsonify({"message": "invalid status"}), 400
    old_status = task.status
    task.status = status

    if task.status == "Pending":
        task.progress = 0
    elif task.status == "Completed":
        task.progress = 100

    log_activity(task.id, translate_ui("Moved task on kanban"), f"{translate_ui('New status')}: {translate_ui(task.status)}")
    if old_status != "Completed" and task.status == "Completed":
        notify_task_completed(task)
    db.session.commit()
    sections = ["task", "activities"]
    notify_task_live(task.id, sections=sections)
    notify_global_change(kind="task_updated", task_id=task.id)

    return jsonify({
        "message": "updated",
        "sections": sections,
        "payload": serialize_task_live(task.id, sections=sections),
    })


@app.route("/api/notifications/read", methods=["POST"])
def api_notifications_read():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401
    Notification.query.filter_by(user_id=session["user_id"], is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"message": "marked_read"})


@app.route("/user-guide/seen", methods=["POST"])
def user_guide_seen():
    user = get_current_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401
    user.has_seen_guide = True
    db.session.commit()
    return jsonify({"message": "ok"})


with app.app_context():
    ensure_schema()

if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
