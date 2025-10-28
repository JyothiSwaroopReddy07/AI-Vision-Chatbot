"""update starred messages schema

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-10-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing columns to starred_messages table
    op.add_column('starred_messages', sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('starred_messages', sa.Column('question', sa.Text(), nullable=True))
    op.add_column('starred_messages', sa.Column('answer', sa.Text(), nullable=True))
    
    # Update existing rows to populate session_id from chat_messages
    op.execute("""
        UPDATE starred_messages sm
        SET session_id = cm.session_id
        FROM chat_messages cm
        WHERE sm.message_id = cm.id
    """)
    
    # Update existing rows to populate question and answer from chat_messages
    op.execute("""
        UPDATE starred_messages sm
        SET question = COALESCE(
            (SELECT content FROM chat_messages 
             WHERE session_id = sm.session_id 
             AND created_at < cm.created_at 
             AND role = 'user' 
             ORDER BY created_at DESC LIMIT 1),
            CASE WHEN cm.role = 'user' THEN cm.content ELSE NULL END
        ),
        answer = CASE 
            WHEN cm.role = 'assistant' THEN cm.content
            ELSE (SELECT content FROM chat_messages 
                  WHERE session_id = sm.session_id 
                  AND created_at > cm.created_at 
                  AND role = 'assistant' 
                  ORDER BY created_at ASC LIMIT 1)
        END
        FROM chat_messages cm
        WHERE sm.message_id = cm.id
    """)
    
    # Make session_id and answer NOT NULL after populating
    op.alter_column('starred_messages', 'session_id', nullable=False)
    op.alter_column('starred_messages', 'answer', nullable=False)
    
    # Add foreign key constraint for session_id
    op.create_foreign_key(
        'fk_starred_messages_session_id_chat_sessions',
        'starred_messages', 'chat_sessions',
        ['session_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Create index on session_id
    op.create_index(op.f('ix_starred_messages_session_id'), 'starred_messages', ['session_id'], unique=False)
    
    # Convert tags from Text to ARRAY(String)
    # First, convert existing comma-separated tags to array
    op.execute("""
        UPDATE starred_messages
        SET tags = string_to_array(NULLIF(tags, ''), ',')
        WHERE tags IS NOT NULL AND tags != ''
    """)
    
    # Change column type
    op.alter_column('starred_messages', 'tags',
        type_=postgresql.ARRAY(sa.String()),
        postgresql_using='tags::text[]'
    )


def downgrade() -> None:
    # Convert tags back from ARRAY to Text
    op.execute("""
        UPDATE starred_messages
        SET tags = array_to_string(tags, ',')
        WHERE tags IS NOT NULL
    """)
    
    op.alter_column('starred_messages', 'tags',
        type_=sa.Text(),
        postgresql_using='tags::text'
    )
    
    # Drop index
    op.drop_index(op.f('ix_starred_messages_session_id'), table_name='starred_messages')
    
    # Drop foreign key
    op.drop_constraint('fk_starred_messages_session_id_chat_sessions', 'starred_messages', type_='foreignkey')
    
    # Drop columns
    op.drop_column('starred_messages', 'answer')
    op.drop_column('starred_messages', 'question')
    op.drop_column('starred_messages', 'session_id')

