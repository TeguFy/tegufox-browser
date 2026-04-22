"""GUI Pages for Tegufox Profile Manager"""

from .dashboard_page import DashboardWidget
from .profiles_page import ProfilesListWidget
from .create_profile_page import CreateProfileWidget
from .sessions_page import SessionsWidget
from .settings_page import SettingsWidget

__all__ = [
    "DashboardWidget",
    "ProfilesListWidget",
    "CreateProfileWidget",
    "SessionsWidget",
    "SettingsWidget",
]
