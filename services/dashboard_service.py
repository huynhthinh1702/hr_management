from datetime import datetime

from sqlalchemy import and_, case, extract, func, or_, select

from database import db
from models.activity_log import ActivityLog
from models.issue import Issue
from models.subtask import SubTask, subtask_users
from models.task import Task, task_users
from models.user import User
from services.cache import get_int, get_json, incr, set_json


DASHBOARD_CACHE_TTL_SECONDS = 45
DASHBOARD_CACHE_VERSION_KEY = "hr:dashboard:version"


def _cache_key(kind, user_id):
    version = get_int(DASHBOARD_CACHE_VERSION_KEY, 1)
    return f"hr:dashboard:{kind}:v{version}:u{int(user_id)}"


def invalidate_dashboard_cache():
    return incr(DASHBOARD_CACHE_VERSION_KEY)


def active_subtask_scope_query(user_id):
    return (
        db.session.query(
            SubTask.id.label("id"),
            SubTask.status.label("status"),
            SubTask.task_id.label("task_id"),
        )
        .join(Task, Task.id == SubTask.task_id)
        .filter(Task.is_deleted.is_(False))
        .filter(
            or_(
                SubTask.created_by == user_id,
                SubTask.assigned_users.any(User.id == user_id),
            )
        )
    )


def _task_counts(task_scope_sq):
    return db.session.query(
        func.count(task_scope_sq.c.id),
        func.coalesce(
            func.sum(case((task_scope_sq.c.status == "Completed", 1), else_=0)),
            0,
        ),
    ).one()


def _subtask_counts(subtask_scope_sq):
    return db.session.query(
        func.count(subtask_scope_sq.c.id),
        func.coalesce(
            func.sum(case((subtask_scope_sq.c.status == "Completed", 1), else_=0)),
            0,
        ),
    ).one()


def _issue_scope_filter(task_scope_sq, subtask_scope_sq):
    task_ids = select(task_scope_sq.c.id)
    subtask_ids = select(subtask_scope_sq.c.id)
    return or_(
        and_(Issue.subtask_id.is_(None), Issue.task_id.in_(task_ids)),
        Issue.subtask_id.in_(subtask_ids),
    )


def build_dashboard_summary(task_scope_query, user_id):
    cache_key = _cache_key("summary", user_id)
    cached = get_json(cache_key)
    if cached:
        return cached

    task_scope_sq = task_scope_query.with_entities(
        Task.id.label("id"),
        Task.status.label("status"),
    ).subquery()
    subtask_scope_sq = active_subtask_scope_query(user_id).subquery()

    task_total, task_completed = _task_counts(task_scope_sq)
    subtask_total, subtask_completed = _subtask_counts(subtask_scope_sq)

    total_tasks = int(task_total or 0) + int(subtask_total or 0)
    completed_tasks = int(task_completed or 0) + int(subtask_completed or 0)
    pending_tasks = total_tasks - completed_tasks

    issue_filter = _issue_scope_filter(task_scope_sq, subtask_scope_sq)
    total_issues, resolved_issues = db.session.query(
        func.count(Issue.id),
        func.coalesce(
            func.sum(case((Issue.status == "Resolved", 1), else_=0)),
            0,
        ),
    ).filter(issue_filter).one()

    recent_issues = (
        Issue.query.filter(issue_filter)
        .order_by(Issue.created_at.desc(), Issue.id.desc())
        .limit(6)
        .all()
    )

    total_issues = int(total_issues or 0)
    resolved_issues = int(resolved_issues or 0)
    unresolved_issues = total_issues - resolved_issues
    issue_resolution_rate = int((resolved_issues / total_issues) * 100) if total_issues else 0

    payload = {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "total_issues": total_issues,
        "resolved_issues": resolved_issues,
        "unresolved_issues": unresolved_issues,
        "issue_resolution_rate": issue_resolution_rate,
        "recent_issues": [
            {
                "id": issue.id,
                "title": issue.title,
                "status": issue.status,
                "creator_name": issue.creator_name,
            }
            for issue in recent_issues
        ],
    }
    set_json(cache_key, payload, ex=DASHBOARD_CACHE_TTL_SECONDS)
    return payload


