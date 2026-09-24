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
