from flask import Blueprint, jsonify
from .models import Coach, TrainingProgram, Lesson

bp = Blueprint("training", __name__, url_prefix="/admin/training")

@bp.get("")
def index():
    return jsonify({
        "coaches": Coach.query.filter_by(is_active=True).count(),
        "programs": TrainingProgram.query.filter_by(is_active=True).count(),
        "upcoming": Lesson.query.filter(Lesson.status=="scheduled").count(),
    })
