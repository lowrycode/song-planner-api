"""Change User role column from Enum to Integer with data migration using temp column"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '7afcaed7ddac'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add temporary integer column 'role_int' nullable for transition
    op.add_column('users', sa.Column('role_int', sa.Integer(), nullable=True))

    # 2. Copy and convert enum role string values to integers in 'role_int'
    op.execute("""
        UPDATE users SET role_int =
            CASE role
                WHEN 'unapproved' THEN 0
                WHEN 'normal' THEN 1
                WHEN 'editor' THEN 2
                WHEN 'admin' THEN 3
            END
    """)

    # 3. Drop old enum 'role' column
    op.drop_column('users', 'role')

    # 4. Rename 'role_int' to 'role' and set NOT NULL
    op.alter_column('users', 'role_int', new_column_name='role', nullable=False)

    # 5. Drop the PostgreSQL enum type
    op.execute("DROP TYPE IF EXISTS userrole;")


def downgrade() -> None:
    # 1. Recreate enum type 'userrole'
    userrole_enum = postgresql.ENUM('unapproved', 'normal', 'editor', 'admin', name='userrole')
    userrole_enum.create(op.get_bind(), checkfirst=True)

    # 2. Add temporary enum column 'role_enum' nullable for transition
    op.add_column('users', sa.Column('role_enum', userrole_enum, nullable=True))

    # 3. Convert integer roles back to enum strings in 'role_enum'
    op.execute("""
        UPDATE users SET role_enum =
            CASE role
                WHEN 0 THEN 'unapproved'
                WHEN 1 THEN 'normal'
                WHEN 2 THEN 'editor'
                WHEN 3 THEN 'admin'
            END
    """)

    # 4. Drop integer 'role' column
    op.drop_column('users', 'role')

    # 5. Rename 'role_enum' to 'role' and set NOT NULL
    op.alter_column('users', 'role_enum', new_column_name='role', nullable=False)
