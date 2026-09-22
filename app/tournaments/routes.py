from datetime import date, datetime
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from ..extensions import db
from ..resources.models import Resource, Sport
from ..teams.models import Team
from .models import Match, Tournament
bp=Blueprint('tournaments',__name__,url_prefix='/admin/tournaments',template_folder='templates')
def _allowed(): return current_user.username=='admin' or current_user.has_permission('tournament.manage')
@bp.get('')
@login_required
def ui(): return render_template('tournaments/index.html',tournaments=Tournament.query.order_by(Tournament.id.desc()).limit(60).all(),matches=Match.query.order_by(Match.starts_at.desc(),Match.id.desc()).limit(60).all())
@bp.get('/new')
@login_required
def new():
    if not _allowed(): return {'error':'forbidden'},403
    return render_template('tournaments/form.html',sports=Sport.query.filter_by(is_active=True).all())
@bp.post('/new')
@login_required
def create():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        name=(request.form.get('name_ar') or '').strip()
        if not name: raise ValueError('اسم البطولة مطلوب')
        start=date.fromisoformat(request.form['starts_on']); end=date.fromisoformat(request.form['ends_on']) if request.form.get('ends_on') else None
        if end and end<start: raise ValueError('تاريخ نهاية البطولة غير صحيح')
        db.session.add(Tournament(name_ar=name,sport_id=int(request.form['sport_id']),starts_on=start,ends_on=end,registration_open=request.form.get('registration_open')=='1',status=request.form.get('status','draft'),entry_fee=request.form.get('entry_fee') or 0,prize_description_ar=request.form.get('prize_description_ar'),rules_ar=request.form.get('rules_ar')));db.session.commit()
    except (KeyError,TypeError,ValueError) as exc: db.session.rollback();return render_template('tournaments/form.html',sports=Sport.query.filter_by(is_active=True).all(),error=str(exc)),400
    return redirect(url_for('tournaments.ui'))
@bp.get('/matches/new')
@login_required
def match_new():
    if not _allowed(): return {'error':'forbidden'},403
    return render_template('tournaments/match_form.html',
        tournaments=Tournament.query.order_by(Tournament.id.desc()).all(),
        teams=Team.query.filter_by(is_active=True).order_by(Team.name_ar).all(),
        resources=Resource.query.filter_by(is_active=True).order_by(Resource.id).all())

@bp.post('/matches/new')
@login_required
def match_create():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        db.session.add(Match(tournament_id=int(request.form['tournament_id']),team_a_id=int(request.form['team_a_id']) if request.form.get('team_a_id') else None,team_b_id=int(request.form['team_b_id']) if request.form.get('team_b_id') else None,resource_id=int(request.form['resource_id']) if request.form.get('resource_id') else None,starts_at=datetime.fromisoformat(request.form['starts_at']) if request.form.get('starts_at') else None,status='scheduled'));db.session.commit()
    except (KeyError,TypeError,ValueError) as exc: db.session.rollback();return {'error':str(exc)},400
    return redirect(url_for('tournaments.ui'))
@bp.get('/api')
@login_required
def api(): return jsonify({'active':Tournament.query.filter(Tournament.status.in_(['published','live'])).count(),'matches':Match.query.filter_by(status='scheduled').count(),'items':[{'id':t.id,'name_ar':t.name_ar,'status':t.status} for t in Tournament.query.order_by(Tournament.id.desc()).limit(40).all()]})