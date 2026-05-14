from datetime import datetime

from database import db


class Issue(db.Model):
    __table_args__ = (
        db.Index("ix_issue_task_status_created", "task_id", "status", "created_at"),
        db.Index("ix_issue_subtask_status_created", "subtask_id", "status", "created_at"),
        db.Index("ix_issue_created_by_created", "created_by", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(30), default="Normal", nullable=False)
    status = db.Column(db.String(50), default="Open", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

    task_id = db.Column(db.Integer, nullable=False)
    subtask_id = db.Column(db.Integer, nullable=True)
    created_by = db.Column(db.Integer, nullable=False)
    creator_name = db.Column(db.String(100), nullable=False)
