"""empty message

Revision ID: f151d8d44b84
Revises: 73dd0fddab62
Create Date: 2016-11-28 15:39:17.695033

"""

# revision identifiers, used by Alembic.
revision = 'f151d8d44b84'
down_revision = '73dd0fddab62'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'is_active')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('is_active', sa.BOOLEAN(), autoincrement=False, nullable=True))
    ### end Alembic commands ###