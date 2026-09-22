from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..audit.services import record as audit_record
from ..extensions import db
from ..models import Permission, Role, User

bp=Blueprint("users",__name__,url_prefix="/admin/users",template_folder="templates")


def _allowed():
    return current_user.username=="admin" or current_user.has_permission("users.manage")


@bp.get("")
@login_required
def ui():
    if not _allowed(): return {"error":"forbidden"},403
    return render_template("users/index.html",users=User.query.order_by(User.id.desc()).limit(100).all(),roles=Role.query.order_by(Role.id).all(),permissions=Permission.query.filter_by(is_active=True).order_by(Permission.key).all())


@bp.get("/new")
@login_required
def new():
    if not _allowed(): return {"error":"forbidden"},403
    return render_template("users/form.html",roles=Role.query.order_by(Role.name_ar).all())


@bp.post("/new")
@login_required
def create():
    if not _allowed(): return {"error":"forbidden"},403
    username=(request.form.get("username") or "").strip()
    name=(request.form.get("display_name") or "").strip()
    phone=(request.form.get("phone") or "").strip() or None
    password=request.form.get("password") or ""
    try: role_id=int(request.form["role_id"])
    except (KeyError,TypeError,ValueError): role_id=None
    roles=Role.query.order_by(Role.name_ar).all()
    if not username or not name or len(password)<8 or not role_id:
        return render_template("users/form.html",roles=roles,error="الاسم واسم المستخدم والدور وكلمة مرور 8 أحرف مطلوبة"),400
    if User.query.filter_by(username=username).first(): return render_template("users/form.html",roles=roles,error="اسم المستخدم مستخدم"),400
    if phone and User.query.filter_by(phone=phone).first(): return render_template("users/form.html",roles=roles,error="الهاتف مستخدم"),400
    role=db.session.get(Role,role_id)
    if not role: return render_template("users/form.html",roles=roles,error="الدور غير موجود"),400
    user=User(username=username,display_name=name,phone=phone,roles=[role])
    user.set_password(password)
    db.session.add(user);db.session.flush()
    audit_record("user.create","User",user.id,after={"username":user.username,"role":role.name})
    db.session.commit()
    return redirect(url_for("users.ui"))


@bp.get("/roles/new")
@login_required
def role_new():
    if not _allowed(): return {"error":"forbidden"},403
    return render_template("users/role_form.html",permissions=Permission.query.filter_by(is_active=True).order_by(Permission.key).all())


@bp.post("/roles/new")
@login_required
def role_create():
    if not _allowed(): return {"error":"forbidden"},403
    name=(request.form.get("name") or "").strip()
    name_ar=(request.form.get("name_ar") or "").strip()
    ids=[]
    for value in request.form.getlist("permission_ids"):
        try: ids.append(int(value))
        except ValueError: pass
    if not name or not name_ar: return render_template("users/role_form.html",permissions=Permission.query.filter_by(is_active=True).order_by(Permission.key).all(),error="اسم الدور مطلوب"),400
    if Role.query.filter_by(name=name).first(): return render_template("users/role_form.html",permissions=Permission.query.filter_by(is_active=True).order_by(Permission.key).all(),error="اسم الدور مستخدم"),400
    role=Role(name=name,name_ar=name_ar,permissions=Permission.query.filter(Permission.id.in_(list(dict.fromkeys(ids)))).all() if ids else [])
    db.session.add(role);db.session.flush();audit_record("role.create","Role",role.id,after={"name":role.name,"permissions":[p.key for p in role.permissions]});db.session.commit()
    return redirect(url_for("users.ui"))
