from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template

from ..announcements.models import AnnouncementCard
from ..models import Resource, Sport
from ..news.models import Post
from ..offers.models import Offer
from ..live.models import LiveEvent
from ..tournaments.models import Match, Tournament

bp = Blueprint("public", __name__)


@bp.get("/")
def home():
    now = datetime.now(timezone.utc)
    announcements = (
        AnnouncementCard.query
        .filter(AnnouncementCard.status == "published")
        .order_by(AnnouncementCard.priority.desc(), AnnouncementCard.created_at.desc())
        .all()
    )
    announcements = [item for item in announcements if item.visible(now)][:8]
    sports = Sport.query.filter_by(is_active=True).order_by(Sport.sort_order, Sport.id).all()
    resources = Resource.query.filter_by(is_active=True).limit(8).all()
    return render_template("public/home.html", announcements=announcements, sports=sports, resources=resources)


@bp.get("/news")
def news():
    posts = Post.query.filter_by(status="published").order_by(Post.published_at.desc()).limit(50).all()
    return render_template("public/news.html", posts=posts)


@bp.get("/offers")
def offers():
    now = datetime.now(timezone.utc)
    rows = Offer.query.filter(Offer.status == "published").order_by(Offer.priority.desc(), Offer.id.desc()).limit(50).all()
    rows = [offer for offer in rows if (not offer.starts_at or offer.starts_at <= now) and (not offer.ends_at or now < offer.ends_at)]
    return render_template("public/offers.html", offers=rows)


@bp.get("/tournaments")
def tournaments():
    rows = Tournament.query.order_by(Tournament.starts_on.desc(), Tournament.id.desc()).limit(40).all()
    return render_template("public/tournaments.html", tournaments=rows)


@bp.get("/live")
def live():
    events = LiveEvent.query.order_by(LiveEvent.starts_at.desc(), LiveEvent.id.desc()).limit(30).all()
    return render_template("public/live.html", events=events)


@bp.get("/matches")
def matches():
    rows = Match.query.order_by(Match.starts_at.desc(), Match.id.desc()).limit(60).all()
    return render_template("public/matches.html", matches=rows)


@bp.get("/api/sports")
def api_sports():
    sports = Sport.query.filter_by(is_active=True).order_by(Sport.sort_order, Sport.id).all()
    return jsonify([{"id": s.id, "key": s.key, "name_ar": s.name_ar, "icon": s.icon} for s in sports])
