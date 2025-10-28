"""Add bookmarks and starred messages

Revision ID: a1b2c3d4e5f6
Revises: 628f507433db
Create Date: 2025-10-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '628f507433db'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create bookmark_folders table
    op.create_table('bookmark_folders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bookmark_folders_user_id'), 'bookmark_folders', ['user_id'], unique=False)
    
    # Create chat_bookmarks table
    op.create_table('chat_bookmarks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('folder_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['folder_id'], ['bookmark_folders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('folder_id', 'session_id', name='uq_folder_session')
    )
    op.create_index(op.f('ix_chat_bookmarks_folder_id'), 'chat_bookmarks', ['folder_id'], unique=False)
    op.create_index(op.f('ix_chat_bookmarks_session_id'), 'chat_bookmarks', ['session_id'], unique=False)
    
    # Create starred_messages table
    op.create_table('starred_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'message_id', name='uq_user_message_star')
    )
    op.create_index(op.f('ix_starred_messages_message_id'), 'starred_messages', ['message_id'], unique=False)
    op.create_index(op.f('ix_starred_messages_user_id'), 'starred_messages', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_starred_messages_user_id'), table_name='starred_messages')
    op.drop_index(op.f('ix_starred_messages_message_id'), table_name='starred_messages')
    op.drop_table('starred_messages')
    
    op.drop_index(op.f('ix_chat_bookmarks_session_id'), table_name='chat_bookmarks')
    op.drop_index(op.f('ix_chat_bookmarks_folder_id'), table_name='chat_bookmarks')
    op.drop_table('chat_bookmarks')
    
    op.drop_index(op.f('ix_bookmark_folders_user_id'), table_name='bookmark_folders')
    op.drop_table('bookmark_folders')

