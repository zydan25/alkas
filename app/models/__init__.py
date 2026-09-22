from .user import Permission, Role, User
from .customer import Customer
from .venue import ResourceBundle, Resource, Sport, Venue, VenueZone
from .booking import Booking, BookingAllocation, BookingHold
from .setting import SiteSetting, SiteTheme
from .announcement import Announcement
from .accounting import Account, JournalEntry, JournalLine


def register_models():
    # Importing models is enough for SQLAlchemy metadata registration.
    return (
        Permission, Role, User, Customer, Venue, VenueZone, Sport,
        Resource, ResourceBundle, Booking, BookingAllocation, BookingHold,
        SiteSetting, SiteTheme, Announcement, Account, JournalEntry, JournalLine,
    )
