from datetime import datetime

from database import db


class TaskAttachment(db.Model):
    __table_args__ = (
        db.Index("ix_attachment_task_subtask_created", "task_id", "subtask_id", "created_at"),
        db.Index("ix_attachment_uploaded_by_created", "uploaded_by", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(120), nullable=True)
    file_size = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    task_id = db.Column(db.Integer, nullable=False)
    subtask_id = db.Column(db.Integer, nullable=True)
    uploaded_by = db.Column(db.Integer, nullable=False)
    uploader_name = db.Column(db.String(100), nullable=False)
