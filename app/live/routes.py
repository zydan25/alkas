from datetime import datetime
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from ..extensions import db
from .models import LiveEvent, Stream
bp=Blueprint('live',__name__,url_prefix='/admin/live',template_folder='templates')
def _allowed(): return current_user.username=='admin' or current_user.has_permission('live.manage')
@bp.get('')
@login_required
def ui(): return render_template('live/index.html',events=LiveEvent.query.order_by(LiveEvent.starts_at.desc(),LiveEvent.id.desc()).limit(60).all(),streams=Stream.query.order_by(Stream.id.desc()).limit(60).all())
@bp.get('/new')
@login_required
def new():
    if not _allowed(): return {'error':'forbidden'},403
    return render_template('live/form.html')
@bp.post('/new')
@login_required
def create():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        name=(request.form.get('name_ar') or '').strip()
        if not name: raise ValueError('اسم الفعالية مطلوب')
        db.session.add(LiveEvent(name_ar=name,description_ar=request.form.get('description_ar'),event_type=request.form.get('event_type','match'),starts_at=datetime.fromisoformat(request.form['starts_at']) if request.form.get('starts_at') else None,status=request.form.get('status','scheduled'),cover_url=request.form.get('cover_url')));db.session.commit()
    except (KeyError,TypeError,ValueError) as exc: db.session.rollback();return render_template('live/form.html',error=str(exc)),400
    return redirect(url_for('live.ui'))
@bp.post('/stream')
@login_required
def stream_create():
    if not _allowed(): return {'error':'forbidden'},403
    try: db.session.add(Stream(event_id=int(request.form['event_id']),provider=request.form.get('provider','custom'),stream_url=request.form['stream_url'],playback_url=request.form.get('playback_url'),status=request.form.get('status','scheduled')));db.session.commit()
    except (KeyError,TypeError,ValueError) as exc: db.session.rollback();return {'error':str(exc)},400
    return redirect(url_for('live.ui'))
@bp.get('/api')
@login_required
def api(): return jsonify([{'id':e.id,'name_ar':e.name_ar,'status':e.status} for e in LiveEvent.query.order_by(LiveEvent.id.desc()).limit(50).all()])