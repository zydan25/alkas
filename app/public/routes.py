from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template

from ..announcements.models import AnnouncementCard
from ..live.models import LiveEvent, Stream
from ..models import Resource, Sport
from ..news.models import Post
from ..offers.models import Offer
from ..teams.models import Team
from ..tournaments.models import Match, Tournament

bp = Blueprint("public", __name__)


@bp.get("/")
def home():
    now = datetime.now(timezone.utc)
    announcements = AnnouncementCard.query.filter_by(status="published").order_by(
        AnnouncementCard.priority.desc(), AnnouncementCard.created_at.desc()
    ).all()
    announcements = [item for item in announcements if item.visible(now)][:8]
    sports = Sport.query.filter_by(is_active=True).order_by(Sport.sort_order, Sport.id).all()
    resources = Resource.query.filter_by(is_active=True).limit(8).all()
    live_now = LiveEvent.query.filter_by(status="live").order_by(LiveEvent.starts_at.desc()).limit(3).all()
    return render_template(
        "public/home.html",
        announcements=announcements,
        sports=sports,
        resources=resources,
        live_now=live_now,
    )


@bp.get("/news")
def news():
    posts = Post.query.filter_by(status="published").order_by(Post.published_at.desc(), Post.id.desc()).limit(60).all()
    return render_template("public/news.html", posts=posts)


@bp.get("/offers")
def offers():
    now = datetime.now(timezone.utc)
    rows = Offer.query.filter_by(status="published").order_by(Offer.priority.desc(), Offer.id.desc()).all()
    rows = [row for row in rows if (row.starts_at is None or row.starts_at <= now) and (row.ends_at is None or row.ends_at > now)]
    return render_template("public/offers.html", offers=rows)


@bp.get("/tournaments")
def tournaments():
    rows = Tournament.query.filter(Tournament.status.in_(["published", "live"])).order_by(Tournament.starts_on.desc(), Tournament.id.desc()).limit(40).all()
    return render_template("public/tournaments.html", tournaments=rows)


@bp.get("/matches")
def matches():
    rows = Match.query.filter(Match.status.in_(["scheduled", "live", "completed"])).order_by(Match.starts_at.desc(), Match.id.desc()).limit(80).all()
    return render_template("public/matches.html", matches=rows)


@bp.get("/live")
def live():
    events = LiveEvent.query.order_by(LiveEvent.starts_at.desc(), LiveEvent.id.desc()).limit(40).all()
    return render_template("public/live.html", events=events)


@bp.get("/live/<int:event_id>")
def live_event(event_id):
    event = LiveEvent.query.get_or_404(event_id)
    stream = Stream.query.filter_by(event_id=event.id).order_by(Stream.id.desc()).first()
    return render_template("public/live_event.html", event=event, stream=stream)


@bp.get("/teams")
def teams():
    rows = Team.query.filter_by(is_active=True).order_by(Team.id.desc()).limit(60).all()
    return render_template("public/teams.html", teams=rows)


@bp.get("/api/sports")
def api_sports():
    sports = Sport.query.filter_by(is_active=True).order_by(Sport.sort_order, Sport.id).all()
    return jsonify([{"id": s.id, "key": s.key, "name_ar": s.name_ar, "icon": s.icon} for s in sports])
