import urllib.request
import json
from urllib.parse import urlparse

def _proxy_url_with_creds(proxy):
    parsed = urlparse(proxy.get("server", ""))
    user = proxy.get("username", "")
    pwd = proxy.get("password", "")
    if user and pwd:
        return f"{parsed.scheme}://{user}:{pwd}@{parsed.hostname}:{parsed.port}"
    return proxy.get("server", "")

def _resolve_proxy_geo(proxy):
    proxy_url = _proxy_url_with_creds(proxy)
    handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
    opener = urllib.request.build_opener(handler)
    try:
        with opener.open("http://ip-api.com/json?fields=query,timezone", timeout=5) as resp:
            data = json.loads(resp.read())
            return {"ip": data.get("query"), "timezone": data.get("timezone")}
    except Exception as e:
        print("Geo error:", e)
        return {"ip": None, "timezone": None}
