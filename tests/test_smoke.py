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
