"""Seed useful default sports resources without replacing existing data.

Revision ID: 20260923_0005
Revises: 20260923_0004
"""
from alembic import op
import sqlalchemy as sa

revision = "20260923_0005"
down_revision = "20260923_0004"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "sports" not in tables or "resources" not in tables or "venue_zones" not in tables:
        return

    zone_id = bind.execute(sa.text(
        "SELECT id FROM venue_zones WHERE is_active = TRUE ORDER BY id LIMIT 1"
    )).scalar()
    if not zone_id:
        venue_id = bind.execute(sa.text(
            "SELECT id FROM venues WHERE is_active = TRUE ORDER BY id LIMIT 1"
        )).scalar()
        if not venue_id and "venues" in tables:
            venue_id = bind.execute(sa.text(
                "INSERT INTO venues (name, name_ar, description, address, is_active) "
                "VALUES ('alkas-main','ملاعب الكأس','المنشأة الرياضية الرئيسية','صنعاء',TRUE) "
                "RETURNING id"
            )).scalar()
        if venue_id:
            zone_id = bind.execute(sa.text(
                "INSERT INTO venue_zones (venue_id,name,name_ar,sort_order,is_active) "
                "VALUES (:venue,'main','الرئيسية',1,TRUE) RETURNING id"
            ), {"venue": venue_id}).scalar()

    if not zone_id:
        return

    defaults = [
        ("football","ملعب كرة القدم الرئيسي","ملعب كرة قدم عشبي مجهز للحجز بالساعة",12000,22),
        ("basketball","ملعب كرة السلة","ملعب كرة سلة مجهز للمباريات والتدريب",8000,12),
        ("tennis","ملعب التنس","ملعب تنس للحصص الفردية والمباريات",6000,4),
        ("volleyball","ملعب الكرة الطائرة","ملعب كرة طائرة للفرق والتمارين",7000,16),
        ("gymnastics","صالة الجمباز","صالة جمباز مجهزة للتدريب والحصص",5000,20),
        ("table-tennis","صالة تنس الطاولة","طاولات تنس طاولة للحجز الفردي",4000,4),
    ]

    for sport_key,name_ar,description_ar,price,capacity in defaults:
        sport_id=bind.execute(sa.text(
            "SELECT id FROM sports WHERE key=:key AND is_active=TRUE LIMIT 1"
        ),{"key":sport_key}).scalar()
        if not sport_id:
            continue
        exists=bind.execute(sa.text(
            "SELECT id FROM resources WHERE sport_id=:sport_id AND is_active=TRUE LIMIT 1"
        ),{"sport_id":sport_id}).scalar()
        if exists:
            continue
        resource_key=f"default-{sport_key}"
        bind.execute(sa.text(
            "INSERT INTO resources "
            "(zone_id,sport_id,key,name_ar,description_ar,image_url,capacity,status,base_price,is_active) "
            "VALUES (:zone,:sport,:key,:name,:description,NULL,:capacity,'available',:price,TRUE) "
            "ON CONFLICT (key) DO NOTHING"
        ),{"zone":zone_id,"sport":sport_id,"key":resource_key,"name":name_ar,
            "description":description_ar,"capacity":capacity,"price":price})


def downgrade():
    bind=op.get_bind()
    bind.execute(sa.text(
        "DELETE FROM resources WHERE key LIKE 'default-%'"
    ))
