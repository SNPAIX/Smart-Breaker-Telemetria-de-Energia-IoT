"""v2 schema: sites, site_members, device profiles/credentials, commands, events, notifications, tariffs, predictions

Revision ID: ac6b3131044c
Revises: a1c2f6e9b3d0
Create Date: 2026-09-14 02:16:57.772838

Reescrita a mano sobre la salida de `alembic revision --autogenerate`: el
diff automático intentaba alterar `devices.id` de VARCHAR a Integer en el
mismo paso en que crea tablas nuevas cuya FK a `devices.id` ya asume el tipo
Integer — union de operaciones que Postgres no puede aplicar en ese orden.
Sin datos de producción que preservar (proyecto nuevo), se opta por la
migración DROP/CREATE limpia ya documentada en roadmap/01-gap-analysis.md:
se sueltan las tablas viejas que dependían del `Device` anterior y se crea
el esquema v2 completo desde cero.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ac6b3131044c'
down_revision: str | None = 'a1c2f6e9b3d0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Soltar todo lo que dependía del Device anterior (sin backfill: no
    # hay datos de producción que preservar) ---
    op.drop_index(op.f('ix_safety_events_device_id'), table_name='safety_events')
    op.drop_table('safety_events')
    op.drop_index(op.f('ix_alerts_device_id'), table_name='alerts')
    op.drop_table('alerts')
    op.drop_index(op.f('ix_readings_device_id'), table_name='readings')
    op.drop_table('readings')
    op.drop_table('devices')
    op.drop_table('device_groups')

    # --- Esquema v2 ---
    op.create_table('sites',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('kind', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('device_profiles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('site_id', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('max_current_a', sa.Float(), nullable=False),
    sa.Column('auto_cutoff_enabled', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_device_profiles_site_id'), 'device_profiles', ['site_id'], unique=False)

    op.create_table('devices',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('public_id', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('site_id', sa.Integer(), nullable=True),
    sa.Column('profile_id', sa.Integer(), nullable=True),
    sa.Column('desired_state', sa.String(length=10), nullable=False),
    sa.Column('actual_state', sa.String(length=10), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('firmware_version', sa.String(length=50), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['device_profiles.id'], ),
    sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_devices_profile_id'), 'devices', ['profile_id'], unique=False)
    op.create_index(op.f('ix_devices_public_id'), 'devices', ['public_id'], unique=True)
    op.create_index(op.f('ix_devices_site_id'), 'devices', ['site_id'], unique=False)

    op.create_table('device_credentials',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device_id', sa.Integer(), nullable=False),
    sa.Column('secret_hash', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_device_credentials_device_id'), 'device_credentials', ['device_id'], unique=True)

    op.create_table('telemetry_readings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device_id', sa.Integer(), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('voltage', sa.Float(), nullable=False),
    sa.Column('current', sa.Float(), nullable=False),
    sa.Column('power', sa.Float(), nullable=False),
    sa.Column('frequency', sa.Float(), nullable=False),
    sa.Column('power_factor', sa.Float(), nullable=False),
    sa.Column('energy', sa.Float(), nullable=False),
    sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_telemetry_readings_device_id'), 'telemetry_readings', ['device_id'], unique=False)

    op.create_table('commands',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device_id', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('acked_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commands_device_id'), 'commands', ['device_id'], unique=False)
    op.create_index(op.f('ix_commands_status'), 'commands', ['status'], unique=False)

    op.create_table('events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device_id', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_events_device_id'), 'events', ['device_id'], unique=False)
    op.create_index(op.f('ix_events_type'), 'events', ['type'], unique=False)

    op.create_table('anomaly_alerts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device_id', sa.Integer(), nullable=False),
    sa.Column('power', sa.Float(), nullable=False),
    sa.Column('expected_power', sa.Float(), nullable=False),
    sa.Column('detector', sa.String(length=50), nullable=False),
    sa.Column('acknowledged', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_anomaly_alerts_device_id'), 'anomaly_alerts', ['device_id'], unique=False)

    op.create_table('predictions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device_id', sa.Integer(), nullable=False),
    sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('horizon', sa.String(length=20), nullable=False),
    sa.Column('projected_kwh', sa.Float(), nullable=False),
    sa.Column('projected_cost', sa.Float(), nullable=False),
    sa.Column('method', sa.String(length=50), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_predictions_device_id'), 'predictions', ['device_id'], unique=False)

    op.create_table('site_members',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('site_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('site_id', 'user_id', name='uq_site_member')
    )
    op.create_index(op.f('ix_site_members_site_id'), 'site_members', ['site_id'], unique=False)
    op.create_index(op.f('ix_site_members_user_id'), 'site_members', ['user_id'], unique=False)

    op.create_table('tariffs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('site_id', sa.Integer(), nullable=False),
    sa.Column('currency', sa.String(length=10), nullable=False),
    sa.Column('price_per_kwh', sa.Float(), nullable=False),
    sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False),
    sa.Column('valid_to', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tariffs_site_id'), 'tariffs', ['site_id'], unique=False)

    op.create_table('notification_preferences',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('channel', sa.String(length=20), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'channel', name='uq_notification_preference')
    )
    op.create_index(op.f('ix_notification_preferences_user_id'), 'notification_preferences', ['user_id'], unique=False)

    op.create_table('notifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('event_id', sa.Integer(), nullable=True),
    sa.Column('channel', sa.String(length=20), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.String(length=1000), nullable=False),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_index(op.f('ix_notification_preferences_user_id'), table_name='notification_preferences')
    op.drop_table('notification_preferences')
    op.drop_index(op.f('ix_tariffs_site_id'), table_name='tariffs')
    op.drop_table('tariffs')
    op.drop_index(op.f('ix_site_members_user_id'), table_name='site_members')
    op.drop_index(op.f('ix_site_members_site_id'), table_name='site_members')
    op.drop_table('site_members')
    op.drop_index(op.f('ix_predictions_device_id'), table_name='predictions')
    op.drop_table('predictions')
    op.drop_index(op.f('ix_anomaly_alerts_device_id'), table_name='anomaly_alerts')
    op.drop_table('anomaly_alerts')
    op.drop_index(op.f('ix_events_type'), table_name='events')
    op.drop_index(op.f('ix_events_device_id'), table_name='events')
    op.drop_table('events')
    op.drop_index(op.f('ix_commands_status'), table_name='commands')
    op.drop_index(op.f('ix_commands_device_id'), table_name='commands')
    op.drop_table('commands')
    op.drop_index(op.f('ix_telemetry_readings_device_id'), table_name='telemetry_readings')
    op.drop_table('telemetry_readings')
    op.drop_index(op.f('ix_device_credentials_device_id'), table_name='device_credentials')
    op.drop_table('device_credentials')
    op.drop_index(op.f('ix_devices_site_id'), table_name='devices')
    op.drop_index(op.f('ix_devices_public_id'), table_name='devices')
    op.drop_index(op.f('ix_devices_profile_id'), table_name='devices')
    op.drop_table('devices')
    op.drop_index(op.f('ix_device_profiles_site_id'), table_name='device_profiles')
    op.drop_table('device_profiles')
    op.drop_table('sites')

    # --- Recrear el esquema v1 tal cual estaba en a1c2f6e9b3d0 ---
    op.create_table('devices',
    sa.Column('id', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
    sa.Column('name', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('owner_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('group_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('max_current_threshold', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.Column('auto_cutoff_enabled', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('is_active', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('relay_status', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('devices_pkey'))
    )
    op.create_table('device_groups',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('description', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('device_groups_pkey')),
    sa.UniqueConstraint('name', name=op.f('device_groups_name_key'))
    )
    op.create_foreign_key(op.f('devices_group_id_fkey'), 'devices', 'device_groups', ['group_id'], ['id'])
    op.create_foreign_key(op.f('devices_owner_id_fkey'), 'devices', 'users', ['owner_id'], ['id'])

    op.create_table('readings',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('device_id', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
    sa.Column('voltage', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.Column('current', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.Column('power', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.Column('recorded_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('frequency', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.Column('power_factor', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.Column('energy', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], name=op.f('readings_device_id_fkey')),
    sa.PrimaryKeyConstraint('id', name=op.f('readings_pkey'))
    )
    op.create_index(op.f('ix_readings_device_id'), 'readings', ['device_id'], unique=False)

    op.create_table('alerts',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('device_id', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.Column('power', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.Column('expected_power', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.Column('detector', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
    sa.Column('acknowledged', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], name=op.f('alerts_device_id_fkey')),
    sa.PrimaryKeyConstraint('id', name=op.f('alerts_pkey'))
    )
    op.create_index(op.f('ix_alerts_device_id'), 'alerts', ['device_id'], unique=False)

    op.create_table('safety_events',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('device_id', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.Column('event_type', sa.VARCHAR(length=50), server_default=sa.text("'CRITICAL_OVERLOAD'::character varying"), autoincrement=False, nullable=False),
    sa.Column('current', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.Column('max_current_threshold', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.Column('action_taken', sa.VARCHAR(length=50), server_default=sa.text("'SHUTDOWN_ORDER_ISSUED'::character varying"), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], name=op.f('safety_events_device_id_fkey')),
    sa.PrimaryKeyConstraint('id', name=op.f('safety_events_pkey'))
    )
    op.create_index(op.f('ix_safety_events_device_id'), 'safety_events', ['device_id'], unique=False)