def build_dashboard_analytics(task_scope_query, user_id, today_date):
    cache_key = _cache_key("analytics", user_id)
    cached = get_json(cache_key)
    if cached:
        return cached

    task_scope_sq = task_scope_query.with_entities(
        Task.id.label("id"),
        Task.status.label("status"),
        Task.deadline.label("deadline"),
    ).subquery()
    subtask_scope_sq = active_subtask_scope_query(user_id).subquery()
    task_ids = select(task_scope_sq.c.id)

    task_rows = db.session.query(task_scope_sq.c.deadline, task_scope_sq.c.status).all()
    overdue = 0
    total = len(task_rows)
    for deadline, status in task_rows:
        if status == "Completed" or not deadline:
            continue
        try:
            overdue += int(datetime.strptime(str(deadline), "%Y-%m-%d").date() < today_date)
        except ValueError:
            continue
    overdue_rate = int((overdue / total) * 100) if total else 0

    task_productivity_rows = (
        db.session.query(
            User.id,
            User.username,
            User.full_name,
            func.count(Task.id).label("total"),
            func.coalesce(
                func.sum(case((Task.status == "Completed", 1), else_=0)),
                0,
            ).label("completed"),
        )
        .select_from(task_users)
        .join(Task, Task.id == task_users.c.task_id)
        .join(User, User.id == task_users.c.user_id)
        .filter(Task.id.in_(task_ids))
        .group_by(User.id, User.username, User.full_name)
        .all()
    )

    subtask_productivity_rows = (
        db.session.query(
            User.id,
            User.username,
            User.full_name,
            func.count(SubTask.id).label("total"),
            func.coalesce(
                func.sum(case((SubTask.status == "Completed", 1), else_=0)),
                0,
            ).label("completed"),
        )
        .select_from(subtask_users)
        .join(SubTask, SubTask.id == subtask_users.c.subtask_id)
        .join(User, User.id == subtask_users.c.user_id)
        .filter(SubTask.id.in_(select(subtask_scope_sq.c.id)))
        .group_by(User.id, User.username, User.full_name)
        .all()
    )

    productivity_map = {}
    for row in list(task_productivity_rows) + list(subtask_productivity_rows):
        label = row.full_name or row.username
        item = productivity_map.setdefault(
            row.id,
            {"username": label, "completed": 0, "total": 0},
        )
        item["completed"] += int(row.completed or 0)
        item["total"] += int(row.total or 0)

    productivity = sorted(
        productivity_map.values(),
        key=lambda item: (-item["completed"], -item["total"], item["username"]),
    )[:12]

    created_rows = (
        db.session.query(
            func.date(ActivityLog.created_at).label("day"),
            func.count(ActivityLog.id).label("count"),
        )
        .filter(
            ActivityLog.task_id.in_(task_ids),
            ActivityLog.action == "Created task",
        )
        .group_by(func.date(ActivityLog.created_at))
        .order_by(func.date(ActivityLog.created_at))
        .all()
    )

    completed_rows = (
        db.session.query(
            func.date(ActivityLog.created_at).label("day"),
            func.count(ActivityLog.id).label("count"),
        )
        .filter(
            ActivityLog.task_id.in_(task_ids),
            ActivityLog.action.in_(["Updated task", "Moved task on kanban"]),
            ActivityLog.details.ilike("%Completed%"),
        )
        .group_by(func.date(ActivityLog.created_at))
        .order_by(func.date(ActivityLog.created_at))
        .all()
    )

    created_map = {str(row.day): int(row.count or 0) for row in created_rows}
    completed_map = {str(row.day): int(row.count or 0) for row in completed_rows}
    all_days = sorted(set(created_map) | set(completed_map))[-30:]

    heat_rows = (
        db.session.query(
            extract("dow", ActivityLog.created_at).label("weekday"),
            extract("hour", ActivityLog.created_at).label("hour"),
            func.count(ActivityLog.id).label("count"),
        )
        .filter(ActivityLog.task_id.in_(task_ids))
        .group_by(
            extract("dow", ActivityLog.created_at),
            extract("hour", ActivityLog.created_at),
        )
        .all()
    )
    heat = [[0 for _ in range(24)] for _ in range(7)]
    for row in heat_rows:
        heat[int(row.weekday)][int(row.hour)] = int(row.count or 0)

    payload = {
        "overdue": {"count": overdue, "total": total, "rate": overdue_rate},
        "productivity": productivity,
        "trend": {
            "labels": all_days,
            "created": [created_map.get(day, 0) for day in all_days],
            "completed": [completed_map.get(day, 0) for day in all_days],
        },
        "heatmap": {
            "weekday_labels": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            "hours": list(range(24)),
            "matrix": heat,
        },
    }
    set_json(cache_key, payload, ex=DASHBOARD_CACHE_TTL_SECONDS)
    return payload
