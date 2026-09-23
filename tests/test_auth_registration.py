import uuid

from app import create_app
from app.extensions import db
from app.models import Customer, User


def test_customer_registration_creates_user_and_customer():
    app = create_app()
    app.config["WTF_CSRF_ENABLED"] = False
    phone = "77" + str(uuid.uuid4().int % 10**8).zfill(8)

    client = app.test_client()
    response = client.post(
        "/auth/register",
        data={
            "full_name": "عميل اختبار",
            "phone": phone,
            "email": "test@example.com",
            "password": "TestPass123",
            "password_confirm": "TestPass123",
            "next": "/bookings",
        },
        follow_redirects=False,
    )

    assert response.status_code in {302, 303}

    with app.app_context():
        user = User.query.filter_by(phone=phone).first()
        assert user is not None
        assert user.display_name == "عميل اختبار"
        assert user.check_password("TestPass123")
        customer = Customer.query.filter_by(user_id=user.id).first()
        assert customer is not None
        assert customer.phone == phone

        db.session.delete(customer)
        db.session.delete(user)
        db.session.commit()


def test_registration_rejects_duplicate_phone():
    app = create_app()
    app.config["WTF_CSRF_ENABLED"] = False
    phone = "77" + str(uuid.uuid4().int % 10**8).zfill(8)

    with app.app_context():
        user = User(
            username="registration_fixture_" + uuid.uuid4().hex[:10],
            display_name="Duplicate Fixture",
            phone=phone,
            is_active=True,
        )
        user.set_password("FixturePass123")
        db.session.add(user)
        db.session.commit()

        client = app.test_client()
        response = client.post(
            "/auth/register",
            data={
                "full_name": "Duplicate",
                "phone": phone,
                "password": "TestPass123",
                "password_confirm": "TestPass123",
            },
        )
        assert response.status_code == 200
        assert "رقم الهاتف مرتبط بحساب موجود بالفعل." in response.get_data(as_text=True)

        db.session.delete(user)
        db.session.commit()
