"""Update feed event schema

Revision ID: e62259a99df0
Revises: 317ddf3509cb
Create Date: 2020-10-27 15:49:06.283799

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e62259a99df0'
down_revision = '317ddf3509cb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('feed_event',
    sa.Column('device_hid', sa.Text(), nullable=False),
    sa.Column('start_time', sa.Integer(), nullable=False),
    sa.Column('end_time', sa.Integer(), server_default='0', nullable=False),
    sa.Column('timestamp', sa.Integer(), nullable=False),
    sa.Column('pour', sa.Integer(), server_default='0', nullable=False),
    sa.Column('full', sa.Integer(), server_default='0', nullable=False),
    sa.Column('grams_expected', sa.Integer(), server_default='0', nullable=False),
    sa.Column('grams_actual', sa.Integer(), server_default='0', nullable=False),
    sa.Column('hopper_start', sa.Integer(), server_default='0', nullable=False),
    sa.Column('hopper_end', sa.Integer(), server_default='0', nullable=False),
    sa.Column('source', sa.Integer(), server_default='0', nullable=True),
    sa.Column('fail', sa.Boolean(), server_default=sa.text('0'), nullable=False),
    sa.Column('trip', sa.Boolean(), server_default=sa.text('0'), nullable=True),
    sa.Column('lrg', sa.Boolean(), server_default=sa.text('0'), nullable=True),
    sa.Column('vol', sa.Boolean(), server_default=sa.text('0'), nullable=True),
    sa.Column('bowl', sa.Boolean(), server_default=sa.text('0'), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('recipe_id', sa.Text(), server_default='UNKNOWN', nullable=False),
    sa.ForeignKeyConstraint(['device_hid'], ['kronos_device.hid'], ),
    sa.PrimaryKeyConstraint('device_hid', 'start_time')
    )
    op.drop_table('feeding_event')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('feeding_event',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('timestamp', sa.INTEGER(), nullable=False),
    sa.Column('device_hid', sa.TEXT(), nullable=False),
    sa.ForeignKeyConstraint(['device_hid'], ['kronos_device.hid'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_table('feed_event')
    # ### end Alembic commands ###
