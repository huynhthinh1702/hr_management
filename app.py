import os
from datetime import datetime, date
from zoneinfo import ZoneInfo

from flask import Flask, abort, jsonify, redirect, render_template, request, send_from_directory, session
from flask_wtf.csrf import CSRFProtect
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

from database import db
from models.activity_log import ActivityLog
from models.comment import Comment
from models.issue import Issue
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


def notify_task_live(task_id):
    emit_task_live(socketio, task_id)


def notify_task_removed(task_id):
    emit_task_removed(socketio, task_id)


def notify_global_change(kind="data_changed", task_id=None):
    emit_global(socketio, kind=kind, task_id=task_id)


def serialize_task_live(task_id):
    task = Task.query.get(task_id)
    if not task:
        return None
    subtasks = SubTask.query.filter_by(task_id=task_id).order_by(SubTask.id).all()
    comments = Comment.query.filter_by(task_id=task_id).order_by(Comment.created_at.desc()).all()
    attachments = TaskAttachment.query.filter_by(task_id=task_id).order_by(TaskAttachment.created_at.desc()).all()
    issues = Issue.query.filter_by(task_id=task_id).order_by(Issue.created_at.desc()).all()
    activities = (
        ActivityLog.query.filter_by(task_id=task_id)
        .order_by(ActivityLog.created_at.desc())
        .limit(5)
        .all()
    )

    def dt_iso(dt):
        return fmt_vn(dt)

    return {
        "task": {
            "id": task.id,
            "title": task.title,
            "description": task.description or "",
            "status": task.status,
            "progress": task.progress,
            "deadline": task.deadline,
            "priority": task.priority,
        },
        "subtasks": [
            {
                "id": s.id,
                "title": s.title,
                "status": s.status,
                "progress": s.progress,
            }
            for s in subtasks
        ],
        "comments": [
            {
                "author_name": c.author_name,
                "content": c.content,
                "created_at": dt_iso(c.created_at),
            }
            for c in comments
        ],
        "issues": [
            {
                "id": i.id,
                "title": i.title,
                "description": i.description or "",
                "status": i.status,
                "creator_name": i.creator_name,
                "created_at": dt_iso(i.created_at),
            }
            for i in issues
        ],
        "attachments": [
            {
                "file_path": a.file_path,
                "original_filename": a.original_filename,
                "uploader_name": a.uploader_name,
            }
            for a in attachments
        ],
        "activities": [
            {
                "action": a.action,
                "details": a.details,
                "actor_name": a.actor_name,
                "created_at": dt_iso(a.created_at),
            }
            for a in activities
        ],
    }


def get_current_user():
    if "user_id" not in session:
        return None
    return User.query.get(session["user_id"])


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
        user_id=session["user_id"],
        actor_name=session.get("username", "Unknown"),
        action=action,
        details=details
    )
    db.session.add(activity)


@app.context_processor
def inject_global_data():
    return {
        "current_user": get_current_user(),
        "fmt_vn": fmt_vn,
        "is_overdue_task": is_overdue_task,
    }


@app.template_filter("vn_time")
def vn_time_filter(dt, fmt="%Y-%m-%d %H:%M"):
    return fmt_vn(dt, fmt=fmt)


def scoped_task_query():
    if session.get("role") in ["manager", "admin"]:
        return Task.query
    current_user = User.query.get(session["user_id"])
    return Task.query.join(task_users).filter(
        task_users.c.user_id == current_user.id
    )


def task_accessible_for_session(task_id):
    if "user_id" not in session:
        return False
    return scoped_task_query().filter(Task.id == task_id).first() is not None


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
    payload = serialize_task_live(task_id)
    if payload is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(payload)


