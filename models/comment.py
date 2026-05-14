from datetime import datetime

from database import db


class Comment(db.Model):
    __table_args__ = (
        db.Index("ix_comment_task_subtask_created", "task_id", "subtask_id", "created_at"),
        db.Index("ix_comment_user_created", "user_id", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    task_id = db.Column(db.Integer, nullable=False)
    subtask_id = db.Column(db.Integer, nullable=True)
    user_id = db.Column(db.Integer, nullable=False)
    author_name = db.Column(db.String(100), nullable=False)
