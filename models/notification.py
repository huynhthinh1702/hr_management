from datetime import datetime

from database import db


class Notification(db.Model):
    __table_args__ = (
        db.Index("ix_notification_user_read_created", "user_id", "is_read", "created_at"),
        db.Index("ix_notification_user_type_task", "user_id", "type", "task_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    actor_id = db.Column(db.Integer, nullable=True)
    task_id = db.Column(db.Integer, nullable=True)
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    url = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
