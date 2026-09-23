from datetime import date, timedelta
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from ..customers.models import Customer
from ..extensions import db
from ..notifications.models import Notification
from .models import Membership, MembershipPlan, MembershipRequest, MembershipMessage

bp=Blueprint("memberships",__name__,url_prefix="/admin/memberships",template_folder="templates")

def _allowed():
    return current_user.username=="admin" or current_user.has_permission("membership.manage")

@bp.get("")
@login_required
def ui():
    if not _allowed():
        return {"error":"forbidden"},403
    return render_template(
        "memberships/index.html",
        plans=MembershipPlan.query.filter_by(is_active=True).order_by(MembershipPlan.id.desc()).all(),
        memberships=Membership.query.order_by(Membership.id.desc()).limit(80).all(),
        requests=MembershipRequest.query.order_by(MembershipRequest.id.desc()).limit(80).all(),
        customers=Customer.query.filter_by(is_active=True).order_by(Customer.name).limit(500).all(),
    )

@bp.get("/new")
@login_required
def new():
    if not _allowed(): return {"error":"forbidden"},403
    return render_template("memberships/form.html",customers=Customer.query.filter_by(is_active=True).order_by(Customer.name).all())

@bp.post("/new")
@login_required
def create():
    if not _allowed(): return {"error":"forbidden"},403
    try:
        name=(request.form.get("name_ar") or "").strip()
        price=request.form.get("price") or 0
        days=int(request.form.get("duration_days") or 30)
        if not name: raise ValueError("اسم الخطة مطلوب")
        if days<=0: raise ValueError("مدة الخطة غير صحيحة")
        if MembershipPlan.query.filter_by(name_ar=name).first(): raise ValueError("الخطة موجودة")
        db.session.add(MembershipPlan(
            name_ar=name,price=price,discount_percent=request.form.get("discount_percent") or 0,
            priority_booking=request.form.get("priority_booking")=="1",duration_days=days
        ))
        db.session.commit()
    except (KeyError,TypeError,ValueError) as exc:
        db.session.rollback()
        return render_template("memberships/form.html",customers=Customer.query.filter_by(is_active=True).order_by(Customer.name).all(),error=str(exc)),400
    return redirect(url_for("memberships.ui"))

@bp.post("/assign")
@login_required
def assign():
    if not _allowed(): return {"error":"forbidden"},403
    try:
        start=date.fromisoformat(request.form.get("starts_on") or date.today().isoformat())
        plan=db.session.get(MembershipPlan,int(request.form["plan_id"]))
        customer=db.session.get(Customer,int(request.form["customer_id"]))
        if not plan or not customer: raise ValueError("العميل أو الخطة غير موجودة")
        membership=Membership(
            customer_id=customer.id,plan_id=plan.id,starts_on=start,
            ends_on=start+timedelta(days=plan.duration_days-1),status="active",
            auto_renew=request.form.get("auto_renew")=="1"
        )
        db.session.add(membership)
        db.session.commit()
    except (KeyError,TypeError,ValueError) as exc:
        db.session.rollback(); return {"error":str(exc)},400
    return redirect(url_for("memberships.ui"))

@bp.post("/requests/<int:request_id>/status")
@login_required
def update_request(request_id):
    if not _allowed(): return {"error":"forbidden"},403
    row=MembershipRequest.query.get_or_404(request_id)
    status=(request.form.get("status") or "").strip()
    reason=(request.form.get("reason_ar") or "").strip() or None
    if status not in {"approved","rejected","cancelled"}:
        return {"error":"الحالة غير صحيحة"},400
    if row.status in {"cancelled","rejected"}:
        return {"error":"لا يمكن تعديل هذا الطلب بعد إغلاقه"},400

    if status=="approved":
        start=row.starts_on or date.today()
        row.starts_on=start
        row.ends_on=start+timedelta(days=max(1,row.duration_days)-1)
        row.status="approved"
        existing=Membership.query.filter_by(customer_id=row.customer_id,plan_id=row.plan_id,starts_on=start).first()
        if not existing:
            db.session.add(Membership(
                customer_id=row.customer_id,plan_id=row.plan_id,starts_on=start,
                ends_on=row.ends_on,status="active",auto_renew=row.auto_renew
            ))
        db.session.add(Notification(
            user_id=row.customer.user_id,
            title_ar="تمت الموافقة على طلب العضوية",
            body_ar=f"تم قبول طلب {row.title_ar}. تبدأ العضوية في {row.starts_on}.",
            kind="membership",priority="high"
        ))
    else:
        row.status=status
        row.cancellation_reason=reason
        label="رفض طلب العضوية" if status=="rejected" else "إلغاء طلب العضوية"
        db.session.add(Notification(
            user_id=row.customer.user_id,
            title_ar=label,
            body_ar=f"{row.title_ar}. {reason or 'راجع تفاصيل الطلب لمزيد من المعلومات.'}",
            kind="membership",priority="normal"
        ))
    db.session.commit()
    return redirect(url_for("memberships.ui"))

@bp.get("/api")
@login_required
def api():
    if not _allowed(): return {"error":"forbidden"},403
    return jsonify({
        "plans":MembershipPlan.query.filter_by(is_active=True).count(),
        "active":Membership.query.filter_by(status="active").count(),
        "pending_requests":MembershipRequest.query.filter_by(status="pending").count(),
    })
