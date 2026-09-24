from ..users.models import Permission, Role, User
from ..customers.models import Customer
from ..resources.models import Resource, ResourceBundle, Sport, Venue, VenueZone
from ..bookings.models import Booking, BookingAllocation, BookingHold, RecurringBooking, ResourceBlock, WaitlistEntry, BookingMessage, BookingPaymentReceipt
from ..settings.models import SiteSetting, SiteTheme
from ..announcements.models import AnnouncementCard

from ..accounting.models import Account, AccountingVoucher, Branch, CostCenter, FiscalPeriod, JournalEntry, JournalLine
from ..ads.models import AdCampaign, AdCreative, AdPlacement
from ..audit.models import AuditLog
from ..cashier.models import CashRegister, CashShift, CashTransaction
from ..closing.models import FinancialClose
from ..employees.models import Attendance, Department, Employee, Leave, Position
from ..invoices.models import Invoice, InvoiceLine
from ..inventory.models import Product, ProductCategory, StockMovement, Warehouse
from ..live.models import LiveEvent, Stream, Viewer
from ..maintenance.models import MaintenanceRequest, WorkOrder
from ..memberships.models import Membership, MembershipPlan, MembershipRequest, MembershipMessage
from ..news.models import NewsCategory, Post, PostTag
from ..notifications.models import Notification, NotificationLog, NotificationPreference
from ..offers.models import Coupon, Offer, OfferComment, OfferInquiry
from ..packages.models import BookingPackage, CustomerPackage, PackageConsumption
from ..payments.models import Payment, Refund
from ..payroll.models import EmployeeAdvance, PayrollLine, PayrollRun, SalaryStructure
from ..policies.models import BookingPolicy, PaymentPolicy, RefundRequest
from ..pricing.models import PriceOverride, PriceRule
from ..reports.models import SavedReport
from ..shifts.models import EmployeeShift, WorkShift
from ..suppliers.models import PurchaseInvoice, Supplier, SupplierPayment
from ..teams.models import Player, Team, TeamPlayer
from ..tournaments.models import Match, MatchEvent, Tournament, TournamentGroup, TournamentRegistration, TournamentRound
from ..training.models import Coach, Lesson, TrainingProgram
from ..staff.models import ParkVisit, ParkVisitExit, StaffDeduction


def register_models():
    return True
