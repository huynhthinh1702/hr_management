from database import db

subtask_users = db.Table(
    "subtask_users",

    db.Column(
        "subtask_id",
        db.Integer,
        db.ForeignKey("sub_task.id")
    ),

    db.Column(
        "user_id",
        db.Integer,
        db.ForeignKey("user.id")
    )
)


class SubTask(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200))

    status = db.Column(db.String(50))

    progress = db.Column(db.Integer)

    task_id = db.Column(db.Integer)

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