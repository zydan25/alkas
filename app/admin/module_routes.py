from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from ..accounting.models import Account
from ..ads.models import AdCampaign
from ..announcements.models import AnnouncementCard
from ..cashier.models import CashShift
from ..closing.models import FinancialClose
from ..employees.models import Employee
from ..extensions import db
from ..invoices.models import Invoice
from ..inventory.models import Product
from ..live.models import LiveEvent
from ..maintenance.models import MaintenanceRequest
from ..memberships.models import Membership
from ..news.models import Post
from ..notifications.models import Notification
from ..offers.models import Offer
from ..packages.models import CustomerPackage
from ..payments.models import Payment
from ..payroll.models import PayrollRun
from ..reports.models import SavedReport
from ..shifts.models import WorkShift
from ..suppliers.models import Supplier
from ..teams.models import Team
from ..tournaments.models import Tournament
from ..training.models import TrainingProgram


bp = Blueprint("module_ui", __name__, url_prefix="/admin/workspace", template_folder="templates")


def _allowed():
    return current_user.username == "admin" or current_user.has_permission("booking.view")


MODULES = {
    "accounting": ("المحاسبة", "شجرة الحسابات والقيود والفترات والأستاذ", "/admin/accounting/api", Account),
    "invoices": ("الفواتير", "فواتير العملاء والأرصدة والمستحقات", "/admin/invoices/api", Invoice),
    "payments": ("المدفوعات والاسترجاعات", "التحصيل وطرق الدفع والاسترجاعات", "/admin/payments/api", Payment),
    "cashier": ("الصناديق والوردية", "الصناديق والورديات والحركات النقدية", "/admin/cashier/api", CashShift),
    "closing": ("الإقفال المالي", "إقفال اليوم ومطابقة النقد والفرق", "/admin/closing/api", FinancialClose),
    "employees": ("الموظفون", "الملفات الوظيفية والأقسام والحالة", "/admin/employees/api", Employee),
    "payroll": ("الرواتب", "الدورات والرواتب والخصومات والسلف", "/admin/payroll/api", PayrollRun),
    "shifts": ("الورديات", "جداول العمل وتوزيع الموظفين", "/admin/shifts/api", WorkShift),
    "maintenance": ("الصيانة", "بلاغات الأعطال وأوامر العمل وحجب الموارد", "/admin/maintenance/api", MaintenanceRequest),
    "memberships": ("العضويات", "خطط العضوية والاشتراكات النشطة", "/admin/memberships/api", Membership),
    "packages": ("الباقات", "باقات الساعات واستهلاك العملاء", "/admin/packages/api", CustomerPackage),
    "training": ("التدريب", "المدربون والبرامج والحصص", "/admin/training/api", TrainingProgram),
    "tournaments": ("البطولات", "البطولات والمباريات والنتائج", "/admin/tournaments/api", Tournament),
    "teams": ("الفرق واللاعبون", "الفرق وقواعد اللاعبين", "/admin/teams/api", Team),
    "announcements": ("بطاقات الرئيسية", "بطاقات نصية وصورية وفيديو ومؤقتة وروابط", "/admin/announcements/api", AnnouncementCard),
    "news": ("الأخبار", "المقالات والتصنيفات والمحتوى", "/admin/news/api", Post),
    "offers": ("العروض", "العروض والكوبونات والتعليقات والاستفسارات", "/admin/offers/api", Offer),
    "ads": ("الإعلانات", "الحملات الإعلانية والمواد ومواقع العرض", "/admin/ads/api", AdCampaign),
    "live": ("البث المباشر", "الأحداث ومصادر البث والمشاهدون", "/admin/live/api", LiveEvent),
    "notifications": ("الإشعارات", "إشعارات المستخدمين وقنوات الإرسال", "/notifications", Notification),
    "reports": ("التقارير", "لوحات المؤشرات والتقارير المحفوظة", "/admin/reports/dashboard", SavedReport),
    "suppliers": ("الموردون", "الموردون وفواتير المشتريات والمدفوعات", "/admin/suppliers/api", Supplier),
    "inventory": ("المخزون", "المنتجات والمستودعات وحركات المخزون", "/admin/inventory/api", Product),
}


@bp.get("")
@login_required
def index():
    if not _allowed():
        abort(403)
    modules = []
    for slug, (title, description, api, model) in MODULES.items():
        modules.append({
            "slug": slug,
            "title": title,
            "description": description,
            "count": model.query.count() if model is not None else 0,
        })
    return render_template("admin/modules.html", modules=modules)


@bp.get("/<slug>")
@login_required
def module(slug):
    if not _allowed() or slug not in MODULES:
        abort(404)
    title, description, api, model = MODULES[slug]
    return render_template(
        "admin/module.html",
        title=title,
        description=description,
        count=model.query.count() if model is not None else 0,
        api=api,
        module_key=slug,
    )
