"""Staff operations panel, park visits and staff deductions.

Revision ID: 20260924_0008
Revises: 20260923_0007
"""
from alembic import op
import sqlalchemy as sa

revision = "20260924_0008"
down_revision = "20260923_0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "staff_deductions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("deduction_date", sa.Date(), nullable=False),
        sa.Column("reason_ar", sa.String(length=500), nullable=False),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount >= 0", name="ck_staff_deduction_nonnegative"),
    )
    op.create_index("ix_staff_deductions_employee_id", "staff_deductions", ["employee_id"])

    op.create_table(
        "park_visits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="SET NULL")),
        sa.Column("visitor_name", sa.String(length=180), nullable=False),
        sa.Column("people_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("people_remaining", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("price_per_person", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expected_end_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id", ondelete="SET NULL")),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.CheckConstraint("people_count > 0", name="ck_park_visit_people_positive"),
        sa.CheckConstraint("people_remaining >= 0 AND people_remaining <= people_count", name="ck_park_visit_remaining_valid"),
        sa.CheckConstraint("price_per_person >= 0 AND total >= 0", name="ck_park_visit_amounts_nonnegative"),
    )
    op.create_index("ix_park_visits_customer_id", "park_visits", ["customer_id"])
    op.create_index("ix_park_visits_status", "park_visits", ["status"])
    op.create_index("ix_park_visits_started_status", "park_visits", ["started_at", "status"])

    op.create_table(
        "park_visit_exits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("visit_id", sa.Integer(), sa.ForeignKey("park_visits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("people_count", sa.Integer(), nullable=False),
        sa.Column("exited_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note_ar", sa.String(length=400)),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.CheckConstraint("people_count > 0", name="ck_park_exit_people_positive"),
    )
    op.create_index("ix_park_visit_exits_visit_id", "park_visit_exits", ["visit_id"])

    permissions = [
        ("staff.access", "دخول لوحة الموظف", "الوصول إلى واجهة التشغيل والكاشير الخاصة بالموظف."),
        ("staff.booking.confirm", "تأكيد الحجوزات", "تأكيد حجوزات العملاء بعد التحقق من الدفع أو العربون."),
        ("staff.booking.chat", "محادثات الحجوزات", "فتح وإرسال رسائل محادثات الحجوزات."),
        ("staff.booking.cancel", "إلغاء الحجوزات", "إلغاء الحجز وبدء طلب الاسترجاع وفق السياسة."),
        ("staff.park.manage", "إدارة دخول الحديقة", "تسجيل الدخول والخروج للزوار ومتابعة المتبقين."),
        ("staff.finance.view", "البيانات المالية للموظف", "عرض الراتب والخصومات والسلف وحركات العهدة الخاصة بالموظف."),
        ("staff.cash.manage", "إدارة وردية الموظف", "فتح وإغلاق وردية الصندوق وإخلاء العهدة الخاصة بالموظف."),
    ]
    for key, name_ar, description_ar in permissions:
        op.execute(
            sa.text(
                "INSERT INTO permissions (key, name_ar, description_ar, is_active) "
                "VALUES (:key, :name_ar, :description_ar, true) "
                "ON CONFLICT (key) DO UPDATE SET "
                "name_ar = EXCLUDED.name_ar, description_ar = EXCLUDED.description_ar, is_active = true"
            ).bindparams(key=key, name_ar=name_ar, description_ar=description_ar)
        )


def downgrade():
    op.drop_index("ix_park_visit_exits_visit_id", table_name="park_visit_exits")
    op.drop_table("park_visit_exits")
    op.drop_index("ix_park_visits_started_status", table_name="park_visits")
    op.drop_index("ix_park_visits_status", table_name="park_visits")
    op.drop_index("ix_park_visits_customer_id", table_name="park_visits")
    op.drop_table("park_visits")
    op.drop_index("ix_staff_deductions_employee_id", table_name="staff_deductions")
    op.drop_table("staff_deductions")
    for key in (
        "staff.access",
        "staff.booking.confirm",
        "staff.booking.chat",
        "staff.booking.cancel",
        "staff.park.manage",
        "staff.finance.view",
        "staff.cash.manage",
    ):
        op.execute(sa.text("DELETE FROM permissions WHERE key = :key").bindparams(key=key))
