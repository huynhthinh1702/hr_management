"""add performance indexes and timestamps

Revision ID: b9f6a2c7d4e1
Revises: 6e22451093ec
Create Date: 2026-05-13 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b9f6a2c7d4e1"
down_revision = "6e22451093ec"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "task",
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.add_column(
        "sub_task",
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index("ix_task_active_status", "task", ["is_deleted", "status"], unique=False)
    op.create_index("ix_task_created_by_status", "task", ["created_by", "status"], unique=False)
    op.create_index("ix_task_deadline_status", "task", ["deadline", "status"], unique=False)
    op.create_index("ix_task_created_at", "task", ["created_at"], unique=False)

    op.create_index("ix_subtask_task_status", "sub_task", ["task_id", "status"], unique=False)
    op.create_index("ix_subtask_created_by_status", "sub_task", ["created_by", "status"], unique=False)
    op.create_index("ix_subtask_created_at", "sub_task", ["created_at"], unique=False)

    op.create_index(
        "ix_notification_user_read_created",
        "notification",
        ["user_id", "is_read", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_notification_user_type_task",
        "notification",
        ["user_id", "type", "task_id"],
        unique=False,
    )

    op.create_index(
        "ix_activity_task_subtask_created",
        "activity_log",
        ["task_id", "subtask_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_activity_task_action_created",
        "activity_log",
        ["task_id", "action", "created_at"],
        unique=False,
    )
    op.create_index("ix_activity_user_created", "activity_log", ["user_id", "created_at"], unique=False)

    op.create_index(
        "ix_comment_task_subtask_created",
        "comment",
        ["task_id", "subtask_id", "created_at"],
        unique=False,
    )
    op.create_index("ix_comment_user_created", "comment", ["user_id", "created_at"], unique=False)

    op.create_index(
        "ix_issue_task_status_created",
        "issue",
        ["task_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_issue_subtask_status_created",
        "issue",
        ["subtask_id", "status", "created_at"],
        unique=False,
    )
    op.create_index("ix_issue_created_by_created", "issue", ["created_by", "created_at"], unique=False)

    op.create_index(
        "ix_attachment_task_subtask_created",
        "task_attachment",
        ["task_id", "subtask_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_attachment_uploaded_by_created",
        "task_attachment",
        ["uploaded_by", "created_at"],
        unique=False,
    )

    op.create_index("ix_user_role_locked", "user", ["role", "is_locked"], unique=False)
    op.create_index("ix_user_full_name", "user", ["full_name"], unique=False)

    op.create_index("ix_task_users_user_task", "task_users", ["user_id", "task_id"], unique=False)
    op.create_index("ix_task_users_task_user", "task_users", ["task_id", "user_id"], unique=False)
    op.create_index("ix_subtask_users_user_subtask", "subtask_users", ["user_id", "subtask_id"], unique=False)
    op.create_index("ix_subtask_users_subtask_user", "subtask_users", ["subtask_id", "user_id"], unique=False)


def downgrade():
    op.drop_index("ix_subtask_users_subtask_user", table_name="subtask_users")
    op.drop_index("ix_subtask_users_user_subtask", table_name="subtask_users")
    op.drop_index("ix_task_users_task_user", table_name="task_users")
    op.drop_index("ix_task_users_user_task", table_name="task_users")
    op.drop_index("ix_user_full_name", table_name="user")
    op.drop_index("ix_user_role_locked", table_name="user")
    op.drop_index("ix_attachment_uploaded_by_created", table_name="task_attachment")
    op.drop_index("ix_attachment_task_subtask_created", table_name="task_attachment")
    op.drop_index("ix_issue_created_by_created", table_name="issue")
    op.drop_index("ix_issue_subtask_status_created", table_name="issue")
    op.drop_index("ix_issue_task_status_created", table_name="issue")
    op.drop_index("ix_comment_user_created", table_name="comment")
    op.drop_index("ix_comment_task_subtask_created", table_name="comment")
    op.drop_index("ix_activity_user_created", table_name="activity_log")
    op.drop_index("ix_activity_task_action_created", table_name="activity_log")
    op.drop_index("ix_activity_task_subtask_created", table_name="activity_log")
    op.drop_index("ix_notification_user_type_task", table_name="notification")
    op.drop_index("ix_notification_user_read_created", table_name="notification")
    op.drop_index("ix_subtask_created_at", table_name="sub_task")
    op.drop_index("ix_subtask_created_by_status", table_name="sub_task")
    op.drop_index("ix_subtask_task_status", table_name="sub_task")
    op.drop_index("ix_task_created_at", table_name="task")
    op.drop_index("ix_task_deadline_status", table_name="task")
    op.drop_index("ix_task_created_by_status", table_name="task")
    op.drop_index("ix_task_active_status", table_name="task")
    op.drop_column("sub_task", "created_at")
    op.drop_column("task", "created_at")
