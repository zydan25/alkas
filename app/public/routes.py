from datetime import datetime, timezone

import json
from flask import Blueprint, Response, jsonify, render_template
from flask_login import current_user
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from ..ads.models import AdCampaign, AdCreative, AdPlacement
from ..announcements.models import AnnouncementCard
from ..live.models import LiveEvent, Stream
from ..models import Booking, BookingAllocation, Customer, Resource, Sport
from ..news.models import Post
from ..offers.models import Offer
from ..teams.models import Team
from ..tournaments.models import Match, Tournament

bp = Blueprint("public", __name__)


def _active_banner_rows(now):
    ads = (
        AdCreative.query
        .join(AdCampaign, AdCreative.campaign_id == AdCampaign.id)
        .join(AdPlacement, AdCreative.placement_id == AdPlacement.id)
        .filter(
            AdCreative.status == "active",
            AdCampaign.status == "active",
            AdPlacement.is_active.is_(True),
            or_(AdCampaign.starts_at.is_(None), AdCampaign.starts_at <= now),
            or_(AdCampaign.ends_at.is_(None), AdCampaign.ends_at > now),
        )
        .order_by(AdCreative.priority.desc(), AdCreative.id.desc())
        .limit(12)
        .all()
    )

    announcements = AnnouncementCard.query.filter_by(status="published").order_by(
        AnnouncementCard.priority.desc(), AnnouncementCard.created_at.desc()
    ).limit(40).all()
    announcements = [item for item in announcements if item.visible(now)][:12]

    banners = []
    for item in ads:
        banners.append(
            {
                "id": f"ad-{item.id}",
                "source": "ad",
                "title_ar": item.title_ar or "إعلان جديد",
                "body_ar": None,
                "label_ar": "إعلان",
                "image_url": item.image_url,
                "video_url": item.video_url,
                "target_url": item.target_url,
                "button_text_ar": "عرض التفاصيل" if item.target_url else None,
                "rotation_seconds": 8,
                "priority": item.priority,
                "order": 1,
            }
        )

    for item in announcements:
        banners.append(
            {
                "id": f"announcement-{item.id}",
                "source": "announcement",
                "title_ar": item.title_ar,
                "body_ar": item.body_ar,
                "label_ar": item.accent_label_ar
                or ("فيديو" if item.video_url else "عرض" if item.image_url else "جديد"),
                "image_url": item.image_url,
                "video_url": item.video_url,
                "target_url": item.target_url,
                "button_text_ar": item.button_text_ar or "عرض التفاصيل",
                "rotation_seconds": item.rotation_seconds,
                "priority": item.priority,
                "order": 0,
            }
        )

    banners.sort(
        key=lambda banner: (
            banner["priority"],
            banner["order"],
            banner["id"],
        ),
        reverse=True,
    )
    return banners[:10]


def _upcoming_matches(now):
    rows = (
        Match.query
        .filter(
            Match.status.in_(["scheduled", "live"]),
            Match.starts_at.is_not(None),
            Match.starts_at >= now,
        )
        .order_by(Match.starts_at.asc(), Match.id.asc())
        .limit(4)
        .all()
    )
    if not rows:
        return []

    team_ids = {
        team_id
        for row in rows
        for team_id in (row.team_a_id, row.team_b_id)
        if team_id
    }
    team_map = {}
    if team_ids:
        team_map = {team.id: team for team in Team.query.filter(Team.id.in_(team_ids)).all()}

    tournament_ids = {row.tournament_id for row in rows if row.tournament_id}
    tournament_map = {}
    if tournament_ids:
        tournament_map = {
            tournament.id: tournament
            for tournament in Tournament.query.filter(Tournament.id.in_(tournament_ids)).all()
        }

    resource_ids = {row.resource_id for row in rows if row.resource_id}
    resource_map = {}
    if resource_ids:
        resource_map = {
            resource.id: resource
            for resource in Resource.query.filter(Resource.id.in_(resource_ids)).all()
        }

    result = []
    for row in rows:
        team_a = team_map.get(row.team_a_id)
        team_b = team_map.get(row.team_b_id)
        resource = resource_map.get(row.resource_id)
        tournament = tournament_map.get(row.tournament_id)
        result.append(
            {
                "id": row.id,
                "starts_at": row.starts_at,
                "status": row.status,
                "score_a": row.score_a,
                "score_b": row.score_b,
                "team_a": team_a.name_ar if team_a else "الفريق الأول",
                "team_b": team_b.name_ar if team_b else "الفريق الثاني",
                "logo_a": team_a.logo_url if team_a else None,
                "logo_b": team_b.logo_url if team_b else None,
                "tournament": tournament.name_ar if tournament else None,
                "resource": resource.name_ar if resource else None,
            }
        )
    return result


