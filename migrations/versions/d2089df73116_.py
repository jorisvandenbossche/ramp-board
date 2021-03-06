"""empty message

Revision ID: d2089df73116
Revises: b00d69bcda81
Create Date: 2017-08-25 11:24:12.684803

"""

# revision identifiers, used by Alembic.
revision = 'd2089df73116'
down_revision = 'b00d69bcda81'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('events', sa.Column('title', sa.String(), nullable=False, server_default='test event'))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('events', 'title')
    ### end Alembic commands ###

