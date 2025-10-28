"""add_msigdb_tables

Revision ID: 2991547659fb
Revises: b2c3d4e5f6g7
Create Date: 2025-10-28 03:10:23.819285

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision = '2991547659fb'
down_revision = 'b2c3d4e5f6g7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create msigdb_queries table
    op.create_table(
        'msigdb_queries',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('genes_list', JSON(), nullable=False),
        sa.Column('species', sa.String(20), nullable=False),
        sa.Column('search_type', sa.String(20), nullable=False),
        sa.Column('collections', JSON(), nullable=True),
        sa.Column('num_results', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    
    # Create indexes for msigdb_queries
    op.create_index('ix_msigdb_queries_user_id', 'msigdb_queries', ['user_id'])
    op.create_index('ix_msigdb_queries_created_at', 'msigdb_queries', ['created_at'])
    
    # Create msigdb_results table
    op.create_table(
        'msigdb_results',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('query_id', UUID(as_uuid=True), sa.ForeignKey('msigdb_queries.id', ondelete='CASCADE'), nullable=False),
        sa.Column('gene_set_id', sa.String(100), nullable=False),
        sa.Column('gene_set_name', sa.String(500), nullable=False),
        sa.Column('collection', sa.String(50), nullable=False),
        sa.Column('sub_collection', sa.String(100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('species', sa.String(20), nullable=False),
        sa.Column('gene_set_size', sa.Integer(), nullable=False),
        sa.Column('overlap_count', sa.Integer(), nullable=False),
        sa.Column('overlap_percentage', sa.Float(), nullable=False),
        sa.Column('p_value', sa.Float(), nullable=True),
        sa.Column('adjusted_p_value', sa.Float(), nullable=True),
        sa.Column('odds_ratio', sa.Float(), nullable=True),
        sa.Column('matched_genes', JSON(), nullable=False),
        sa.Column('all_genes', JSON(), nullable=True),
        sa.Column('msigdb_url', sa.String(500), nullable=True),
        sa.Column('external_url', sa.String(500), nullable=True),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    
    # Create indexes for msigdb_results
    op.create_index('ix_msigdb_results_query_id', 'msigdb_results', ['query_id'])
    op.create_index('ix_msigdb_results_collection', 'msigdb_results', ['collection'])
    op.create_index('ix_msigdb_results_overlap_count', 'msigdb_results', ['overlap_count'])
    op.create_index('ix_msigdb_results_p_value', 'msigdb_results', ['p_value'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_msigdb_results_p_value', 'msigdb_results')
    op.drop_index('ix_msigdb_results_overlap_count', 'msigdb_results')
    op.drop_index('ix_msigdb_results_collection', 'msigdb_results')
    op.drop_index('ix_msigdb_results_query_id', 'msigdb_results')
    
    op.drop_index('ix_msigdb_queries_created_at', 'msigdb_queries')
    op.drop_index('ix_msigdb_queries_user_id', 'msigdb_queries')
    
    # Drop tables
    op.drop_table('msigdb_results')
    op.drop_table('msigdb_queries')