@app.route("/api/dashboard/summary", methods=["GET"])
def api_dashboard_summary():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    tasks = scoped_task_query().all()
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == "Completed")
    pending_tasks = total_tasks - completed_tasks

    task_ids = [t.id for t in tasks]
    if task_ids:
        total_issues = Issue.query.filter(Issue.task_id.in_(task_ids)).count()
        resolved_issues = Issue.query.filter(
            Issue.task_id.in_(task_ids),
            Issue.status == "Resolved"
        ).count()
        recent_issues = (
            Issue.query.filter(Issue.task_id.in_(task_ids))
            .order_by(Issue.created_at.desc())
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

    # Productivity by employee (assigned tasks completed)
    prod = {}
    for t in tasks:
        for u in (t.assigned_users or []):
            prod.setdefault(u.username, {"username": u.username, "completed": 0, "total": 0})
            prod[u.username]["total"] += 1
            if t.status == "Completed":
                prod[u.username]["completed"] += 1
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

    # Completion speed: average/median days from creation to completion (based on ActivityLog)
    created_by_task = {}
    completed_by_task = {}
    for log in logs:
        if log.action == "Created task":
            prev = created_by_task.get(log.task_id)
            if prev is None or log.created_at < prev:
                created_by_task[log.task_id] = log.created_at

        # completion signal: moved/updated log that mentions Completed
        if log.action in ["Updated task", "Moved task on kanban"]:
            if "Completed" in (log.details or ""):
                prev = completed_by_task.get(log.task_id)
                if prev is None or log.created_at < prev:
                    completed_by_task[log.task_id] = log.created_at

    durations = []
    for tid, created_at in created_by_task.items():
        completed_at = completed_by_task.get(tid)
        if not completed_at:
            continue
        delta_days = (completed_at - created_at).total_seconds() / 86400.0
        if delta_days >= 0:
            durations.append(delta_days)

    durations_sorted = sorted(durations)
    avg_days = round(sum(durations_sorted) / len(durations_sorted), 2) if durations_sorted else None
    if durations_sorted:
        mid = len(durations_sorted) // 2
        median_days = (
            round(durations_sorted[mid], 2)
            if len(durations_sorted) % 2 == 1
            else round((durations_sorted[mid - 1] + durations_sorted[mid]) / 2.0, 2)
        )
    else:
        median_days = None

    return jsonify({
        "overdue": {"count": overdue, "total": total, "rate": overdue_rate},
        "completion_speed": {
            "avg_days": avg_days,
            "median_days": median_days,
            "completed_count": len(durations_sorted),
        },
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

    if session["role"] in ["manager", "admin"]:
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
            "assigned_users": [{"username": u.username} for u in (t.assigned_users or [])],
        }

    return jsonify({
        "today": today.strftime("%Y-%m-%d"),
        "page": pagination.page,
        "pages": pagination.pages,
        "has_prev": pagination.has_prev,
        "has_next": pagination.has_next,
        "tasks": [serialize_row(t) for t in tasks],
    })


@app.route("/")
def home():
    return render_template("index.html")

# Đăng ký
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        if User.query.filter_by(email=email).first():
            return "Email already exists"

        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            role=role,
            full_name=full_name
        )
        db.session.add(new_user)
        db.session.commit()
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
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role

            return redirect("/dashboard")
        return "Login Failed"

    return render_template("login.html")


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

    tasks = scoped_task_query().options(selectinload(Task.assigned_users)).all()

    total_tasks = len(tasks)
    completed_tasks = 0
    pending_tasks = 0

    for task in tasks:
        if task.status == "Completed":
            completed_tasks += 1
        else:
            pending_tasks += 1

    task_ids = [task.id for task in tasks]
    if task_ids:
        total_issues = Issue.query.filter(Issue.task_id.in_(task_ids)).count()
        resolved_issues = Issue.query.filter(
            Issue.task_id.in_(task_ids),
            Issue.status == "Resolved"
        ).count()
        recent_issues = Issue.query.filter(Issue.task_id.in_(task_ids)).order_by(Issue.created_at.desc()).limit(6).all()
    else:
        total_issues = 0
        resolved_issues = 0
        recent_issues = []
    unresolved_issues = total_issues - resolved_issues
    issue_resolution_rate = int((resolved_issues / total_issues) * 100) if total_issues else 0

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
    return "Admin Page"

# Tạo task
@app.route("/create-task", methods=["GET", "POST"])
def create_task():
    if "user_id" not in session:
        return redirect("/login")
    if session["role"] != "manager":
        return "Access Deinied"

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
        log_activity(
            task_id=new_task.id,
            action="Created task",
            details=f"Task '{new_task.title}' created"
        )
        db.session.commit()
        notify_task_live(new_task.id)
        notify_global_change(kind="task_created", task_id=new_task.id)

        return redirect(f"/task/{new_task.id}")

    users = User.query.all()
    return render_template(
        "create_task.html",
        users=users
    )

# task detail
@app.route("/task/<int:id>")
def task_detail(id):
    if "user_id" not in session:
        return redirect("/login")

    task = scoped_task_query().filter(Task.id == id).first()
    if not task:
        return redirect("/tasks")

    subtasks = SubTask.query.filter_by(task_id=id).all()
    comments = Comment.query.filter_by(task_id=id).order_by(Comment.created_at.desc()).all()
    activity_page = request.args.get("activity_page", 1, type=int)
    activity_pagination = ActivityLog.query.filter_by(task_id=id).order_by(
        ActivityLog.created_at.desc()
    ).paginate(page=activity_page, per_page=5, error_out=False)
    attachments = TaskAttachment.query.filter_by(task_id=id).order_by(TaskAttachment.created_at.desc()).all()
    issues = Issue.query.filter_by(task_id=id).order_by(Issue.created_at.desc()).all()

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
        return redirect("/login")
    if not task_accessible_for_session(task_id):
        return redirect("/tasks")

    content = request.form["content"].strip()
    if not content:
        return redirect(f"/task/{task_id}")

    comment = Comment(
        task_id=task_id,
        user_id=session["user_id"],
        author_name=session["username"],
        content=content
    )
    db.session.add(comment)
    log_activity(task_id, "Added comment", content[:120])
    db.session.commit()
    notify_task_live(task_id)
    notify_global_change(kind="task_updated", task_id=task_id)
    return redirect(f"/task/{task_id}")


@app.route("/task/<int:task_id>/issues", methods=["POST"])
def create_issue(task_id):
    if "user_id" not in session:
        return redirect("/login")
    if not task_accessible_for_session(task_id):
        return redirect("/tasks")

    title = request.form["title"].strip()
    description = request.form["description"].strip()
    if not title:
        return redirect(f"/task/{task_id}")

    issue = Issue(
        title=title,
        description=description,
        status="Open",
        task_id=task_id,
        created_by=session["user_id"],
        creator_name=session["username"]
    )
    db.session.add(issue)
    log_activity(task_id, "Created issue", title)
    db.session.commit()
    notify_task_live(task_id)
    notify_global_change(kind="task_updated", task_id=task_id)
    return redirect(f"/task/{task_id}")


@app.route("/issues/<int:issue_id>/resolve", methods=["POST"])
def resolve_issue(issue_id):
    if "user_id" not in session:
        return redirect("/login")
    issue = Issue.query.get(issue_id)
    if not issue:
        return redirect("/tasks")
    if not task_accessible_for_session(issue.task_id):
        return redirect("/tasks")

    issue.status = "Resolved"
    issue.resolved_at = datetime.utcnow()
    log_activity(issue.task_id, "Resolved issue", issue.title)
    db.session.commit()
    notify_task_live(issue.task_id)
    notify_global_change(kind="task_updated", task_id=issue.task_id)
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
        uploaded_by=session["user_id"],
        uploader_name=session["username"],
        original_filename=safe_name,
        stored_filename=stored_name,
        file_path=f"attachments/{stored_name}",
        file_size=os.path.getsize(absolute_path),
        mime_type=uploaded_file.mimetype
    )
    db.session.add(attachment)
    log_activity(task_id, "Uploaded file", safe_name)
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
        user.username = request.form["username"].strip()
        user.email = request.form["email"].strip()
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
    if len(new_password) < 6:
        return "New password must be at least 6 characters"

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

    if request.method == "POST":
        title = request.form["title"]

        new_subtask = SubTask(
            title=title,
            status="Pending",
            progress=0,
            task_id=task_id
        )
        db.session.add(new_subtask)
        log_activity(task_id, "Created subtask", title)
        db.session.commit()
        notify_task_live(task_id)
        notify_global_change(kind="task_updated", task_id=task_id)

        return redirect(f"/task/{task_id}")
    return render_template("create_subtask.html", task_id=task_id)

