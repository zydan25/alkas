from datetime import datetime

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..utils.media import save_uploaded_media
from .models import AdCampaign, AdCreative, AdPlacement

bp = Blueprint("ads", __name__, url_prefix="/admin/ads", template_folder="templates")


def _allowed():
    return current_user.username == "admin" or current_user.has_permission("ads.manage")


def _render_index(error=None, success=None):
    return render_template(
        "ads/index.html",
        campaigns=AdCampaign.query.order_by(AdCampaign.id.desc()).limit(70).all(),
        creatives=AdCreative.query.order_by(AdCreative.id.desc()).limit(70).all(),
        placements=AdPlacement.query.filter_by(is_active=True).all(),
        error=error,
        success=success,
    )


@bp.get("")
@login_required
def ui():
    return _render_index()


@bp.get("/new")
@login_required
def new():
    if not _allowed():
        return {"error": "forbidden"}, 403
    return render_template(
        "ads/form.html",
        placements=AdPlacement.query.filter_by(is_active=True).all(),
    )


@bp.post("/new")
@login_required
def create():
    if not _allowed():
        return {"error": "forbidden"}, 403
    placements = AdPlacement.query.filter_by(is_active=True).all()
    try:
        name = (request.form.get("name_ar") or "").strip()
        if not name:
            raise ValueError("اسم الحملة مطلوب")

        campaign = AdCampaign(
            name_ar=name,
            advertiser_ar=request.form.get("advertiser_ar"),
            starts_at=datetime.fromisoformat(request.form["starts_at"]) if request.form.get("starts_at") else None,
            ends_at=datetime.fromisoformat(request.form["ends_at"]) if request.form.get("ends_at") else None,
            budget=request.form.get("budget") or None,
            status=request.form.get("status", "draft"),
        )
        db.session.add(campaign)
        db.session.flush()

        image_file = request.files.get("image")
        video_file = request.files.get("video")
        if image_file or video_file:
            placement_id = int(request.form["placement_id"]) if request.form.get("placement_id") else None
            if not placement_id:
                raise ValueError("اختر مكان العرض عند رفع صورة أو فيديو.")

            image_url = save_uploaded_media(image_file, "ads", "image")
            video_url = save_uploaded_media(video_file, "ads", "video")
            if image_url and video_url:
                raise ValueError("اختر صورة أو فيديو واحدًا للمادة الإعلانية.")

            db.session.add(
                AdCreative(
                    campaign_id=campaign.id,
                    placement_id=placement_id,
                    title_ar=request.form.get("creative_title_ar") or name,
                    image_url=image_url,
                    video_url=video_url,
                    target_url=request.form.get("target_url"),
                    priority=int(request.form.get("priority") or 0),
                    status=request.form.get("creative_status", "active"),
                )
            )

        db.session.commit()
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        return render_template("ads/form.html", placements=placements, error=str(exc)), 400
    return redirect(url_for("ads.ui"))


@bp.post("/placement")
@login_required
def placement_create():
    if not _allowed():
        return {"error": "forbidden"}, 403
    key = (request.form.get("key") or "").strip()
    name = (request.form.get("name_ar") or "").strip()
    if not key or not name:
        return {"error": "الكود والاسم مطلوبان"}, 400
    if AdPlacement.query.filter_by(key=key).first():
        return {"error": "موقع العرض موجود"}, 400
    db.session.add(AdPlacement(key=key, name_ar=name))
    db.session.commit()
    return redirect(url_for("ads.ui"))


@bp.post("/creative")
@login_required
def creative_create():
    if not _allowed():
        return {"error": "forbidden"}, 403
    try:
        campaign_id = int(request.form["campaign_id"])
        placement_id = int(request.form["placement_id"])
        image_url = save_uploaded_media(request.files.get("image"), "ads", "image")
        video_url = save_uploaded_media(request.files.get("video"), "ads", "video")

        if not image_url and not video_url:
            raise ValueError("ارفع صورة أو فيديو للمادة الإعلانية.")
        if image_url and video_url:
            raise ValueError("اختر صورة أو فيديو واحدًا للمادة الإعلانية.")

        db.session.add(
            AdCreative(
                campaign_id=campaign_id,
                placement_id=placement_id,
                title_ar=request.form.get("title_ar"),
                image_url=image_url,
                video_url=video_url,
                target_url=request.form.get("target_url"),
                priority=int(request.form.get("priority") or 0),
                status=request.form.get("status", "active"),
            )
        )
        db.session.commit()
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        return _render_index(error=str(exc)), 400

    return redirect(url_for("ads.ui"))


@bp.get("/api")
@login_required
def api():
    return jsonify(
        [
            {"id": x.id, "name_ar": x.name_ar, "status": x.status}
            for x in AdCampaign.query.order_by(AdCampaign.id.desc()).limit(50).all()
        ]
    )
