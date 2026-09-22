from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from ..extensions import db
from ..models import Resource, Sport, VenueZone, ResourceBundle

bp=Blueprint("resources",__name__,url_prefix="/admin/resources",template_folder="templates")

def _allowed(): return current_user.username=="admin" or current_user.has_permission("resource.manage")

@bp.get("/new")
@login_required
def new():
    if not _allowed(): return {"error":"forbidden"},403
    return render_template("resources/form.html",sports=Sport.query.filter_by(is_active=True).all(),zones=VenueZone.query.filter_by(is_active=True).all())

@bp.post("/new")
@login_required
def create():
    if not _allowed(): return {"error":"forbidden"},403
    key=(request.form.get("key") or "").strip()
    name=(request.form.get("name_ar") or "").strip()
    try:
        zone_id=int(request.form["zone_id"]); sport_id=int(request.form["sport_id"])
        price=request.form.get("base_price") or 0
    except (KeyError,ValueError,TypeError): return render_template("resources/form.html",sports=Sport.query.filter_by(is_active=True).all(),zones=VenueZone.query.filter_by(is_active=True).all(),error="البيانات غير صحيحة"),400
    if not key or not name: return render_template("resources/form.html",sports=Sport.query.filter_by(is_active=True).all(),zones=VenueZone.query.filter_by(is_active=True).all(),error="الاسم والمفتاح مطلوبان"),400
    if Resource.query.filter_by(key=key).first(): return render_template("resources/form.html",sports=Sport.query.filter_by(is_active=True).all(),zones=VenueZone.query.filter_by(is_active=True).all(),error="المفتاح مستخدم"),400
    db.session.add(Resource(zone_id=zone_id,sport_id=sport_id,key=key,name_ar=name,base_price=price,capacity=request.form.get("capacity") or None))
    db.session.commit()
    return redirect(url_for("admin.resources"))

@bp.get("/bundles/new")
@login_required
def bundle_new():
    if not _allowed():
        return {"error":"forbidden"},403
    return render_template("resources/bundle_form.html", resources=Resource.query.filter_by(is_active=True).order_by(Resource.sport_id,Resource.id).all())

@bp.post("/bundles/new")
@login_required
def bundle_create():
    if not _allowed():
        return {"error":"forbidden"},403
    name=(request.form.get("name_ar") or "").strip()
    ids=[]
    for value in request.form.getlist("resource_ids"):
        try: ids.append(int(value))
        except ValueError: pass
    resources=Resource.query.filter(Resource.id.in_(list(dict.fromkeys(ids))),Resource.is_active.is_(True)).all() if ids else []
    if not name or not resources:
        return render_template("resources/bundle_form.html",resources=Resource.query.filter_by(is_active=True).all(),error="أدخل اسم الحزمة واختر موردًا واحدًا على الأقل"),400
    bundle=ResourceBundle(name_ar=name,description_ar=request.form.get("description_ar") or None,bundle_type="group",resources=resources)
    db.session.add(bundle)
    db.session.commit()
    return redirect(url_for("admin.resources"))