# Update subtask
@app.route("/update-subtask/<int:id>", methods=["GET", "POST"])
def update_subtask(id):
    if "user_id" not in session:
        return redirect("/login")

    subtask = SubTask.query.get(id)
    if not subtask:
        return redirect("/tasks")
    if not task_accessible_for_session(subtask.task_id):
        return redirect("/tasks")

    if request.method == "POST":
        subtask.status = request.form["status"]
        subtask.progress = int(request.form["progress"])
        db.session.commit()

        subtasks = SubTask.query.filter_by(task_id=subtask.task_id).all()

        total_progress = 0
        for item in subtasks:
            total_progress += item.progress

        average_progress = int(total_progress / len(subtasks)) if subtasks else 0

        parent_task = scoped_task_query().filter(Task.id == subtask.task_id).first()
        if not parent_task:
            return redirect("/tasks")

        parent_task.progress = average_progress

        if average_progress == 100:
            parent_task.status = "Completed"
        elif average_progress > 0:
            parent_task.status = "In Progress"
        else:
            parent_task.status = "Pending"

        log_activity(
            subtask.task_id,
            "Updated subtask",
            f"{subtask.title}: {subtask.status} ({subtask.progress}%)"
        )
        db.session.commit()
        notify_task_live(subtask.task_id)
        notify_global_change(kind="task_updated", task_id=subtask.task_id)
        return redirect(f"/task/{subtask.task_id}")

    return render_template("update_subtask.html", subtask=subtask)

