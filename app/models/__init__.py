from .user import Permission, Role, User
from .customer import Customer
from .venue import ResourceBundle, Resource, Sport, Venue, VenueZone
from .booking import Booking, BookingAllocation, BookingHold
from .setting import SiteSetting, SiteTheme
from .announcement import Announcement

# Compatibility exports for the accounting domain now living in app/accounting.
from ..accounting.models import Account, CostCenter, FiscalPeriod, JournalEntry, JournalLine

from ..ads.models import AdCampaign, AdCreative, AdPlacement
from ..cashier.models import CashRegister, CashShift, CashTransaction
from ..closing.models import FinancialClose
from ..employees.models import Attendance, Department, Employee, Leave, Position
from ..invoices.models import Invoice, InvoiceLine
from ..inventory.models import Product, ProductCategory, StockMovement, Warehouse
from ..live.models import LiveEvent, Stream, Viewer
from ..maintenance.models import MaintenanceRequest, WorkOrder
from ..memberships.models import Membership, MembershipPlan
from ..news.models import NewsCategory, Post, PostTag
from ..notifications.models import Notification, NotificationLog, NotificationPreference
from ..offers.models import Coupon, Offer, OfferComment, OfferInquiry
from ..packages.models import BookingPackage, CustomerPackage, PackageConsumption
from ..payments.models import Payment, Refund
from ..payroll.models import EmployeeAdvance, PayrollLine, PayrollRun, SalaryStructure
from ..reports.models import SavedReport
from ..shifts.models import EmployeeShift, WorkShift
from ..suppliers.models import PurchaseInvoice, Supplier, SupplierPayment
from ..teams.models import Player, Team, TeamPlayer
from ..tournaments.models import Match, MatchEvent, Tournament, TournamentGroup, TournamentRegistration, TournamentRound
from ..training.models import Coach, Lesson, TrainingProgram


def register_models():
    return (
        Permission, Role, User, Customer, Venue, VenueZone, Sport, Resource, ResourceBundle,
        Booking, BookingAllocation, BookingHold, SiteSetting, SiteTheme, Announcement,
        Account, CostCenter, FiscalPeriod, JournalEntry, JournalLine,
        AdCampaign, AdCreative, AdPlacement, CashRegister, CashShift, CashTransaction,
        FinancialClose, Attendance, Department, Employee, Leave, Position, Invoice, InvoiceLine,
        Product, ProductCategory, StockMovement, Warehouse, LiveEvent, Stream, Viewer,
        MaintenanceRequest, WorkOrder, Membership, MembershipPlan, NewsCategory, Post, PostTag,
        Notification, NotificationLog, NotificationPreference, Coupon, Offer, OfferComment,
        OfferInquiry, BookingPackage, CustomerPackage, PackageConsumption, Payment, Refund,
        EmployeeAdvance, PayrollLine, PayrollRun, SalaryStructure, SavedReport, EmployeeShift,
        WorkShift, PurchaseInvoice, Supplier, SupplierPayment, Player, Team, TeamPlayer,
        Match, MatchEvent, Tournament, TournamentGroup, TournamentRegistration, TournamentRound,
        Coach, Lesson, TrainingProgram,
    )
