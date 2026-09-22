from datetime import datetime
from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
from .models import SavedReport
from .services import balance_sheet, booking_report, dashboard_snapshot, financial_summary, income_statement, ledger, trial_balance, utilization_report

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


@bp.get("/ledger/<int:account_id>")
@login_required
def ledger_page(account_id):
    start=request.args.get("start"); end=request.args.get("end")
    try:
        start_date=datetime.strptime(start,"%Y-%m-%d").date() if start else None
        end_date=datetime.strptime(end,"%Y-%m-%d").date() if end else None
        data=ledger(account_id,start_date,end_date)
    except (ValueError,TypeError) as exc:
        return {"error":str(exc)},400
    return render_template("reports/ledger.html",data=data,start=start or "",end=end or "")

@bp.get("/income-statement")
@login_required
def income_page():
    start=request.args.get("start"); end=request.args.get("end")
    try:
        start_date=datetime.strptime(start,"%Y-%m-%d").date() if start else None
        end_date=datetime.strptime(end,"%Y-%m-%d").date() if end else None
    except ValueError:
        return {"error":"التاريخ غير صحيح"},400
    return render_template("reports/income_statement.html",data=income_statement(start_date,end_date),start=start or "",end=end or "")

@bp.get("/balance-sheet")
@login_required
def balance_page():
    end=request.args.get("end")
    try:
        end_date=datetime.strptime(end,"%Y-%m-%d").date() if end else None
    except ValueError:
        return {"error":"التاريخ غير صحيح"},400
    return render_template("reports/balance_sheet.html",data=balance_sheet(end_date),end=end or "")
