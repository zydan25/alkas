from ..extensions import db


class BookingPackage(db.Model):
    __tablename__ = "booking_packages"
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(160), nullable=False, unique=True)
    total_units = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    price = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    unit_name_ar = db.Column(db.String(60), nullable=False, default="ساعة")
    duration_days = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class CustomerPackage(db.Model):
    __tablename__ = "customer_packages"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey("booking_packages.id", ondelete="RESTRICT"), nullable=False)
    purchased_units = db.Column(db.Numeric(12, 2), nullable=False)
    remaining_units = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="active")


class PackageConsumption(db.Model):
    __tablename__ = "package_consumptions"
    id = db.Column(db.Integer, primary_key=True)
    customer_package_id = db.Column(db.Integer, db.ForeignKey("customer_packages.id", ondelete="RESTRICT"), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id", ondelete="RESTRICT"))
    units = db.Column(db.Numeric(12, 2), nullable=False)
