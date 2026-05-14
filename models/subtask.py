from database import db
from datetime import datetime

subtask_users = db.Table(
    "subtask_users",

    db.Column(
        "subtask_id",
        db.Integer,
        db.ForeignKey("sub_task.id"),
        nullable=False,
    ),

    db.Column(
        "user_id",
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
    ),
    db.Index("ix_subtask_users_user_subtask", "user_id", "subtask_id"),
    db.Index("ix_subtask_users_subtask_user", "subtask_id", "user_id"),
)


class SubTask(db.Model):
    __table_args__ = (
        db.Index("ix_subtask_task_status", "task_id", "status"),
        db.Index("ix_subtask_created_by_status", "created_by", "status"),
        db.Index("ix_subtask_created_at", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200))

    status = db.Column(db.String(50))

    progress = db.Column(db.Integer)

    task_id = db.Column(db.Integer)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    created_by = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True,
    )

    creator = db.relationship(
        "User",
        foreign_keys=[created_by]
    )

    assigned_users = db.relationship(
        "User",
        secondary=subtask_users,
        backref="assigned_subtasks"
    )
