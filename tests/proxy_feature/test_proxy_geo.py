from tegufox_automation.session import SessionConfig
from tegufox_core.proxy_manager import ProxyManager
import urllib.request
import json
from urllib.parse import urlparse

def _proxy_url_with_creds(proxy_config):
    parsed = urlparse(proxy_config.get("server", ""))
    user = proxy_config.get("username", "")
    pwd = proxy_config.get("password", "")
    if user and pwd:
        return f"{parsed.scheme}://{user}:{pwd}@{parsed.hostname}:{parsed.port}"
    return proxy_config.get("server", "")

def _resolve_proxy_geo(proxy_config):
    proxy_url = _proxy_url_with_creds(proxy_config)
    handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
    opener = urllib.request.build_opener(handler)
    try:
        with opener.open("http://ip-api.com/json?fields=query,timezone", timeout=10) as resp:
            data = json.loads(resp.read())
            return {"ip": data.get("query") or None, "timezone": data.get("timezone") or None}
    except Exception as e:
        print("Error:", e)
        return {"ip": None, "timezone": None}

pm = ProxyManager()
proxy_data = pm.load(pm.list()[0])
proxy_config = {
    "server": f"http://{proxy_data['host']}:{proxy_data['port']}",
    "username": proxy_data["username"],
    "password": proxy_data["password"]
}

print(_resolve_proxy_geo(proxy_config))
