from ..extensions import db


class Venue(db.Model):
    __tablename__ = "venues"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    name_ar = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    address = db.Column(db.String(300))
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    zones = db.relationship("VenueZone", back_populates="venue", cascade="all, delete-orphan")


class VenueZone(db.Model):
    __tablename__ = "venue_zones"

    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey("venues.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    name_ar = db.Column(db.String(160), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    venue = db.relationship("Venue", back_populates="zones")
    resources = db.relationship("Resource", back_populates="zone", cascade="all, delete-orphan")


class Sport(db.Model):
    __tablename__ = "sports"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(60), unique=True, nullable=False)
    name_ar = db.Column(db.String(120), nullable=False)
    icon = db.Column(db.String(80))
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class Resource(db.Model):
    __tablename__ = "resources"

    id = db.Column(db.Integer, primary_key=True)
    zone_id = db.Column(db.Integer, db.ForeignKey("venue_zones.id", ondelete="CASCADE"), nullable=False, index=True)
    sport_id = db.Column(db.Integer, db.ForeignKey("sports.id", ondelete="RESTRICT"), nullable=False, index=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    name_ar = db.Column(db.String(160), nullable=False)
    description_ar = db.Column(db.Text)
    capacity = db.Column(db.Integer)
    status = db.Column(db.String(30), nullable=False, default="available")
    base_price = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    zone = db.relationship("VenueZone", back_populates="resources")
    sport = db.relationship("Sport", lazy="joined")


class ResourceBundle(db.Model):
    __tablename__ = "resource_bundles"

    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(160), nullable=False)
    description_ar = db.Column(db.Text)
    bundle_type = db.Column(db.String(30), nullable=False, default="group")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    resources = db.relationship(
        "Resource",
        secondary=lambda: resource_bundle_items,
        lazy="selectin",
    )


resource_bundle_items = db.Table(
    "resource_bundle_items",
    db.Column("bundle_id", db.ForeignKey("resource_bundles.id", ondelete="CASCADE"), primary_key=True),
    db.Column("resource_id", db.ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True),
)
