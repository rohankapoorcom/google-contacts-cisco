"""add_display_name_validation

Revision ID: f68f00bdffe0
Revises: 3b6d750552da
Create Date: 2026-01-09 22:00:12.281038

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f68f00bdffe0'
down_revision: Union[str, Sequence[str], None] = '3b6d750552da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.
    
    1. Clean up any existing contacts with empty or whitespace-only display_name
    2. Add check constraint to prevent future empty display_name values
    """
    # First, update any existing contacts with empty or whitespace-only display_name
    # Set them to "Unnamed Contact" as a fallback
    op.execute("""
        UPDATE contacts 
        SET display_name = 'Unnamed Contact'
        WHERE display_name = '' 
           OR display_name IS NULL 
           OR trim(display_name) = ''
    """)
    
    # Add check constraint to ensure display_name is not empty or only whitespace
    # PostgreSQL/SQLite: Use length(trim(display_name)) > 0
    op.create_check_constraint(
        'ck_display_name_not_empty',
        'contacts',
        'length(trim(display_name)) > 0'
    )


def downgrade() -> None:
    """Downgrade schema.
    
    Remove the check constraint added in upgrade.
    """
    op.drop_constraint('ck_display_name_not_empty', 'contacts', type_='check')
