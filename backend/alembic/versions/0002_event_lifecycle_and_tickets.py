"""event lifecycle, categories, registration deadline and tickets

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-12 19:24:31.771183

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_EVENT_STATUSES = ('SUBMITTED', 'IN_PROGRESS', 'COMPLETED')
EVENT_CATEGORIES = (
    'WORKSHOP', 'CONFERENCE', 'TRAINING', 'SOCIAL', 'VOLUNTEERING', 'COMPETITION', 'OTHER'
)


def upgrade() -> None:
    # New lifecycle states. ADD VALUE must run outside the migration transaction.
    with op.get_context().autocommit_block():
        for value in NEW_EVENT_STATUSES:
            op.execute(f"ALTER TYPE event_status ADD VALUE IF NOT EXISTS '{value}'")

    event_category = postgresql.ENUM(*EVENT_CATEGORIES, name='event_category')
    event_category.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'events',
        sa.Column(
            'category',
            postgresql.ENUM(*EVENT_CATEGORIES, name='event_category', create_type=False),
            server_default='OTHER',
            nullable=False,
        ),
    )
    op.add_column(
        'events', sa.Column('registration_deadline', sa.DateTime(timezone=True), nullable=True)
    )

    op.create_table('tickets',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('registration_id', sa.Uuid(), nullable=False),
    sa.Column('event_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('code', sa.String(length=64), nullable=False),
    sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('checked_in_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('checked_in_by_id', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['checked_in_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.ForeignKeyConstraint(['registration_id'], ['registrations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code'),
    sa.UniqueConstraint('registration_id')
    )
    op.create_index(op.f('ix_tickets_event_id'), 'tickets', ['event_id'], unique=False)
    op.create_index(op.f('ix_tickets_user_id'), 'tickets', ['user_id'], unique=False)

    # Existing confirmed registrations get a ticket too.
    op.execute(
        """
        INSERT INTO tickets (id, registration_id, event_id, user_id, code, issued_at)
        SELECT gen_random_uuid(), r.id, r.event_id, r.user_id,
               replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', ''),
               now()
        FROM registrations r
        WHERE r.status = 'CONFIRMED'
        """
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_tickets_user_id'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_event_id'), table_name='tickets')
    op.drop_table('tickets')
    op.drop_column('events', 'registration_deadline')
    op.drop_column('events', 'category')
    postgresql.ENUM(name='event_category').drop(op.get_bind(), checkfirst=True)
    # Postgres cannot drop enum values; move events in new states back to old ones.
    op.execute("UPDATE events SET status = 'DRAFT' WHERE status = 'SUBMITTED'")
    op.execute(
        "UPDATE events SET status = 'PUBLISHED' WHERE status IN ('IN_PROGRESS', 'COMPLETED')"
    )
