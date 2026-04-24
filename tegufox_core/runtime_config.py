"""
Tegufox Runtime Config
Writes runtime.json consumed by C++ patches (DNS + timezone spoofing).

Schema (flat, C++-parseable):
    {
        "timezone": "America/New_York",
        "dns_doh_uri": "https://cloudflare-dns.com/dns-query",
        "dns_strategy": "proxy_socks_dns"  | "doh_only" | "native"
    }

Consumed by:
    - patches/tegufox/11-dns-force-doh.patch      → dns_doh_uri, dns_strategy
    - patches/tegufox/12-timezone-native-spoof.patch → timezone
"""
import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

import httpx


logger = logging.getLogger("tegufox.runtime_config")

DEFAULT_CONFIG_PATH = Path.home() / ".tegufox" / "runtime.json"
DEFAULT_DOH_URI = "https://cloudflare-dns.com/dns-query"


def resolve_config_path(override: Optional[str] = None) -> Path:
    """Resolve runtime.json path: param > env var > default."""
    if override:
        return Path(override).expanduser()
    env_path = os.environ.get("TEGUFOX_RUNTIME_CONFIG")
    if env_path:
        return Path(env_path).expanduser()
    return DEFAULT_CONFIG_PATH


def resolve_proxy_timezone(proxy_config: Dict) -> Optional[str]:
    """Detect IANA timezone from proxy IP via ip-api.com.

    Uses httpx which supports http/https/socks5 proxies natively.
    (urllib.request.ProxyHandler only handles http/https — would silently
    fallback to direct connection for socks5, returning the user's real IP
    timezone instead of the proxy's → exactly the bug that caused the
    timezone mismatch in the first release.)
    """
    server = proxy_config.get("server", "")
    if not server:
        return None
    parsed = urlparse(server)
    user = proxy_config.get("username", "")
    pwd = proxy_config.get("password", "")
    if user and pwd:
        proxy_url = f"{parsed.scheme}://{user}:{pwd}@{parsed.hostname}:{parsed.port}"
    else:
        proxy_url = server
    try:
        with httpx.Client(proxy=proxy_url, timeout=8.0) as client:
            resp = client.get("http://ip-api.com/json?fields=query,timezone")
            data = resp.json()
            tz = data.get("timezone")
            detected_ip = data.get("query")
            logger.info(f"ip-api via proxy: IP={detected_ip} tz={tz}")
            return tz or None
    except Exception as e:
        logger.warning(f"resolve_proxy_timezone failed: {e}")
        return None


def _handle_missing_config(reason: str) -> Dict[str, str]:
    """STRICT strategy: refuse to launch when timezone/DNS cannot be resolved.

    Why: Tegufox's guarantee is no-leak fingerprint spoofing. If we can't
    determine the proxy's timezone, launching with UTC would mismatch the
    proxy's IP timezone and trigger detection (the exact bug user reported).
    Better to fail loud than leak silently.
    """
    raise RuntimeError(
        f"Tegufox runtime config unresolvable: {reason}. "
        "Refusing to launch to prevent fingerprint leak. "
        "Check proxy connectivity or provide timezone manually via "
        "TegufoxSession(timezone='America/New_York')."
    )


def prepare_runtime(
    proxy_config: Optional[Dict] = None,
    timezone: Optional[str] = None,
    doh_uri: str = DEFAULT_DOH_URI,
    config_path: Optional[str] = None,
    dns_strategy_override: Optional[str] = None,
) -> Dict[str, str]:
    """Resolve + persist runtime config. Returns env vars to pass to browser.

    Strategy:
        - If proxy given:    dns_strategy = proxy_socks_dns, TZ from proxy IP
        - If no proxy:       dns_strategy = doh_only (unless overridden)
        - Explicit timezone param always wins over proxy detection.
        - `dns_strategy_override` lets the caller force 'native' (OS DNS) for
          countries where real Firefox doesn't auto-enable DoH — the C++
          patch reads this and decides between MODE_TRRONLY / MODE_TRROFF /
          Firefox-default.

    Returns:
        Dict of env vars: {TZ, CAMOUFOX_TZ_OVERRIDE, TEGUFOX_RUNTIME_CONFIG}
    """
    # Timezone resolution
    resolved_tz = timezone
    if not resolved_tz and proxy_config:
        resolved_tz = resolve_proxy_timezone(proxy_config)
        if not resolved_tz:
            _handle_missing_config(
                "proxy timezone detection failed (ip-api.com unreachable through proxy)"
            )

    # DNS strategy resolution
    if dns_strategy_override:
        dns_strategy = dns_strategy_override
    else:
        dns_strategy = "proxy_socks_dns" if proxy_config else "doh_only"

    target = resolve_config_path(config_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timezone": resolved_tz or "",
        "dns_doh_uri": doh_uri,
        "dns_strategy": dns_strategy,
    }
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(target)
    logger.info(f"Runtime config written: tz={resolved_tz} strategy={dns_strategy} path={target}")

    env = {"TEGUFOX_RUNTIME_CONFIG": str(target)}
    if resolved_tz:
        env["TZ"] = resolved_tz
        env["CAMOUFOX_TZ_OVERRIDE"] = resolved_tz
    return env
