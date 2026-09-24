from app import create_app


def test_health():
    app = create_app()
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_admin_uses_single_tree_dashboard_layout():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    legacy = root / "app" / "templates" / "admin" / "dashboard.html"
    admin_layout = root / "app" / "admin" / "templates" / "admin" / "layout.html"
    admin_dashboard = root / "app" / "admin" / "templates" / "admin" / "dashboard.html"

    assert not legacy.exists()
    assert "admin-nav-tree" in admin_layout.read_text(encoding="utf-8")
    assert "admin-app" not in admin_dashboard.read_text(encoding="utf-8") or 'extends "admin/layout.html"' in admin_dashboard.read_text(encoding="utf-8")


def test_admin_tree_has_visible_chevron_and_contrast_overrides():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    icon_sprite = (root / "app" / "static" / "img" / "admin-icons.svg").read_text(encoding="utf-8")
    theme = (root / "app" / "static" / "css" / "admin-theme.css").read_text(encoding="utf-8")

    assert 'id="chevron"' in icon_sprite
    assert ".admin-nav-tree[open]>summary" in theme
    assert ".admin-nav-children>a.active" in theme


def test_admin_bookings_page_renders_for_admin_user():
    import uuid

    from app import create_app
    from app.extensions import db
    from app.models import Permission, Role, User

    app = create_app()
    app.config["WTF_CSRF_ENABLED"] = False
    username = "booking_smoke_" + uuid.uuid4().hex[:10]

    with app.app_context():
        user = User(
            username=username,
            phone="77" + str(uuid.uuid4().int % 10**8).zfill(8),
            display_name="اختبار الحجوزات",
            is_active=True,
        )
        user.set_password("TestPass123")
        permission = Permission(key="admin.access", name_ar="دخول الإدارة")
        booking_permission = Permission(key="booking.view", name_ar="عرض الحجوزات")
        role = Role(name="booking_smoke_" + uuid.uuid4().hex[:8], name_ar="اختبار الحجوزات", is_system=False, permissions=[permission, booking_permission])
        user.roles.append(role)
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True

        response = client.get("/admin/bookings")
        assert response.status_code == 200
        assert "الحجوزات" in response.get_data(as_text=True)

        db.session.delete(user)
        db.session.commit()


def test_staff_dashboard_renders_for_linked_employee():
    import uuid

    from app import create_app
    from app.extensions import db
    from app.models import Employee, User

    app = create_app()
    app.config["WTF_CSRF_ENABLED"] = False
    username = "staff_smoke_" + uuid.uuid4().hex[:10]
    phone = "77" + str(uuid.uuid4().int % 10**8).zfill(8)

    with app.app_context():
        user = User(
            username=username,
            phone=phone,
            display_name="موظف اختبار",
            is_active=True,
        )
        user.set_password("TestPass123")
        db.session.add(user)
        db.session.flush()
        employee = Employee(
            employee_code="EMP-SMOKE-" + uuid.uuid4().hex[:6].upper(),
            name_ar="موظف اختبار",
            phone=phone,
            employment_status="active",
            base_salary=1000,
            user_id=user.id,
        )
        db.session.add(employee)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)
            session["_fresh"] = True

        response = client.get("/staff")
        assert response.status_code == 200
        assert "حجز ملعب أو لعبة" in response.get_data(as_text=True)
        assert "دخول سريع للحديقة" in response.get_data(as_text=True)

        db.session.delete(employee)
        db.session.delete(user)
        db.session.commit()


def test_employee_login_redirects_to_staff_app():
    import uuid

    from app import create_app
    from app.extensions import db
    from app.models import Employee, User

    app = create_app()
    app.config["WTF_CSRF_ENABLED"] = False
    username = "staff_login_" + uuid.uuid4().hex[:10]
    phone = "77" + str(uuid.uuid4().int % 10**8).zfill(8)

    with app.app_context():
        user = User(
            username=username,
            phone=phone,
            display_name="دخول موظف",
            is_active=True,
        )
        user.set_password("TestPass123")
        db.session.add(user)
        db.session.flush()
        employee = Employee(
            employee_code="EMP-LOGIN-" + uuid.uuid4().hex[:6].upper(),
            name_ar="دخول موظف",
            employment_status="active",
            user_id=user.id,
        )
        db.session.add(employee)
        db.session.commit()

        client = app.test_client()
        response = client.post(
            "/auth/login",
            data={"identifier": username, "password": "TestPass123"},
            follow_redirects=False,
        )
        assert response.status_code in {302, 303}
        assert response.headers["Location"].endswith("/staff")

        db.session.delete(employee)
        db.session.delete(user)
        db.session.commit()


