import sys
from tegufox_automation.session import TegufoxSession, SessionConfig
from tegufox_core.proxy_manager import ProxyManager
import socket
from urllib.parse import urlparse

pm = ProxyManager()
proxies = pm.list()
proxy_data = pm.load(proxies[0])

# Using the hostname in the config, relying on TegufoxSession to resolve it
proxy_config = {
    "server": f"http://{proxy_data['host']}:{proxy_data['port']}",
    "username": proxy_data["username"],
    "password": proxy_data["password"]
}

simple_profile = {
    "name": "test-chrome",
    "os": "macos",
    "navigator": {"userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
    "screen": {"width": 1920, "height": 1080},
    "firefox_preferences": {
        "network.trr.mode": 3,
        "network.trr.uri": "https://dns.quad9.net/dns-query"
    }
}

class MockDB:
    def get_profile(self, name): return simple_profile

from unittest.mock import MagicMock
mock_module = MagicMock()
mock_module.ProfileDatabase.return_value = MockDB()
sys.modules['tegufox_core.database'] = mock_module

import tegufox_automation.session
config = SessionConfig(headless=True, proxy=proxy_config)

try:
    with tegufox_automation.session.TegufoxSession(profile="test-chrome", config=config) as session:
        print("Navigating...")
        session.goto("https://httpbin.org/ip")
        print(session.page.content()[:200])
except Exception as e:
    print(f"Error: {e}")
