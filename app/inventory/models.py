from datetime import datetime, timezone
from ..extensions import db

class ProductCategory(db.Model):
    __tablename__ = "product_categories"
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(150), nullable=False, unique=True)

class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name_ar = db.Column(db.String(220), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("product_categories.id", ondelete="SET NULL"))
    unit_ar = db.Column(db.String(40), nullable=False, default="قطعة")
    cost_price = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    sale_price = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    reorder_level = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

class Warehouse(db.Model):
    __tablename__ = "warehouses"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name_ar = db.Column(db.String(180), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

class StockMovement(db.Model):
    __tablename__ = "stock_movements"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False)
    movement_type = db.Column(db.String(30), nullable=False)
    quantity = db.Column(db.Numeric(12, 2), nullable=False)
    unit_cost = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    reference_type = db.Column(db.String(80))
    reference_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
