"""notifications, announcements, post-event feedback and event tasks

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-15 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EVENT_TASK_STATUSES = ('TODO', 'IN_PROGRESS', 'DONE')


def upgrade() -> None:
    op.create_table('notifications',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('event_id', sa.Uuid(), nullable=True),
    sa.Column('type', sa.String(length=40), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('dedup_key', sa.String(length=120), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('emailed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'dedup_key', name='uq_notifications_user_dedup')
    )
    op.create_index(op.f('ix_notifications_event_id'), 'notifications', ['event_id'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)

    op.create_table('event_announcements',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('event_id', sa.Uuid(), nullable=False),
    sa.Column('author_id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_announcements_event_id'), 'event_announcements', ['event_id'], unique=False)

    op.create_table('event_feedback',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('event_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('rating', sa.Integer(), nullable=False),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('rating BETWEEN 1 AND 5', name='ck_event_feedback_rating'),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('event_id', 'user_id', name='uq_event_feedback_event_user')
    )
    op.create_index(op.f('ix_event_feedback_event_id'), 'event_feedback', ['event_id'], unique=False)

    task_status = postgresql.ENUM(*EVENT_TASK_STATUSES, name='event_task_status')
    task_status.create(op.get_bind(), checkfirst=True)
    op.create_table('event_tasks',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('event_id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('assignee_id', sa.Uuid(), nullable=True),
    sa.Column(
        'status',
        postgresql.ENUM(*EVENT_TASK_STATUSES, name='event_task_status', create_type=False),
        nullable=False,
    ),
    sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_by_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_tasks_assignee_id'), 'event_tasks', ['assignee_id'], unique=False)
    op.create_index(op.f('ix_event_tasks_event_id'), 'event_tasks', ['event_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_event_tasks_event_id'), table_name='event_tasks')
    op.drop_index(op.f('ix_event_tasks_assignee_id'), table_name='event_tasks')
    op.drop_table('event_tasks')
    postgresql.ENUM(name='event_task_status').drop(op.get_bind(), checkfirst=True)
    op.drop_index(op.f('ix_event_feedback_event_id'), table_name='event_feedback')
    op.drop_table('event_feedback')
    op.drop_index(op.f('ix_event_announcements_event_id'), table_name='event_announcements')
    op.drop_table('event_announcements')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_event_id'), table_name='notifications')
    op.drop_table('notifications')
