from datetime import datetime, timezone

from flask import Blueprint, Response, jsonify, render_template
from sqlalchemy import or_
import json

from ..ads.models import AdCampaign, AdCreative
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
    ads = (
        AdCreative.query
        .join(AdCampaign, AdCreative.campaign_id == AdCampaign.id)
        .filter(
            AdCreative.status == "active",
            AdCampaign.status == "active",
            or_(AdCampaign.starts_at.is_(None), AdCampaign.starts_at <= now),
            or_(AdCampaign.ends_at.is_(None), AdCampaign.ends_at > now),
        )
        .order_by(AdCreative.priority.desc(), AdCreative.id.desc())
        .limit(8)
        .all()
    )
    announcements = AnnouncementCard.query.filter_by(status="published").order_by(
        AnnouncementCard.priority.desc(), AnnouncementCard.created_at.desc()
    ).all()
    announcements = [item for item in announcements if item.visible(now)][:8]
    sports = Sport.query.filter_by(is_active=True).order_by(Sport.sort_order, Sport.id).all()
    resources = Resource.query.filter_by(is_active=True).limit(8).all()
    live_now = LiveEvent.query.filter_by(status="live").order_by(LiveEvent.starts_at.desc()).limit(3).all()
    return render_template(
        "public/home.html",
        ads=ads,
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


@bp.get("/manifest.webmanifest")
def manifest():
    return Response(
        json.dumps({
            "name": "ملاعب الكأس",
            "short_name": "الكأس",
            "lang": "ar",
            "dir": "rtl",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "background_color": "#f8fafc",
            "theme_color": get_site_color("primary"),
            "icons": [
                {"src": "/static/img/icon-192.svg", "sizes": "192x192", "type": "image/svg+xml"},
                {"src": "/static/img/icon-512.svg", "sizes": "512x512", "type": "image/svg+xml", "purpose": "any maskable"},
            ],
        }, ensure_ascii=False),
        mimetype="application/manifest+json",
    )


@bp.get("/sw.js")
def service_worker():
    js = """const CACHE='alkas-shell-v7';
const SHELL=['/','/static/css/app.css','/static/css/admin.css','/static/css/customer.css','/static/js/app.js','/static/css/public-modern.css','/static/css/admin-modern.css','/static/css/admin-theme.css','/static/img/admin-icons.svg'];
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(e.request.method!=='GET'||u.pathname.startsWith('/api')||u.pathname.startsWith('/admin')) return;
  e.respondWith(fetch(e.request).then(r=>{const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));return r}).catch(()=>caches.match(e.request).then(r=>r||caches.match('/'))));
});"""
    return Response(js,mimetype="application/javascript")


def get_site_color(key):
    try:
        from ..settings.services import get_site_settings
        return get_site_settings()["theme"].get(key, "#0f172a")
    except Exception:
        return "#0f172a"
