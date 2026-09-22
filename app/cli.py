import click
from flask import current_app
from werkzeug.exceptions import BadRequest

from .extensions import db
from .models import (
    Account,
    Announcement,
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


def register_commands(app):
    @app.cli.command("create-admin")
    @click.option("--username", default="admin", show_default=True)
    @click.option("--password", required=True, prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--name", default="مدير النظام", show_default=True)
    def create_admin(username, password, name):
        """إنشاء مستخدم مدير بصلاحيات النظام."""
        user = User.query.filter_by(username=username).first()
        if user:
            raise BadRequest("اسم المستخدم موجود بالفعل")

        permissions = [
            ("settings.manage", "إدارة الإعدادات"),
            ("booking.view", "عرض الحجوزات"),
            ("booking.create", "إنشاء الحجوزات"),
            ("booking.edit", "تعديل الحجوزات"),
            ("payment.view", "عرض المدفوعات"),
            ("accounting.view", "عرض المحاسبة"),
        ]
        permission_rows = []
        for key, label in permissions:
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

        user = User(username=username, display_name=name)
        user.set_password(password)
        user.roles = [role]
        db.session.add(user)
        db.session.commit()
        click.echo(f"تم إنشاء المدير: {username}")

    @app.cli.command("seed-demo")
    @click.option("--admin-password", default="ChangeMe123!", show_default=False)
    def seed_demo(admin_password):
        """إضافة بيانات تجريبية أولية قابلة للتعديل."""
        # Roles and permissions.
        permission_specs = [
            ("settings.manage", "إدارة الإعدادات"),
            ("booking.view", "عرض الحجوزات"),
            ("booking.create", "إنشاء الحجوزات"),
            ("booking.edit", "تعديل الحجوزات"),
            ("payment.view", "عرض المدفوعات"),
            ("accounting.view", "عرض المحاسبة"),
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
            customer = Customer(
                user_id=customer_user.id,
                customer_code="CUS-0001",
                name="عميل تجريبي",
                phone="770000000",
            )
            db.session.add(customer)

        football = Sport.query.filter_by(key="football").first()
        if not football:
            football = Sport(key="football", name_ar="كرة القدم", icon="⚽", sort_order=1)
            db.session.add(football)
        tennis = Sport.query.filter_by(key="tennis").first()
        if not tennis:
            tennis = Sport(key="tennis", name_ar="التنس", icon="🎾", sort_order=2)
            db.session.add(tennis)
        basketball = Sport.query.filter_by(key="basketball").first()
        if not basketball:
            basketball = Sport(key="basketball", name_ar="كرة السلة", icon="🏀", sort_order=3)
            db.session.add(basketball)
        gymnastics = Sport.query.filter_by(key="gymnastics").first()
        if not gymnastics:
            gymnastics = Sport(key="gymnastics", name_ar="الجمباز", icon="🤸", sort_order=4)
            db.session.add(gymnastics)

        venue = Venue.query.filter_by(name="Alkas Main Venue").first()
        if not venue:
            venue = Venue(
                name="Alkas Main Venue",
                name_ar="مدينة ملاعب الكأس",
                description="بيانات تجريبية قابلة للاستبدال من لوحة الإدارة.",
            )
            db.session.add(venue)
            db.session.flush()

        zone = VenueZone.query.filter_by(venue_id=venue.id, name_ar="ملاعب رئيسية").first()
        if not zone:
            zone = VenueZone(venue_id=venue.id, name="main", name_ar="ملاعب رئيسية")
            db.session.add(zone)
            db.session.flush()

        resource_specs = [
            ("football-1", "ملعب كرة قدم 1", football, 12000),
            ("football-2", "ملعب كرة قدم 2", football, 12000),
            ("football-3", "ملعب كرة قدم 3", football, 12000),
            ("tennis-1", "ملعب تنس 1", tennis, 8000),
            ("basketball-1", "ملعب سلة 1", basketball, 9000),
            ("gym-1", "صالة الجمباز", gymnastics, 10000),
        ]
        resources = []
        for key, name_ar, sport, price in resource_specs:
            resource = Resource.query.filter_by(key=key).first()
            if not resource:
                resource = Resource(
                    zone_id=zone.id,
                    sport_id=sport.id,
                    key=key,
                    name_ar=name_ar,
                    base_price=price,
                )
                db.session.add(resource)
            resources.append(resource)

        bundle = ResourceBundle.query.filter_by(name_ar="جميع ملاعب كرة القدم").first()
        if not bundle:
            bundle = ResourceBundle(
                name_ar="جميع ملاعب كرة القدم",
                description_ar="حجز جماعي للملاعب الثلاثة في عملية واحدة.",
                bundle_type="group",
            )
            bundle.resources = resources[:3]
            db.session.add(bundle)

        theme = SiteTheme.query.filter_by(name="default").first()
        if not theme:
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

        announcements = [
            ("temporary", "خصم افتتاحي", "خصم تجريبي لمدة محددة — عدل المواعيد من لوحة الإدارة.", None, None, None),
            ("text", "موسم البطولات", "تابع أخبار البطولات والنتائج أولًا بأول.", None, None, "/tournaments"),
            ("link", "الحجز الجماعي", "يمكن حجز أكثر من ملعب من عملية واحدة.", None, None, "/bookings"),
        ]
        for card_type, title, body, image_url, video_url, target_url in announcements:
            exists = Announcement.query.filter_by(title_ar=title).first()
            if not exists:
                db.session.add(Announcement(
                    card_type=card_type,
                    title_ar=title,
                    body_ar=body,
                    image_url=image_url,
                    video_url=video_url,
                    target_url=target_url,
                    button_text_ar="التفاصيل",
                    priority=10,
                    status="published",
                ))

        # Basic chart of accounts for the financial foundation.
        account_specs = [
            ("1000", "الأصول", "asset", None),
            ("1100", "الصندوق", "asset", "1000"),
            ("1200", "البنوك", "asset", "1000"),
            ("1300", "ذمم العملاء", "asset", "1000"),
            ("4000", "الإيرادات", "revenue", None),
            ("4100", "إيرادات تأجير الملاعب", "revenue", "4000"),
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

        db.session.commit()
        click.echo("تمت إضافة البيانات التجريبية للنواة.")
