from database import db

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100))

    email = db.Column(db.String(100))

    password = db.Column(db.String(100))

    role = db.Column(db.String(50))

    avatar_path = db.Column(db.String(255), nullable=True)
    full_name = db.Column(db.String(120), nullable=True)
    bio = db.Column(db.Text, nullable=True)