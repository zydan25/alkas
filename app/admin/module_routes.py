from flask import Blueprint, abort, redirect, render_template
from flask_login import current_user, login_required

from ..accounting.models import Account
from ..bookings.models import Booking
from ..customers.models import Customer
from ..resources.models import Resource
from ..users.models import User
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
from ..pricing.models import PriceRule
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
    return current_user.username == "admin" or current_user.has_permission("admin.access")


PERMISSION_BY_SLUG = {
    "accounting":"accounting.view","invoices":"invoice.view","payments":"payment.view","cashier":"cashier.manage",
    "closing":"closing.manage","employees":"employee.view","payroll":"payroll.manage","shifts":"shift.manage",
    "maintenance":"maintenance.view","memberships":"membership.manage","packages":"package.manage","pricing":"pricing.view",
    "training":"training.manage","tournaments":"tournament.manage","teams":"team.manage","announcements":"content.manage",
    "news":"content.manage","offers":"offer.manage","ads":"ads.manage","live":"live.manage","notifications":"admin.access",
    "reports":"reports.view","suppliers":"supplier.manage","inventory":"inventory.manage","bookings":"booking.view",
    "customers":"customer.view","resources":"resource.manage","users":"users.manage","audit":"audit.view","settings":"settings.manage",
}

MODULE_ICONS = {
    "accounting":"ledger","invoices":"file","payments":"money","cashier":"cash","closing":"check",
    "employees":"employee","payroll":"payroll","shifts":"clock","maintenance":"wrench","memberships":"star",
    "packages":"package","pricing":"tag","training":"training","tournaments":"trophy","teams":"team",
    "announcements":"megaphone","news":"news","offers":"percent","ads":"megaphone","live":"broadcast",
    "notifications":"bell","reports":"chart","suppliers":"truck","inventory":"box","bookings":"calendar",
    "customers":"users","resources":"stadium","users":"user","audit":"shield","settings":"settings",
}

MODULES = {
    "accounting": ("المحاسبة", "شجرة الحسابات والقيود والسندات والفروع والفترات", "/admin/accounting/api", Account, "/admin/accounting"),
    "invoices": ("الفواتير", "فواتير العملاء والأرصدة والمستحقات", "/admin/invoices/api", Invoice, "/admin/invoices"),
    "payments": ("المدفوعات والاسترجاعات", "التحصيل وطرق الدفع والاسترجاعات", "/admin/payments/api", Payment, "/admin/payments"),
    "cashier": ("الصناديق والوردية", "الصناديق والورديات والحركات النقدية", "/admin/cashier/api", CashShift, "/admin/cashier"),
    "closing": ("الإقفال المالي", "إقفال اليوم ومطابقة النقد والفرق", "/admin/closing/api", FinancialClose, "/admin/closing"),
    "employees": ("الموظفون", "الملفات الوظيفية والأقسام والحالة", "/admin/employees/api", Employee, "/admin/employees"),
    "payroll": ("الرواتب", "الدورات والرواتب والخصومات والسلف", "/admin/payroll/api", PayrollRun, "/admin/payroll"),
    "shifts": ("الورديات", "جداول العمل وتوزيع الموظفين", "/admin/shifts/api", WorkShift, "/admin/shifts"),
    "maintenance": ("الصيانة", "بلاغات الأعطال وأوامر العمل وحجب الموارد", "/admin/maintenance/api", MaintenanceRequest, "/admin/maintenance"),
    "memberships": ("العضويات", "خطط العضوية والاشتراكات النشطة", "/admin/memberships/api", Membership, "/admin/memberships"),
    "packages": ("الباقات", "باقات الساعات واستهلاك العملاء", "/admin/packages/api", CustomerPackage, "/admin/packages"),
    "pricing": ("التسعير", "قواعد الأسعار والاستثناءات الزمنية", "/admin/pricing/api", PriceRule, "/admin/pricing"),
    "training": ("التدريب", "المدربون والبرامج والحصص", "/admin/training/api", TrainingProgram, "/admin/training"),
    "tournaments": ("البطولات", "البطولات والمباريات والنتائج", "/admin/tournaments/api", Tournament, "/admin/tournaments"),
    "teams": ("الفرق واللاعبون", "الفرق وقواعد اللاعبين", "/admin/teams/api", Team, "/admin/teams"),
    "announcements": ("بطاقات الرئيسية", "بطاقات نصية وصورية وفيديو ومؤقتة وروابط", "/admin/announcements/api", AnnouncementCard, "/admin/announcements"),
    "news": ("الأخبار", "المقالات والتصنيفات والمحتوى", "/admin/news/api", Post, "/admin/news"),
    "offers": ("العروض", "العروض والكوبونات والتعليقات والاستفسارات", "/admin/offers/api", Offer, "/admin/offers"),
    "ads": ("الإعلانات", "الحملات الإعلانية والمواد ومواقع العرض", "/admin/ads/api", AdCampaign, "/admin/ads"),
    "live": ("البث المباشر", "الأحداث ومصادر البث والمشاهدون", "/admin/live/api", LiveEvent, "/admin/live"),
    "notifications": ("الإشعارات", "إشعارات المستخدمين وقنوات الإرسال", "/notifications", Notification, "/notifications"),
    "reports": ("التقارير", "لوحات المؤشرات والتقارير المحفوظة", "/admin/reports/dashboard", SavedReport, "/admin/reports/dashboard"),
    "suppliers": ("الموردون", "الموردون وفواتير المشتريات والمدفوعات", "/admin/suppliers/api", Supplier, "/admin/suppliers"),
    "inventory": ("المخزون", "المنتجات والمستودعات وحركات المخزون", "/admin/inventory/api", Product, "/admin/inventory"),
    "bookings": ("الحجوزات", "التقويم والحجوزات والتعارضات", "/bookings", Booking, "/admin/bookings"),
    "customers": ("العملاء", "ملفات العملاء والهواتف والذمم", "/admin/customers", Customer, "/admin/customers"),
    "resources": ("الملاعب والموارد", "المنشأة والموارد وحزم الحجز", "/admin/resources", Resource, "/admin/resources"),
    "users": ("المستخدمون", "المستخدمون والأدوار والصلاحيات", "/admin/users", User, "/admin/users"),
    "audit": ("سجل التدقيق", "سجل العمليات الحساسة والمراجعة", "/admin/audit", None, "/admin/audit"),
    "settings": ("الإعدادات", "هوية الموقع والثيم وسياسات التشغيل", "/settings", None, "/settings"),
}


@bp.get("")
@login_required
def index():
    if not _allowed():
        abort(403)
    modules = []
    for slug, (title, description, api, model, ui_path) in MODULES.items():
        permission = PERMISSION_BY_SLUG.get(slug, "admin.access")
        if current_user.username != "admin" and not current_user.has_permission(permission):
            continue
        modules.append({
            "slug": slug,
            "title": title,
            "description": description,
            "count": model.query.count() if model is not None else 0,
            "ui_path": ui_path,
            "icon": MODULE_ICONS.get(slug, "grid"),
        })
    return render_template("admin/modules.html", modules=modules)


@bp.get("/<slug>")
@login_required
def module(slug):
    if not _allowed() or slug not in MODULES:
        abort(404)
    _, _, _, _, ui_path = MODULES[slug]
    return redirect(ui_path)