@bp.get("/")
def home():
    now = datetime.now(timezone.utc)
    banners = _active_banner_rows(now)

    sports = (
        Sport.query.filter_by(is_active=True)
        .order_by(Sport.sort_order, Sport.id)
        .limit(12)
        .all()
    )

    resources = (
        Resource.query.filter_by(is_active=True)
        .order_by(Resource.id.desc())
        .limit(8)
        .all()
    )

    offers = (
        Offer.query.filter_by(status="published")
        .order_by(Offer.priority.desc(), Offer.id.desc())
        .limit(8)
        .all()
    )
    offers = [
        row
        for row in offers
        if (row.starts_at is None or row.starts_at <= now)
        and (row.ends_at is None or row.ends_at > now)
    ][:4]

    tournaments = (
        Tournament.query.filter(Tournament.status.in_(["published", "live"]))
        .order_by(Tournament.starts_on.asc(), Tournament.id.asc())
        .limit(6)
        .all()
    )

    news_posts = (
        Post.query.filter_by(status="published")
        .order_by(Post.published_at.desc(), Post.id.desc())
        .limit(6)
        .all()
    )

    live_now = (
        LiveEvent.query.filter_by(status="live")
        .order_by(LiveEvent.starts_at.desc(), LiveEvent.id.desc())
        .limit(3)
        .all()
    )

    customer = None
    customer_bookings = []
    if current_user.is_authenticated:
        customer = Customer.query.filter_by(
            user_id=current_user.id,
            is_active=True,
        ).first()
        if customer:
            customer_bookings = (
                Booking.query
                .options(
                    joinedload(Booking.allocations)
                    .joinedload(BookingAllocation.resource)
                )
                .filter_by(customer_id=customer.id)
                .order_by(Booking.start_at.desc(), Booking.id.desc())
                .limit(4)
                .all()
            )

    return render_template(
        "public/home.html",
        banners=banners,
        sports=sports,
        resources=resources,
        live_now=live_now,
        upcoming_matches=_upcoming_matches(now),
        offers=offers,
        tournaments=tournaments,
        news_posts=news_posts,
        customer=customer,
        customer_bookings=customer_bookings,
        today_date=now.astimezone().strftime("%Y-%m-%d"),
    )


@bp.get("/news")
def news():
    posts = (
        Post.query.filter_by(status="published")
        .order_by(Post.published_at.desc(), Post.id.desc())
        .limit(60)
        .all()
    )
    return render_template("public/news.html", posts=posts)


@bp.get("/offers")
def offers():
    now = datetime.now(timezone.utc)
    rows = (
        Offer.query.filter_by(status="published")
        .order_by(Offer.priority.desc(), Offer.id.desc())
        .all()
    )
    rows = [
        row
        for row in rows
        if (row.starts_at is None or row.starts_at <= now)
        and (row.ends_at is None or row.ends_at > now)
    ]
    return render_template("public/offers.html", offers=rows)


@bp.get("/tournaments")
def tournaments():
    rows = (
        Tournament.query.filter(Tournament.status.in_(["published", "live"]))
        .order_by(Tournament.starts_on.desc(), Tournament.id.desc())
        .limit(40)
        .all()
    )
    return render_template("public/tournaments.html", tournaments=rows)


@bp.get("/matches")
def matches():
    rows = (
        Match.query.filter(Match.status.in_(["scheduled", "live", "completed"]))
        .order_by(Match.starts_at.desc(), Match.id.desc())
        .limit(80)
        .all()
    )
    return render_template("public/matches.html", matches=rows)


@bp.get("/live")
def live():
    events = (
        LiveEvent.query.order_by(LiveEvent.starts_at.desc(), LiveEvent.id.desc())
        .limit(40)
        .all()
    )
    return render_template("public/live.html", events=events)


@bp.get("/live/<int:event_id>")
def live_event(event_id):
    event = LiveEvent.query.get_or_404(event_id)
    stream = (
        Stream.query.filter_by(event_id=event.id)
        .order_by(Stream.id.desc())
        .first()
    )
    return render_template("public/live_event.html", event=event, stream=stream)


@bp.get("/teams")
def teams():
    rows = Team.query.filter_by(is_active=True).order_by(Team.id.desc()).limit(60).all()
    return render_template("public/teams.html", teams=rows)


@bp.get("/api/sports")
def api_sports():
    sports = (
        Sport.query.filter_by(is_active=True)
        .order_by(Sport.sort_order, Sport.id)
        .all()
    )
    return jsonify(
        [{"id": s.id, "key": s.key, "name_ar": s.name_ar, "icon": s.icon} for s in sports]
    )


@bp.get("/manifest.webmanifest")
def manifest():
    return Response(
        json.dumps(
            {
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
                    {
                        "src": "/static/img/icon-192.svg",
                        "sizes": "192x192",
                        "type": "image/svg+xml",
                    },
                    {
                        "src": "/static/img/icon-512.svg",
                        "sizes": "512x512",
                        "type": "image/svg+xml",
                        "purpose": "any maskable",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        mimetype="application/manifest+json",
    )


@bp.get("/sw.js")
def service_worker():
    js = """const CACHE='alkas-shell-v12';
const SHELL=['/','/static/css/app.css','/static/css/admin.css','/static/css/customer.css','/static/css/public-modern.css','/static/css/customer-home.css','/static/js/app.js','/static/js/home.js','/static/js/cache-control.js','/static/css/admin-modern.css','/static/css/admin-theme.css','/static/img/admin-icons.svg'];
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('alkas-shell-')&&k!=='alkas-shell-v12').map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(e.request.method!=='GET'||u.pathname.startsWith('/api')||u.pathname.startsWith('/admin')) return;
  e.respondWith(fetch(e.request).then(r=>{const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));return r}).catch(()=>caches.match(e.request).then(r=>r||caches.match('/'))));
});"""
    return Response(js, mimetype="application/javascript")


def get_site_color(key):
    try:
        from ..settings.services import get_site_settings
        return get_site_settings()["theme"].get(key, "#0f172a")
    except Exception:
        return "#0f172a"
