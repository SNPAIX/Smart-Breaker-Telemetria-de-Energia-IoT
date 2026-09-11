"""add_alerts_and_safety_events

Revision ID: a1c2f6e9b3d0
Revises: 'f7f813c4415b'
Create Date: 2026-09-10 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1c2f6e9b3d0'
down_revision: str | None = 'f7f813c4415b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'devices',
        sa.Column(
            'auto_cutoff_enabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('device_id', sa.String(length=50), sa.ForeignKey('devices.id'), index=True),
        sa.Column('power', sa.Float(), nullable=False),
        sa.Column('expected_power', sa.Float(), nullable=False),
        sa.Column('detector', sa.String(length=50), nullable=False),
        sa.Column('acknowledged', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        'safety_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('device_id', sa.String(length=50), sa.ForeignKey('devices.id'), index=True),
        sa.Column(
            'event_type', sa.String(length=50), nullable=False,
            server_default='CRITICAL_OVERLOAD',
        ),
        sa.Column('current', sa.Float(), nullable=False),
        sa.Column('max_current_threshold', sa.Float(), nullable=False),
        sa.Column(
            'action_taken', sa.String(length=50), nullable=False,
            server_default='SHUTDOWN_ORDER_ISSUED',
        ),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table('safety_events')
    op.drop_table('alerts')
    op.drop_column('devices', 'auto_cutoff_enabled')
