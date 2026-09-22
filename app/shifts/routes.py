from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from .models import WorkShift, EmployeeShift
bp=Blueprint("shifts",__name__,url_prefix="/admin/shifts")
@bp.get("")
@login_required
def ui():
    return render_template("shifts/index.html", shifts=WorkShift.query.filter_by(is_active=True).order_by(WorkShift.start_time).all(), scheduled=EmployeeShift.query.order_by(EmployeeShift.work_date.desc(),EmployeeShift.id.desc()).limit(60).all())
@bp.get("/api")
@login_required
def api():
    return jsonify({"shifts":WorkShift.query.filter_by(is_active=True).count(),"scheduled":EmployeeShift.query.filter_by(status="scheduled").count()})