# Xóa subtask
@app.route("/delete-subtask/<int:id>", methods=["POST"])
def delete_subtask(id):
    if "user_id" not in session:
        return redirect("/login")

    subtask = SubTask.query.get(id)
    if not subtask:
        return redirect("/tasks")
    if not task_accessible_for_session(subtask.task_id):
        return redirect("/tasks")

    task_id = subtask.task_id

    db.session.delete(subtask)
    log_activity(task_id, "Deleted subtask", subtask.title)
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
        pagination=pagination
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
        task.status = request.form["status"]
        task.progress = int(request.form["progress"])

        log_activity(task.id, "Updated task", f"Status: {task.status}, Progress: {task.progress}%")
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

    task = scoped_task_query().filter(Task.id == id).first()
    if not task:
        return redirect("/tasks")

    task_id_removed = task.id

    subtasks = SubTask.query.filter_by(task_id=id).all()

    for subtask in subtasks:
        db.session.delete(subtask)

    comments = Comment.query.filter_by(task_id=id).all()
    activities = ActivityLog.query.filter_by(task_id=id).all()
    attachments = TaskAttachment.query.filter_by(task_id=id).all()
    issues = Issue.query.filter_by(task_id=id).all()

    for comment in comments:
        db.session.delete(comment)
    for activity in activities:
        db.session.delete(activity)
    for attachment in attachments:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], attachment.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        db.session.delete(attachment)
    for issue in issues:
        db.session.delete(issue)

    db.session.delete(task)
    db.session.commit()
    notify_task_removed(task_id_removed)
    notify_global_change(kind="task_deleted", task_id=task_id_removed)

    return redirect("/tasks")

@app.route("/kanban")
def kanban():
    if "user_id" not in session:
        return redirect("/login")

    if session["role"] in ["manager", "admin"]:
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

    data = request.get_json()
    task.status = data["status"]

    if task.status == "Pending":
        task.progress = 0
    elif task.status == "Completed":
        task.progress = 100

    log_activity(task.id, "Moved task on kanban", f"New status: {task.status}")
    db.session.commit()
    notify_task_live(task.id)
    notify_global_change(kind="task_updated", task_id=task.id)

    return jsonify({"message": "updated"})


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)