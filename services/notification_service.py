from sqlalchemy import func

from database import db
from models.notification import Notification


NOTIFICATION_LIST_LIMIT = 8


def user_notification_room(user_id):
    return f"user:{int(user_id)}:notifications"


def get_notification_summary(user_id, limit=NOTIFICATION_LIST_LIMIT):
    if not user_id:
        return {"unread_count": 0, "items": []}

    unread_count = (
        db.session.query(func.count(Notification.id))
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .scalar()
        or 0
    )
    items = (
        Notification.query.filter_by(user_id=user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
        .all()
    )
    return {"unread_count": int(unread_count), "items": items}


def serialize_notification(notification, formatter):
    return {
        "id": notification.id,
        "title": notification.title,
        "message": notification.message,
        "url": notification.url or "#",
        "is_read": bool(notification.is_read),
        "created_at": formatter(notification.created_at),
    }


def serialize_notification_summary(user_id, formatter):
    summary = get_notification_summary(user_id)
    return {
        "unread_count": summary["unread_count"],
        "items": [serialize_notification(item, formatter) for item in summary["items"]],
    }


def create_notification(
    user_id,
    type_,
    title,
    message,
    task_id=None,
    url=None,
    actor_id=None,
    dedupe=False,
):
    if not user_id:
        return None

    if dedupe:
        existing = (
            Notification.query.filter_by(
                user_id=user_id,
                type=type_,
                task_id=task_id,
                is_read=False,
            )
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .first()
        )
        if existing:
            return None

    notification = Notification(
        user_id=user_id,
        actor_id=actor_id,
        task_id=task_id,
        type=type_,
        title=title,
        message=message,
        url=url,
    )
    db.session.add(notification)
    return notification


def emit_notification_created(socketio, notification, formatter):
    if not notification or not getattr(notification, "id", None):
        return

    socketio.emit(
        "notification:new",
        {
            "notification": serialize_notification(notification, formatter),
            "unread_count": get_notification_summary(notification.user_id)["unread_count"],
        },
        room=user_notification_room(notification.user_id),
    )


def emit_notification_sync(socketio, user_id, formatter):
    if not user_id:
        return
    socketio.emit(
        "notification:sync",
        serialize_notification_summary(user_id, formatter),
        room=user_notification_room(user_id),
    )
