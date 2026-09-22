from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from .models import Coach, TrainingProgram, Lesson

bp = Blueprint("training", __name__, url_prefix="/admin/training")

@bp.get("")
@login_required
def ui():
    coaches = Coach.query.filter_by(is_active=True).all()
    programs = TrainingProgram.query.filter_by(is_active=True).order_by(TrainingProgram.id.desc()).all()
    lessons = Lesson.query.filter_by(status="scheduled").order_by(Lesson.starts_at).limit(60).all()
    return render_template("training/index.html", coaches=coaches, programs=programs, lessons=lessons)

@bp.get("/api")
@login_required
def api():
    return jsonify({
        "coaches": Coach.query.filter_by(is_active=True).count(),
        "programs": TrainingProgram.query.filter_by(is_active=True).count(),
        "upcoming": Lesson.query.filter(Lesson.status=="scheduled").count(),
    })
