from datetime import date
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from ..extensions import db
from .models import Team, Player, TeamPlayer
bp=Blueprint('teams',__name__,url_prefix='/admin/teams',template_folder='templates')
def _allowed(): return current_user.username=='admin' or current_user.has_permission('team.manage')
@bp.get('')
@login_required
def ui(): return render_template('teams/index.html',teams=Team.query.filter_by(is_active=True).order_by(Team.id.desc()).all(),players=Player.query.filter_by(is_active=True).order_by(Player.id.desc()).limit(80).all())
@bp.get('/new')
@login_required
def new():
    if not _allowed(): return {'error':'forbidden'},403
    return render_template('teams/form.html')
@bp.post('/new')
@login_required
def create():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        name=(request.form.get('name_ar') or '').strip()
        if not name: raise ValueError('اسم الفريق مطلوب')
        db.session.add(Team(name_ar=name,short_name=request.form.get('short_name'),logo_url=request.form.get('logo_url')));db.session.commit()
    except (KeyError,TypeError,ValueError) as exc: db.session.rollback();return render_template('teams/form.html',error=str(exc)),400
    return redirect(url_for('teams.ui'))
@bp.get('/players/new')
@login_required
def player_new():
    if not _allowed(): return {'error':'forbidden'},403
    return render_template('teams/player_form.html')
@bp.post('/players/new')
@login_required
def player_create():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        code=(request.form.get('player_code') or '').strip() or f'PLY-{Player.query.count()+1:05d}'
        name=(request.form.get('name_ar') or '').strip()
        if not name: raise ValueError('اسم اللاعب مطلوب')
        if Player.query.filter_by(player_code=code).first(): raise ValueError('كود اللاعب مستخدم')
        db.session.add(Player(player_code=code,name_ar=name,phone=request.form.get('phone'),birth_date=date.fromisoformat(request.form['birth_date']) if request.form.get('birth_date') else None,photo_url=request.form.get('photo_url')));db.session.commit()
    except (KeyError,TypeError,ValueError) as exc: db.session.rollback();return render_template('teams/player_form.html',error=str(exc)),400
    return redirect(url_for('teams.ui'))
@bp.post('/players/assign')
@login_required
def assign_player():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        if TeamPlayer.query.filter_by(team_id=int(request.form['team_id']),player_id=int(request.form['player_id']),status='active').first(): raise ValueError('اللاعب موجود في الفريق')
        db.session.add(TeamPlayer(team_id=int(request.form['team_id']),player_id=int(request.form['player_id']),jersey_number=int(request.form['jersey_number']) if request.form.get('jersey_number') else None,status='active'));db.session.commit()
    except (KeyError,TypeError,ValueError) as exc: db.session.rollback();return {'error':str(exc)},400
    return redirect(url_for('teams.ui'))
@bp.get('/api')
@login_required
def api(): return jsonify({'teams':Team.query.filter_by(is_active=True).count(),'players':Player.query.filter_by(is_active=True).count()})