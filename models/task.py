from database import db
from datetime import datetime

task_users = db.Table(
    "task_users",

    db.Column(
        "task_id",
        db.Integer,
        db.ForeignKey("task.id"),
        nullable=False,
    ),

    db.Column(
        "user_id",
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
    ),
    db.Index("ix_task_users_user_task", "user_id", "task_id"),
    db.Index("ix_task_users_task_user", "task_id", "user_id"),
)

class Task(db.Model):
    __table_args__ = (
        db.Index("ix_task_active_status", "is_deleted", "status"),
        db.Index("ix_task_created_by_status", "created_by", "status"),
        db.Index("ix_task_deadline_status", "deadline", "status"),
        db.Index("ix_task_created_at", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200))

    description = db.Column(db.Text)

    status = db.Column(db.String(50))

    progress = db.Column(db.Integer)

    deadline = db.Column(db.String(50))

    priority = db.Column(db.String(20))

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # =========================
    # CREATE SYSTEM
    # =========================

    created_by = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True
    )

    creator = db.relationship(
        "User",
        foreign_keys=[created_by]
    )
    # =========================
    # DELETE SYSTEM
    # =========================

    is_deleted = db.Column(
        db.Boolean,
        default=False
    )

    deleted_at = db.Column(
        db.DateTime,
        nullable=True
    )

    deleted_by = db.Column(
        db.String(100),
        nullable=True
    )

    delete_reason = db.Column(
        db.Text,
        nullable=True
    )

    delete_request_status = db.Column(
        db.String(30),
        default="none"
    )

    delete_requested_by = db.Column(
        db.String(100),
        nullable=True
    )

    delete_requested_at = db.Column(
        db.DateTime,
        nullable=True
    )

    assigned_users = db.relationship(
        "User",
        secondary=task_users,
        backref="tasks"
    )
