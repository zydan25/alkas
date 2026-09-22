from ..extensions import db
from ..models import Resource
from .models import MaintenanceRequest


def block_resource(request_id):
    req = db.session.get(MaintenanceRequest, request_id)
    if not req:
        raise ValueError("طلب الصيانة غير موجود")
    resource = db.session.get(Resource, req.resource_id)
    if not resource:
        raise ValueError("المورد غير موجود")
    req.status = "in_progress"
    resource.status = "maintenance"
    db.session.commit()
    return req