def test_manager_can_create_employee_login_and_open_staff_app():
    import uuid

    from app import create_app
    from app.extensions import db
    from app.models import Employee, Permission, Role, User

    app = create_app()
    app.config["WTF_CSRF_ENABLED"] = False
    suffix = uuid.uuid4().hex[:8]
    manager_username = "manager_" + suffix
    staff_username = "new_staff_" + suffix

    with app.app_context():
        keys = {
            "admin.access": "دخول الإدارة",
            "employee.view": "عرض الموظفين",
            "employee.manage": "إدارة الموظفين",
            "staff.access": "دخول لوحة الموظف",
            "staff.booking.confirm": "تأكيد الحجوزات",
            "staff.booking.chat": "محادثات الحجوزات",
        }
        permissions = []
        for key, name_ar in keys.items():
            permission = Permission.query.filter_by(key=key).first()
            if not permission:
                permission = Permission(key=key, name_ar=name_ar, is_active=True)
                db.session.add(permission)
                db.session.flush()
            permissions.append(permission)

        manager_role = Role(
            name="manager_smoke_" + suffix,
            name_ar="مدير اختبار",
            permissions=[p for p in permissions if p.key in {"admin.access", "employee.view", "employee.manage"}],
        )
        staff_role = Role(
            name="staff_smoke_role_" + suffix,
            name_ar="موظف اختبار",
            permissions=[p for p in permissions if p.key in {"staff.access", "staff.booking.confirm", "staff.booking.chat"}],
        )
        manager = User(
            username=manager_username,
            phone="77" + str(uuid.uuid4().int % 10**8).zfill(8),
            display_name="مدير اختبار",
            is_active=True,
            roles=[manager_role],
        )
        manager.set_password("ManagerPass123")
        db.session.add_all([manager_role, staff_role, manager])
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(manager.id)
            session["_fresh"] = True

        response = client.post(
            "/admin/employees/new",
            data={
                "name_ar": "موظف تم إنشاؤه",
                "phone": "78" + str(uuid.uuid4().int % 10**8).zfill(8),
                "base_salary": "250000",
                "login_username": staff_username,
                "login_password": "StaffPass123",
                "login_role_id": str(staff_role.id),
            },
            follow_redirects=False,
        )
        assert response.status_code in {302, 303}

        employee = Employee.query.filter_by(name_ar="موظف تم إنشاؤه").order_by(Employee.id.desc()).first()
        assert employee is not None
        assert employee.user_id is not None
        staff_user = db.session.get(User, employee.user_id)
        assert staff_user is not None
        assert staff_user.username == staff_username
        assert any(role.id == staff_role.id for role in staff_user.roles)

        staff_client = app.test_client()
        response = staff_client.post(
            "/auth/login",
            data={"identifier": staff_username, "password": "StaffPass123"},
            follow_redirects=False,
        )
        assert response.status_code in {302, 303}
        assert response.headers["Location"].endswith("/staff")

        db.session.delete(employee)
        db.session.delete(staff_user)
        db.session.delete(manager)
        db.session.delete(staff_role)
        db.session.delete(manager_role)
        db.session.commit()


def test_booking_policy_and_multi_player_fields_are_present():
    from app.bookings.models import Booking
    from app.policies.models import BookingPolicy

    policy = BookingPolicy()
    booking = Booking()
    assert BookingPolicy.__table__.c.hold_duration_minutes.default.arg == 60
    assert hasattr(booking, "participant_count")
    assert hasattr(booking, "participants_remaining")
    assert hasattr(booking, "participant_unit_price")
