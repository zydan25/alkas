"""baseline schema from SQLAlchemy metadata

Revision ID: 20260922_0001
Revises:
Create Date: 2026-09-22 19:45:00
"""

from alembic import op

revision = "20260922_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # booking_allocations uses EXCLUDE USING gist with an INTEGER equality
    # operator. PostgreSQL supplies the required GiST operator class through
    # the btree_gist extension.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    from app import create_app
    from app.extensions import db

    app = create_app()
    with app.app_context():
        db.metadata.create_all(bind=op.get_bind())


def downgrade():
    # Baseline downgrade is intentionally non-destructive.
    pass
