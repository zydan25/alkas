from datetime import datetime
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from ..customers.models import Customer
from ..extensions import db
from ..resources.models import Resource, Sport
from .models import Coach, TrainingProgram, Lesson
bp=Blueprint('training',__name__,url_prefix='/admin/training',template_folder='templates')
def _allowed(): return current_user.username=='admin' or current_user.has_permission('training.manage')
@bp.get('')
@login_required
def ui():
    return render_template('training/index.html',coaches=Coach.query.filter_by(is_active=True).all(),programs=TrainingProgram.query.filter_by(is_active=True).order_by(TrainingProgram.id.desc()).all(),lessons=Lesson.query.filter_by(status='scheduled').order_by(Lesson.starts_at).limit(60).all())
@bp.get('/new')
@login_required
def new():
    if not _allowed(): return {'error':'forbidden'},403
    return render_template('training/form.html',sports=Sport.query.filter_by(is_active=True).all(),coaches=Coach.query.filter_by(is_active=True).all())
@bp.post('/new')
@login_required
def create():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        name=(request.form.get('name_ar') or '').strip(); sport_id=int(request.form['sport_id'])
        if not name: raise ValueError('اسم البرنامج مطلوب')
        db.session.add(TrainingProgram(sport_id=sport_id,coach_id=int(request.form['coach_id']) if request.form.get('coach_id') else None,name_ar=name,description_ar=request.form.get('description_ar'),capacity=int(request.form['capacity']) if request.form.get('capacity') else None,price=request.form.get('price') or 0))
        db.session.commit()
    except (KeyError,TypeError,ValueError) as exc:
        db.session.rollback(); return render_template('training/form.html',sports=Sport.query.filter_by(is_active=True).all(),coaches=Coach.query.filter_by(is_active=True).all(),error=str(exc)),400
    return redirect(url_for('training.ui'))
@bp.get('/lessons/new')
@login_required
def lesson_new():
    if not _allowed(): return {'error':'forbidden'},403
    return render_template('training/lesson_form.html',programs=TrainingProgram.query.filter_by(is_active=True).all(),customers=Customer.query.filter_by(is_active=True).order_by(Customer.name).all(),resources=Resource.query.filter_by(is_active=True).order_by(Resource.id).all())
@bp.post('/lessons/new')
@login_required
def lesson_create():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        start=datetime.fromisoformat(request.form['starts_at']); end=datetime.fromisoformat(request.form['ends_at'])
        if end<=start: raise ValueError('وقت نهاية الحصة يجب أن يكون بعد بدايتها')
        db.session.add(Lesson(program_id=int(request.form['program_id']),customer_id=int(request.form['customer_id']),resource_id=int(request.form['resource_id']) if request.form.get('resource_id') else None,starts_at=start,ends_at=end,status='scheduled'))
        db.session.commit()
    except (KeyError,TypeError,ValueError) as exc:
        db.session.rollback(); return render_template('training/lesson_form.html',programs=TrainingProgram.query.filter_by(is_active=True).all(),customers=Customer.query.filter_by(is_active=True).order_by(Customer.name).all(),resources=Resource.query.filter_by(is_active=True).order_by(Resource.id).all(),error=str(exc)),400
    return redirect(url_for('training.ui'))
@bp.get('/api')
@login_required
def api(): return jsonify({'coaches':Coach.query.filter_by(is_active=True).count(),'programs':TrainingProgram.query.filter_by(is_active=True).count(),'upcoming':Lesson.query.filter(Lesson.status=='scheduled').count()})