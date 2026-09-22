from datetime import datetime
from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
from .models import SavedReport
from .services import booking_report, dashboard_snapshot, financial_summary, trial_balance, utilization_report

bp=Blueprint("reports",__name__,url_prefix="/admin/reports",template_folder="templates")

@bp.get("")
@login_required
def ui():
    return render_template("reports/index.html",stats=dashboard_snapshot(),saved=SavedReport.query.filter_by(owner_id=current_user.id).order_by(SavedReport.id.desc()).limit(20).all())

@bp.get("/dashboard")
@login_required
def dashboard():
    return jsonify(dashboard_snapshot())

@bp.get("/api")
@login_required
def api():
    return jsonify(dashboard_snapshot())

@bp.get("/financial")
@login_required
def financial():
    start=request.args.get("start"); end=request.args.get("end")
    start_date=datetime.strptime(start,"%Y-%m-%d").date() if start else None
    end_date=datetime.strptime(end,"%Y-%m-%d").date() if end else None
    return render_template("reports/financial.html",summary=financial_summary(start_date,end_date),trial_balance=trial_balance(),start=start or "",end=end or "")

@bp.get("/operations")
@login_required
def operations():
    start=request.args.get("start"); end=request.args.get("end")
    start_date=datetime.strptime(start,"%Y-%m-%d").date() if start else None
    end_date=datetime.strptime(end,"%Y-%m-%d").date() if end else None
    return render_template("reports/operations.html",booking=booking_report(start_date,end_date),utilization=utilization_report(start_date,end_date),start=start or "",end=end or "")
