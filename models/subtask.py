from database import db

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

    assigned_to = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True
    )

    assigned_user = db.relationship("User", foreign_keys=[assigned_to])
    creator = db.relationship("User", foreign_keys=[created_by])