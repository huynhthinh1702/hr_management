import os

from flask_socketio import SocketIO, join_room, leave_room

from services.notification_service import user_notification_room


def init_socketio(app):
    redis_url = os.getenv("REDIS_URL")
    async_mode = os.getenv("SOCKETIO_ASYNC_MODE", "threading")
    return SocketIO(
        app,
        async_mode=async_mode,
        cors_allowed_origins=os.getenv("SOCKETIO_CORS_ORIGINS", "*"),
        message_queue=redis_url,
        manage_session=False,
        ping_interval=25,
        ping_timeout=20,
    )


def join_global_if_authenticated(session):
    if "user_id" in session:
        join_room("global")
        join_room(user_notification_room(session["user_id"]))


def emit_global(socketio, kind="data_changed", task_id=None):
    payload = {"kind": kind}
    if task_id is not None:
        payload["task_id"] = task_id
    socketio.emit("global_changed", payload, room="global")


def emit_task_live(socketio, task_id, sections=None):
    payload = {"task_id": task_id}
    if sections:
        payload["sections"] = sections
    socketio.emit("task_live_update", payload, room=f"task_{task_id}")


def emit_task_removed(socketio, task_id):
    socketio.emit("task_removed", {"task_id": task_id}, room=f"task_{task_id}")


def join_task_room(task_id):
    join_room(f"task_{task_id}")


def leave_task_room(task_id):
    leave_room(f"task_{task_id}")

