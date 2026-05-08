from database import db

class SubTask(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200))

    status = db.Column(db.String(50))

    progress = db.Column(db.Integer)

    task_id = db.Column(db.Integer)