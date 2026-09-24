import json

from ..models import SiteSetting, SiteTheme


DEFAULTS = {
    "site_name": "ملاعب الكأس",
    "site_short_name": "الكأس",
    "logo_url": "",
    "favicon_url": "",
    "hero_title": "كل ملاعبك في مكان واحد",
    "hero_subtitle": "احجز، العب، تابع البطولات، واكتشف العروض بسهولة.",
    "booking_hold_minutes": "10",
    "payment_intro": "بعد تأكيد الحجز اتبع بيانات الدفع التالية، ثم ارفع إشعار التحويل من صفحة الحجز.",
    "payment_bank_name": "",
    "payment_account_name": "",
    "payment_account_number": "",
    "payment_wallet_name": "",
    "payment_wallet_number": "",
    "payment_cash_note": "الدفع النقدي متاح لدى الاستقبال حسب سياسة المنشأة.",
    "booking_policy_note": "لا يعتبر الحجز نهائيًا إلا بعد تأكيده. المواعيد المتعارضة تُرفض تلقائيًا.",
    "asset_version": "1",
    "customer_home_theme": "classic",
    "customer_aurora_primary": "#7c3aed",
    "customer_aurora_secondary": "#06b6d4",
    "customer_aurora_accent": "#f472b6",
    "customer_aurora_background": "#070b18",
    "customer_aurora_surface": "#11182b",
    "customer_aurora_text": "#f4f7ff",
}


def get_site_settings():
    values = dict(DEFAULTS)
    rows = SiteSetting.query.filter_by(is_public=True).all()
    for row in rows:
        if row.value_type == "json":
            try:
                values[row.key] = json.loads(row.value or "{}")
            except json.JSONDecodeError:
                values[row.key] = {}
        else:
            values[row.key] = row.value

    theme = SiteTheme.query.filter_by(is_active=True).order_by(SiteTheme.id.desc()).first()
    values["theme"] = {
        "primary": theme.primary_color if theme else "#0f172a",
        "secondary": theme.secondary_color if theme else "#2563eb",
        "accent": theme.accent_color if theme else "#f59e0b",
        "success": theme.success_color if theme else "#16a34a",
        "danger": theme.danger_color if theme else "#dc2626",
        "surface": theme.surface_color if theme else "#ffffff",
        "background": theme.background_color if theme else "#f8fafc",
        "text": theme.text_color if theme else "#0f172a",
        "radius": theme.radius if theme else "18px",
    }
    return values
