from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from ..ads.models import AdCampaign, AdCreative
from ..announcements.models import AnnouncementCard
from ..cashier.models import CashRegister, CashShift
from ..closing.models import FinancialClose
from ..employees.models import Employee
from ..extensions import db
from ..invoices.models import Invoice
from ..inventory.models import Product, Warehouse
from ..live.models import LiveEvent, Stream
from ..maintenance.models import MaintenanceRequest
from ..memberships.models import Membership, MembershipPlan
from ..news.models import Post
from ..notifications.models import Notification
from ..offers.models import Offer, Coupon
from ..packages.models import BookingPackage, CustomerPackage
from ..payments.models import Payment, Refund
from ..payroll.models import PayrollRun
from ..reports.models import SavedReport
from ..shifts.models import WorkShift
from ..suppliers.models import Supplier, PurchaseInvoice
from ..teams.models import Player, Team
from ..tournaments.models import Tournament, Match
from ..training.models import Coach, TrainingProgram


bp = Blueprint("module_ui", __name__, url_prefix="/admin/workspace", template_folder="templates")


def _allowed():
    return current_user.username == "admin" or current_user.has_permission("booking.view")


MODULES = {
    "accounting": ("المحاسبة", "شجرة الحسابات، القيود، الأستاذ، الفترات والإقفال", "/admin/accounting", "Accounting"),
    "invoices": ("الفواتير", "فواتير العملاء والأرصدة والمستحقات", "/admin/invoices", "Invoice"),
    "payments": ("المدفوعات والاسترجاعات", "التحصيل وطرق الدفع وحالات الاسترجاع", "/admin/payments", "Payment"),
    "cashier": ("الصناديق", "الصناديق والورديات والحركات النقدية", "/admin/cashier", "Cashier"),
    "closing": ("الإقفال المالي", "إغلاق اليوم ومطابقة النقد والفرق", "/admin/closing", "Closing"),
    "employees": ("الموظفون", "الملفات الوظيفية والأقسام والحالة", "/admin/employees", "Employee"),
    "payroll": ("الرواتب", "الدورات والمرتبات والخصومات والسلف", "/admin/payroll", "Payroll"),
    "shifts": ("الورديات", "جداول العمل وتوزيع الموظفين", "/admin/shifts", "Shifts"),
    "maintenance": ("الصيانة", "بلاغات الأعطال وأوامر العمل وحجب الموارد", "/admin/maintenance", "Maintenance"),
    "memberships": ("العضويات", "الباقات والعضويات الفعالة", "/admin/memberships", "Memberships"),
    "packages": ("باقات الساعات", "الباقات واستهلاك ساعات العملاء", "/admin/packages", "Packages"),
    "training": ("التدريب", "المدربون والبرامج والحصص", "/admin/training", "Training"),
    "tournaments": ("البطولات", "البطولات والمباريات والنتائج", "/admin/tournaments", "Tournaments"),
    "teams": ("الفرق واللاعبون", "الفرق واللاعبين وتسجيلاتهم", "/admin/teams", "Teams"),
    "announcements": ("بطاقات الرئيسية", "بطاقات نصية وصورية وفيديو ومؤقتة وروابط", "/admin/announcements", "Announcements"),
    "news": ("الأخبار", "المحتوى المنشور والمقالات والتصنيفات", "/admin/news", "News"),
    "offers": ("العروض", "العروض والكوبونات والتعليقات والاستفسارات", "/admin/offers", "Offers"),
    "ads": ("الإعلانات", "الحملات الإعلانية والمواد والأماكن", "/admin/ads", "Ads"),
    "live": ("البث المباشر", "الأحداث ومصادر البث والمشاهدون", "/admin/live", "Live"),
    "notifications": ("الإشعارات", "إشعارات العملاء والسجل والقنوات", "/notifications", "Notifications"),
    "reports": ("التقارير", "التقارير التشغيلية والمالية المحفوظة", "/admin/reports", "Reports"),
    "suppliers": ("الموردون", "الموردون وفواتير المشتريات والمدفوعات", "/admin/suppliers", "Suppliers"),
    "inventory": ("المخزون", "المنتجات والمستودعات وحركات المخزون", "/admin/inventory", "Inventory"),
}


def _count(slug):
    model_pairs = {
        "invoices": Invoice, "payments": Payment, "cashier": CashShift, "closing": FinancialClose,
        "employees": Employee, "payroll": PayrollRun, "shifts": WorkShift, "maintenance": MaintenanceRequest,
        "memberships": Membership, "packages": CustomerPackage, "training": TrainingProgram,
        "tournaments": Tournament, "teams": Team, "announcements": AnnouncementCard, "news": Post,
        "offers": Offer, "ads": AdCampaign, "live": LiveEvent, "notifications": Notification,
        "reports": SavedReport, "suppliers": Supplier, "inventory": Product,
    }
    model = model_pairs.get(slug)
    return model.query.count() if model is not None else 0


@bp.get("")
@login_required
def index():
    if not _allowed():
        abort(403)
    cards = []
    for slug, (title, description, api, _) in MODULES.items():
        cards.append({
            "slug": slug, "title": title, "description": description,
            "count": _count(slug), "api": api,
        })
    return render_template("admin/modules.html", modules=cards)


@bp.get("/<slug>")
@login_required
def module(slug):
    if not _allowed() or slug not in MODULES:
        abort(404)
    title, description, api, key = MODULES[slug]
    return render_template(
        "admin/module.html",
        title=title,
        description=description,
        count=_count(slug),
        api=api,
        module_key=key,
    )
