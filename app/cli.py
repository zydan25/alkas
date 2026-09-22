import click
from flask import current_app
from werkzeug.exceptions import BadRequest

from .extensions import db
from .models import (
    Account,
    Customer,
    Permission,
    Resource,
    ResourceBundle,
    Role,
    SiteSetting,
    SiteTheme,
    Sport,
    User,
    Venue,
    VenueZone,
)
from .announcements.models import AnnouncementCard
from .accounting.models import FiscalPeriod
from .policies.models import BookingPolicy, PaymentPolicy
from .cashier.models import CashRegister
from datetime import date


def register_commands(app):
    @app.cli.command("create-admin")
    @click.option("--username", default="admin", show_default=True)
    @click.option("--password", required=True, prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--name", default="مدير النظام", show_default=True)
    def create_admin(username, password, name):
        if User.query.filter_by(username=username).first():
            raise BadRequest("اسم المستخدم موجود بالفعل")

        permission_specs = [
            ("admin.access", "دخول لوحة الإدارة"), ("settings.manage", "إدارة الإعدادات"),
            ("users.manage", "إدارة المستخدمين والصلاحيات"),
            ("audit.view", "عرض سجل التدقيق"),
            ("booking.view", "عرض الحجوزات"), ("booking.create", "إنشاء الحجوزات"),
            ("booking.edit", "تعديل الحجوزات"), ("booking.cancel", "إلغاء الحجوزات"),
            ("payment.view", "عرض المدفوعات"), ("payment.create", "تسجيل المدفوعات"),
            ("payment.refund", "طلب الاسترجاع"), ("accounting.view", "عرض المحاسبة"),
            ("accounting.journal.create", "إنشاء القيود"), ("accounting.journal.post", "ترحيل القيود"),
            ("cashier.manage", "إدارة الصناديق"), ("closing.manage", "الإقفال المالي"),
            ("employee.view", "عرض الموظفين"), ("employee.manage", "إدارة الموظفين"),
            ("payroll.manage", "إدارة الرواتب"), ("maintenance.view", "عرض الصيانة"),
            ("maintenance.manage", "إدارة الصيانة"), ("tournament.manage", "إدارة البطولات"),
            ("team.manage", "إدارة الفرق واللاعبين"), ("content.manage", "إدارة المحتوى"),
            ("offer.manage", "إدارة العروض"), ("ads.manage", "إدارة الإعلانات"),
            ("live.manage", "إدارة البث"), ("pricing.manage", "إدارة قواعد التسعير"),
            ("pricing.view", "عرض التسعير"), ("dashboard.view", "عرض لوحة التحكم"),
            ("inventory.manage", "إدارة المخزون"), ("supplier.manage", "إدارة الموردين"),
            ("reports.view", "عرض التقارير"), ("resource.manage", "إدارة الموارد"),
            ("customer.view", "عرض العملاء"), ("invoice.view", "عرض الفواتير"),
            ("invoice.manage", "إدارة الفواتير"), ("shift.manage", "إدارة الورديات"),
            ("membership.manage", "إدارة العضويات"), ("package.manage", "إدارة الباقات"),
            ("training.manage", "إدارة التدريب"),
        ]
        permission_rows = []
        for key, label in permission_specs:
            item = Permission.query.filter_by(key=key).first()
            if not item:
                item = Permission(key=key, name_ar=label)
                db.session.add(item)
            permission_rows.append(item)

        role = Role.query.filter_by(name="manager").first()
        if not role:
            role = Role(name="manager", name_ar="مدير", is_system=True)
            db.session.add(role)
        role.permissions = permission_rows

        current_year = date.today().year
        period_name = str(current_year)
        if not FiscalPeriod.query.filter_by(name=period_name).first():
            db.session.add(FiscalPeriod(name=period_name, starts_on=date(current_year,1,1), ends_on=date(current_year,12,31), status="open"))

        user = User(username=username, display_name=name)
        user.set_password(password)
        user.roles = [role]
        db.session.add(user)
        db.session.commit()
        click.echo(f"تم إنشاء المدير: {username}")

    @app.cli.command("expire-holds")
    def expire_holds_command():
        """إطلاق الحجوزات المؤقتة التي انتهت مهلة الاحتفاظ بها."""
        from .bookings.services import expire_holds
        click.echo(f"تم تحرير {expire_holds()} حجزًا مؤقتًا منتهيًا.")

    @app.cli.command("seed-demo")
    @click.option("--admin-password", default="ChangeMe123!", show_default=False)
    def seed_demo(admin_password):
        permission_specs = [
            ("admin.access", "دخول لوحة الإدارة"),
            ("audit.view", "عرض سجل التدقيق"),
            ("settings.manage", "إدارة الإعدادات"),
            ("users.manage", "إدارة المستخدمين والصلاحيات"),
            ("booking.view", "عرض الحجوزات"),
            ("booking.create", "إنشاء الحجوزات"),
            ("booking.edit", "تعديل الحجوزات"),
            ("booking.cancel", "إلغاء الحجوزات"),
            ("payment.view", "عرض المدفوعات"),
            ("payment.create", "تسجيل المدفوعات"),
            ("payment.refund", "طلب الاسترجاع"),
            ("accounting.view", "عرض المحاسبة"),
            ("accounting.journal.create", "إنشاء القيود"),
            ("accounting.journal.post", "ترحيل القيود"),
            ("cashier.manage", "إدارة الصناديق"),
            ("closing.manage", "الإقفال المالي"),
            ("employee.view", "عرض الموظفين"),
            ("employee.manage", "إدارة الموظفين"),
            ("payroll.manage", "إدارة الرواتب"),
            ("maintenance.view", "عرض الصيانة"),
            ("maintenance.manage", "إدارة الصيانة"),
            ("tournament.manage", "إدارة البطولات"),
            ("team.manage", "إدارة الفرق واللاعبين"),
            ("content.manage", "إدارة المحتوى"),
            ("offer.manage", "إدارة العروض"),
            ("ads.manage", "إدارة الإعلانات"),
            ("live.manage", "إدارة البث"),
            ("pricing.manage", "إدارة قواعد التسعير"),
            ("dashboard.view", "عرض لوحة التحكم"),

            ("inventory.manage", "إدارة المخزون"),
            ("supplier.manage", "إدارة الموردين"),
            ("reports.view", "عرض التقارير"),
            ("resource.manage", "إدارة الموارد"),
            ("customer.view", "عرض العملاء"),
            ("invoice.view", "عرض الفواتير"),
            ("shift.manage", "إدارة الورديات"),
            ("membership.manage", "إدارة العضويات"),
            ("package.manage", "إدارة الباقات"),
            ("pricing.view", "عرض التسعير"),
            ("training.manage", "إدارة التدريب"),

        ]
        perms = []
        for key, name_ar in permission_specs:
            perm = Permission.query.filter_by(key=key).first()
            if not perm:
                perm = Permission(key=key, name_ar=name_ar)
                db.session.add(perm)
            perms.append(perm)

        manager = Role.query.filter_by(name="manager").first()
        if not manager:
            manager = Role(name="manager", name_ar="مدير", is_system=True)
            db.session.add(manager)
        manager.permissions = perms

        role_matrix = {
            "accountant": [
                "admin.access", "audit.view", "dashboard.view", "accounting.view", "accounting.journal.create", "accounting.journal.post",
                "payment.view", "payment.create", "reports.view", "cashier.manage", "closing.manage"
            ],
            "receptionist": [
                "admin.access", "booking.view", "dashboard.view", "booking.create", "booking.edit", "payment.view",
                "payment.create", "cashier.manage", "customer.view"
            ],
            "maintenance": ["admin.access", "maintenance.view", "maintenance.manage", "employee.view"],
            "content": ["admin.access", "dashboard.view", "content.manage", "offer.manage", "ads.manage", "live.manage"],
        }
        for role_name, keys in role_matrix.items():
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                role = Role(name=role_name, name_ar={
                    "accountant": "محاسب", "receptionist": "استقبال",
                    "maintenance": "صيانة", "content": "محتوى"
                }[role_name])
                db.session.add(role)
            role.permissions = [p for p in perms if p.key in keys]

        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(username="admin", display_name="مدير النظام")
            admin.set_password(admin_password)
            admin.roles = [manager]
            db.session.add(admin)

        customer_user = User.query.filter_by(username="demo").first()
        if not customer_user:
            customer_user = User(username="demo", display_name="عميل تجريبي", phone="770000000")
            customer_user.set_password("Demo123!")
            db.session.add(customer_user)
            db.session.flush()
            db.session.add(Customer(
                user_id=customer_user.id,
                customer_code="CUS-0001",
                name="عميل تجريبي",
                phone="770000000",
            ))

        sport_specs = [
            ("football", "كرة القدم", "⚽", 1),
            ("tennis", "التنس", "🎾", 2),
            ("basketball", "كرة السلة", "🏀", 3),
            ("gymnastics", "الجمباز", "🤸", 4),
        ]
        sports = {}
        for key, name_ar, icon, sort_order in sport_specs:
            sport = Sport.query.filter_by(key=key).first()
            if not sport:
                sport = Sport(key=key, name_ar=name_ar, icon=icon, sort_order=sort_order)
                db.session.add(sport)
            sports[key] = sport

        venue = Venue.query.filter_by(name="Alkas Main Venue").first()
        if not venue:
            venue = Venue(name="Alkas Main Venue", name_ar="مدينة ملاعب الكأس", description="بيانات تجريبية قابلة للاستبدال.")
            db.session.add(venue)
            db.session.flush()

        zone = VenueZone.query.filter_by(venue_id=venue.id, name_ar="ملاعب رئيسية").first()
        if not zone:
            zone = VenueZone(venue_id=venue.id, name="main", name_ar="ملاعب رئيسية")
            db.session.add(zone)
            db.session.flush()

        for key, name_ar, sport_key, price in [
            ("football-1", "ملعب كرة قدم 1", "football", 12000),
            ("football-2", "ملعب كرة قدم 2", "football", 12000),
            ("football-3", "ملعب كرة قدم 3", "football", 12000),
            ("tennis-1", "ملعب تنس 1", "tennis", 8000),
            ("basketball-1", "ملعب سلة 1", "basketball", 9000),
            ("gym-1", "صالة الجمباز", "gymnastics", 10000),
        ]:
            if not Resource.query.filter_by(key=key).first():
                db.session.add(Resource(
                    zone_id=zone.id, sport_id=sports[sport_key].id,
                    key=key, name_ar=name_ar, base_price=price
                ))

        db.session.flush()
        football_resources = Resource.query.filter(Resource.key.in_([ "football-1", "football-2", "football-3" ])).all()
        bundle = ResourceBundle.query.filter_by(name_ar="جميع ملاعب كرة القدم").first()
        if not bundle:
            bundle = ResourceBundle(
                name_ar="جميع ملاعب كرة القدم",
                description_ar="حجز جماعي للملاعب الثلاثة في عملية واحدة.",
                bundle_type="group",
                resources=football_resources,
            )
            db.session.add(bundle)

        if not SiteTheme.query.filter_by(name="default").first():
            db.session.add(SiteTheme(name="default"))

        for key, value in {
            "site_name": "ملاعب الكأس",
            "site_short_name": "الكأس",
            "hero_title": "كل ملاعبك في مكان واحد",
            "hero_subtitle": "احجز، العب، تابع البطولات، واكتشف العروض بسهولة.",
            "booking_hold_minutes": "10",
            "asset_version": "1",
        }.items():
            row = SiteSetting.query.filter_by(key=key).first()
            if not row:
                db.session.add(SiteSetting(key=key, value=value, is_public=True))

        demo_cards = [
            dict(card_type="temporary", title_ar="عرض الافتتاح", body_ar="عرض تجريبي مؤقت يمكن تحديد موعد انتهائه من لوحة الإدارة.", accent_label_ar="لفترة محدودة", priority=30),
            dict(card_type="image", title_ar="بطولة الأسبوع", body_ar="بطاقة بصورة أو إعلان بصري، ويمكن ربطها بصفحة البطولة.", image_url="/static/img/icon-512.svg", target_url="/admin/tournaments", button_text_ar="شاهد البطولة", accent_label_ar="رياضة", priority=20),
            dict(card_type="video", title_ar="شاهد الأجواء", body_ar="بطاقة فيديو يمكن أن تحمل رابط YouTube أو مصدر بث خارجي.", video_url="https://www.youtube.com/", button_text_ar="مشاهدة", accent_label_ar="فيديو", priority=10),
        ]
        for data in demo_cards:
            if not AnnouncementCard.query.filter_by(title_ar=data["title_ar"]).first():
                db.session.add(AnnouncementCard(**data, status="published"))

        account_specs = [
            ("1000", "الأصول", "asset", None),
            ("1100", "الصندوق", "asset", "1000"),
            ("1200", "البنوك", "asset", "1000"),
            ("1300", "ذمم العملاء", "asset", "1000"),
            ("4000", "الإيرادات", "revenue", None),
            ("4100", "إيرادات تأجير الملاعب", "revenue", "4000"),
            ("2000", "الالتزامات", "liability", None),
            ("2200", "رواتب مستحقة", "liability", "2000"),
            ("5000", "المصروفات", "expense", None),
            ("5100", "مصروفات التشغيل", "expense", "5000"),
        ]
        accounts = {}
        for code, name_ar, account_type, parent_code in account_specs:
            account = Account.query.filter_by(code=code).first()
            if not account:
                account = Account(code=code, name_ar=name_ar, account_type=account_type)
                db.session.add(account)
                db.session.flush()
            accounts[code] = account
        for code, _, _, parent_code in account_specs:
            if parent_code:
                accounts[code].parent_id = accounts[parent_code].id

        current_year = date.today().year
        period_name = str(current_year)
        if not FiscalPeriod.query.filter_by(name=period_name).first():
            db.session.add(FiscalPeriod(name=period_name, starts_on=date(current_year,1,1), ends_on=date(current_year,12,31), status="open"))

        if not BookingPolicy.query.filter_by(is_default=True, is_active=True).first():
            db.session.add(BookingPolicy(
                name_ar="السياسة الافتراضية",
                cancellation_deadline_minutes=360,
                refund_percent_before_deadline=100,
                refund_percent_after_deadline=0,
                deposit_percent=100,
                is_default=True,
                is_active=True,
            ))
        if not PaymentPolicy.query.filter_by(is_default=True, is_active=True).first():
            db.session.add(PaymentPolicy(
                name_ar="الدفع الافتراضي",
                allow_cash=True,
                allow_transfer=True,
                allow_card=True,
                allow_wallet=True,
                require_full_payment=False,
                is_default=True,
                is_active=True,
            ))
        if not CashRegister.query.filter_by(code="MAIN").first():
            db.session.add(CashRegister(code="MAIN", name_ar="الصندوق الرئيسي", location_ar="الاستقبال", is_active=True))

        db.session.commit()
        click.echo("تمت إضافة البيانات التجريبية للنواة.")
