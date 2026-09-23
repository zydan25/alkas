"""Customer booking mobile experience, media fields, chat and receipts.

Revision ID: 20260923_0004
Revises: 20260923_0003
"""
from alembic import op
import sqlalchemy as sa

revision = "20260923_0004"
down_revision = "20260923_0003"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "sports" in tables:
        columns = {c["name"] for c in inspector.get_columns("sports")}
        if "image_url" not in columns:
            op.add_column("sports", sa.Column("image_url", sa.String(500)))
        if "description_ar" not in columns:
            op.add_column("sports", sa.Column("description_ar", sa.Text()))

    if "resources" in tables:
        columns = {c["name"] for c in inspector.get_columns("resources")}
        if "image_url" not in columns:
            op.add_column("resources", sa.Column("image_url", sa.String(500)))

    if "booking_messages" not in tables:
        op.create_table(
            "booking_messages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sender_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("sender_role", sa.String(30), nullable=False, server_default="customer"),
            sa.Column("message_type", sa.String(30), nullable=False, server_default="message"),
            sa.Column("body_ar", sa.Text()),
            sa.Column("attachment_url", sa.String(800)),
            sa.Column("attachment_name", sa.String(240)),
            sa.Column("attachment_mime", sa.String(120)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_booking_messages_booking_id", "booking_messages", ["booking_id"])

    if "booking_payment_receipts" not in tables:
        op.create_table(
            "booking_payment_receipts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
            sa.Column("uploaded_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("file_url", sa.String(800), nullable=False),
            sa.Column("original_name", sa.String(240), nullable=False),
            sa.Column("mime_type", sa.String(120)),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("note_ar", sa.String(500)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_booking_payment_receipts_booking_id", "booking_payment_receipts", ["booking_id"])

    if "site_settings" in tables:
        defaults = [
            ("payment_intro", "بعد تأكيد الحجز اتبع بيانات الدفع التالية، ثم ارفع إشعار التحويل من صفحة الحجز.", True),
            ("payment_bank_name", "", True),
            ("payment_account_name", "", True),
            ("payment_account_number", "", True),
            ("payment_wallet_name", "", True),
            ("payment_wallet_number", "", True),
            ("payment_cash_note", "الدفع النقدي متاح لدى الاستقبال حسب سياسة المنشأة.", True),
            ("booking_policy_note", "لا يعتبر الحجز نهائيًا إلا بعد تأكيده. المواعيد المتعارضة تُرفض تلقائيًا.", True),
        ]
        for key, value, is_public in defaults:
            bind.execute(
                sa.text(
                    "INSERT INTO site_settings (key, value, value_type, is_public) "
                    "VALUES (:key, :value, 'string', :is_public) "
                    "ON CONFLICT (key) DO NOTHING"
                ),
                {"key": key, "value": value, "is_public": is_public},
            )

    if "sports" in tables:
        sports = [
            ("football", "كرة القدم", "⚽", 1),
            ("basketball", "كرة السلة", "🏀", 2),
            ("tennis", "التنس", "🎾", 3),
            ("volleyball", "الكرة الطائرة", "🏐", 4),
            ("gymnastics", "الجمباز", "🤸", 5),
            ("table-tennis", "تنس الطاولة", "🏓", 6),
        ]
        for key, name_ar, icon, sort_order in sports:
            bind.execute(
                sa.text(
                    "INSERT INTO sports (key, name_ar, icon, sort_order, is_active) "
                    "VALUES (:key, :name_ar, :icon, :sort_order, TRUE) "
                    "ON CONFLICT (key) DO NOTHING"
                ),
                {"key": key, "name_ar": name_ar, "icon": icon, "sort_order": sort_order},
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "booking_payment_receipts" in tables:
        op.drop_index("ix_booking_payment_receipts_booking_id", table_name="booking_payment_receipts")
        op.drop_table("booking_payment_receipts")
    if "booking_messages" in tables:
        op.drop_index("ix_booking_messages_booking_id", table_name="booking_messages")
        op.drop_table("booking_messages")

    inspector = sa.inspect(bind)
    if "resources" in inspector.get_table_names():
        columns = {c["name"] for c in inspector.get_columns("resources")}
        if "image_url" in columns:
            op.drop_column("resources", "image_url")
    if "sports" in inspector.get_table_names():
        columns = {c["name"] for c in inspector.get_columns("sports")}
        if "description_ar" in columns:
            op.drop_column("sports", "description_ar")
        if "image_url" in columns:
            op.drop_column("sports", "image_url")
