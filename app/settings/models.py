from ..extensions import db

class SiteSetting(db.Model):
    __tablename__="site_settings"
    id=db.Column(db.Integer,primary_key=True)
    key=db.Column(db.String(120),unique=True,nullable=False,index=True)
    value=db.Column(db.Text)
    value_type=db.Column(db.String(30),nullable=False,default="string")
    is_public=db.Column(db.Boolean,nullable=False,default=False)

class SiteTheme(db.Model):
    __tablename__="site_themes"
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(80),nullable=False,default="default")
    primary_color=db.Column(db.String(20),nullable=False,default="#0f172a")
    secondary_color=db.Column(db.String(20),nullable=False,default="#2563eb")
    accent_color=db.Column(db.String(20),nullable=False,default="#f59e0b")
    success_color=db.Column(db.String(20),nullable=False,default="#16a34a")
    danger_color=db.Column(db.String(20),nullable=False,default="#dc2626")
    surface_color=db.Column(db.String(20),nullable=False,default="#ffffff")
    background_color=db.Column(db.String(20),nullable=False,default="#f8fafc")
    text_color=db.Column(db.String(20),nullable=False,default="#0f172a")
    radius=db.Column(db.String(20),nullable=False,default="18px")
    is_active=db.Column(db.Boolean,nullable=False,default=True)
