from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from .models import PayrollRun
bp=Blueprint("payroll",__name__,url_prefix="/admin/payroll")
@bp.get("")
@login_required
def ui():
    return render_template("payroll/index.html", rows=PayrollRun.query.order_by(PayrollRun.id.desc()).limit(60).all())
@bp.get("/api")
@login_required
def api():
    return jsonify([{"id":r.id,"period":r.period_name,"status":r.status,"net":str(r.total_net)} for r in PayrollRun.query.order_by(PayrollRun.id.desc()).limit(24).all()])