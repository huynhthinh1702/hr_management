from flask_socketio import SocketIO, join_room, leave_room


def init_socketio(app):
    return SocketIO(app, async_mode="threading", cors_allowed_origins="*")


def join_global_if_authenticated(session):
    if "user_id" in session:
        join_room("global")


def emit_global(socketio, kind="data_changed", task_id=None):
    payload = {"kind": kind}
    if task_id is not None:
        payload["task_id"] = task_id
    socketio.emit("global_changed", payload, room="global")


def emit_task_live(socketio, task_id):
    socketio.emit("task_live_update", {"task_id": task_id}, room=f"task_{task_id}")


def emit_task_removed(socketio, task_id):
    socketio.emit("task_removed", {"task_id": task_id}, room=f"task_{task_id}")


def join_task_room(task_id):
    join_room(f"task_{task_id}")


def leave_task_room(task_id):
    leave_room(f"task_{task_id}")

