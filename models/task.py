from database import db

task_users = db.Table(
    "task_users",

    db.Column(
        "task_id",
        db.Integer,
        db.ForeignKey("task.id")
    ),

    db.Column(
        "user_id",
        db.Integer,
        db.ForeignKey("user.id")
    )
)

class Task(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200))

    description = db.Column(db.Text)

    status = db.Column(db.String(50))

    progress = db.Column(db.Integer)

    deadline = db.Column(db.String(50))

    priority = db.Column(db.String(20))

    assigned_users = db.relationship(
        "User",
        secondary=task_users,
        backref="tasks"
    )