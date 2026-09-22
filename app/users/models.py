from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db

user_roles = db.Table(
    "user_roles",
    db.Column("user_id", db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    db.Column("role_id", db.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)
role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    db.Column("permission_id", db.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(db.Model):
    __tablename__="permissions"
    id=db.Column(db.Integer,primary_key=True)
    key=db.Column(db.String(120),unique=True,nullable=False,index=True)
    name_ar=db.Column(db.String(160),nullable=False)
    description_ar=db.Column(db.String(500))
    is_active=db.Column(db.Boolean,nullable=False,default=True)


class Role(db.Model):
    __tablename__="roles"
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(80),unique=True,nullable=False)
    name_ar=db.Column(db.String(120),nullable=False)
    is_system=db.Column(db.Boolean,nullable=False,default=False)
    permissions=db.relationship("Permission",secondary=role_permissions,lazy="selectin")


class User(UserMixin,db.Model):
    __tablename__="users"
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(120),unique=True,nullable=False,index=True)
    phone=db.Column(db.String(40),unique=True,index=True)
    password_hash=db.Column(db.String(255),nullable=False)
    display_name=db.Column(db.String(160),nullable=False)
    is_active=db.Column(db.Boolean,nullable=False,default=True)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda: datetime.now(timezone.utc))
    last_login_at=db.Column(db.DateTime(timezone=True))
    roles=db.relationship("Role",secondary=user_roles,lazy="selectin")

    def set_password(self,value): self.password_hash=generate_password_hash(value)
    def check_password(self,value): return check_password_hash(self.password_hash,value)
    def has_permission(self,key):
        return any(permission.key==key for role in self.roles for permission in role.permissions)
