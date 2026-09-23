"""Apply local default sport artwork to sports and starter resources.

Revision ID: 20260923_0006
Revises: 20260923_0005
"""
from alembic import op
import sqlalchemy as sa

revision="20260923_0006"
down_revision="20260923_0005"
branch_labels=None
depends_on=None

ART={
    "football":"/static/img/sports/football.svg",
    "basketball":"/static/img/sports/basketball.svg",
    "tennis":"/static/img/sports/tennis.svg",
    "volleyball":"/static/img/sports/volleyball.svg",
    "gymnastics":"/static/img/sports/gymnastics.svg",
    "table-tennis":"/static/img/sports/table-tennis.svg",
}

def upgrade():
    bind=op.get_bind()
    if "sports" in sa.inspect(bind).get_table_names():
        for key,url in ART.items():
            bind.execute(sa.text(
                "UPDATE sports SET image_url=:url "
                "WHERE key=:key AND (image_url IS NULL OR image_url='')"
            ),{"key":key,"url":url})
    if "resources" in sa.inspect(bind).get_table_names() and "sports" in sa.inspect(bind).get_table_names():
        for key,url in ART.items():
            bind.execute(sa.text(
                "UPDATE resources r SET image_url=:url "
                "FROM sports s "
                "WHERE r.sport_id=s.id AND s.key=:key "
                "AND (r.image_url IS NULL OR r.image_url='')"
            ),{"key":key,"url":url})

def downgrade():
    bind=op.get_bind()
    if "resources" in sa.inspect(bind).get_table_names():
        bind.execute(sa.text("UPDATE resources SET image_url=NULL WHERE image_url LIKE '/static/img/sports/%.svg'"))
    if "sports" in sa.inspect(bind).get_table_names():
        bind.execute(sa.text("UPDATE sports SET image_url=NULL WHERE image_url LIKE '/static/img/sports/%.svg'"))
