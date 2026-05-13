from database import db

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True)

    email = db.Column(db.String(100), unique=True)

    password = db.Column(db.Text)

    role = db.Column(db.String(50))

    avatar_path = db.Column(db.String(255), nullable=True)
    full_name = db.Column(db.String(120), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    is_locked = db.Column(db.Boolean, default=False)
    has_seen_guide = db.Column(db.Boolean, default=False)

ROLE_HIERARCHY = {
    "admin": 6,
    "director": 5,
    "manager": 4,
    "team_lead": 3,
    "qa": 2,
    "employee": 2
}

def can_assign_role(current_role, target_role):
    return ROLE_HIERARCHY.get(current_role, 0) > ROLE_HIERARCHY.get(target_role, 0)