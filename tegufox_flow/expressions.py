"""Sandboxed Jinja2 environment for flow expressions.

Variable namespaces (passed via context dict): inputs, vars, state, env.
Helpers: now(), today(), uuid(), random_int(a, b).
Filters: slug, tojson, b64encode, b64decode.
"""

from __future__ import annotations
import base64
import json
import random
import re
import secrets
import string
import uuid as _uuid
from datetime import datetime, date
from typing import Any, Dict, Optional

from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment


_SLUG_NONALNUM = re.compile(r"[^a-z0-9]+")


# ---------------------------------------------------------------------------
# Faker — lazy import + per-locale cache.
# ---------------------------------------------------------------------------

_FAKER_CACHE: Dict[str, Any] = {}


def _get_faker(locale: str = "vi_VN"):
    if locale not in _FAKER_CACHE:
        from faker import Faker
        _FAKER_CACHE[locale] = Faker(locale)
    return _FAKER_CACHE[locale]


def _random_email(domain: Optional[str] = None, locale: str = "en_US") -> str:
    fk = _get_faker(locale)
    if domain:
        return f"{fk.user_name()}{random.randint(100, 9999)}@{domain}"
    return fk.email()


def _random_phone(country: str = "vn") -> str:
    if country.lower() == "vn":
        return "0" + str(random.randint(300_000_000, 999_999_999))
    locale_map = {"us": "en_US", "uk": "en_GB", "vn": "vi_VN"}
    return _get_faker(locale_map.get(country.lower(), "en_US")).phone_number()


def _random_name(locale: str = "vi_VN") -> str:
    return _get_faker(locale).name()


def _random_first_name(locale: str = "vi_VN") -> str:
    return _get_faker(locale).first_name()


def _random_last_name(locale: str = "vi_VN") -> str:
    return _get_faker(locale).last_name()


def _random_username(locale: str = "en_US") -> str:
    return f"{_get_faker(locale).user_name()}{random.randint(100, 9999)}"


def _random_password(length: int = 12) -> str:
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(chars) for _ in range(int(length)))


def _random_string(length: int = 8, charset: str = "alnum") -> str:
    presets = {
        "alnum": string.ascii_letters + string.digits,
        "alpha": string.ascii_letters,
        "lower": string.ascii_lowercase,
        "upper": string.ascii_uppercase,
        "digits": string.digits,
        "hex": "0123456789abcdef",
    }
    chars = presets.get(charset, charset)
    return "".join(random.choice(chars) for _ in range(int(length)))


def _random_choice(items):
    return random.choice(list(items))


def _random_address(locale: str = "vi_VN") -> str:
    return _get_faker(locale).address()


def _slug(s: Any) -> str:
    return _SLUG_NONALNUM.sub("-", str(s).lower()).strip("-")


def _tojson(o: Any, indent: int | None = None) -> str:
    return json.dumps(o, ensure_ascii=False, indent=indent, default=str)


def _b64encode(s: Any) -> str:
    if isinstance(s, str):
        s = s.encode("utf-8")
    return base64.b64encode(s).decode("ascii")


def _b64decode(s: Any) -> str:
    return base64.b64decode(str(s)).decode("utf-8")


def _dt_now() -> datetime:  # indirection for monkeypatching in tests
    return datetime.utcnow()


def _today() -> date:
    return _dt_now().date()


class ExpressionEngine:
    def __init__(self) -> None:
        env = SandboxedEnvironment(
            undefined=StrictUndefined,
            autoescape=False,
            keep_trailing_newline=False,
        )
        env.filters.update({
            "slug": _slug,
            "tojson": _tojson,
            "b64encode": _b64encode,
            "b64decode": _b64decode,
        })
        # Use lambdas that dynamically look up the module-level functions
        # This allows monkeypatching in tests
        import sys
        module = sys.modules[__name__]

        env.globals.update({
            "now": lambda: getattr(module, '_dt_now')(),
            "today": lambda: getattr(module, '_today')(),
            "uuid": lambda: str(_uuid.uuid4()),
            "random_int": lambda a, b: random.randint(int(a), int(b)),
            # Faker-backed random data
            "random_email": _random_email,
            "random_phone": _random_phone,
            "random_name": _random_name,
            "random_first_name": _random_first_name,
            "random_last_name": _random_last_name,
            "random_username": _random_username,
            "random_password": _random_password,
            "random_string": _random_string,
            "random_choice": _random_choice,
            "random_address": _random_address,
        })
        self._env = env

    def render(self, template: str, context: Dict[str, Any]) -> str:
        return self._env.from_string(template).render(**context)

    def eval(self, expr: str, context: Dict[str, Any]) -> Any:
        # Use from_string to ensure sandbox checks work properly and to get native Python types
        # compile_expression has issues with deferred SecurityError exceptions
        template_code = "{{ (" + expr + ") }}"

        # Create a temporary environment with a capturing finalize function
        raw_result = [None]
        original_finalize = self._env.finalize

        def capturing_finalize(value):
            raw_result[0] = value
            # Apply the original finalize if it exists
            if original_finalize is not None:
                return original_finalize(value)
            return value

        # Temporarily replace finalize
        self._env.finalize = capturing_finalize
        try:
            template = self._env.from_string(template_code)
            template.render(**context)
            return raw_result[0]
        finally:
            # Restore original finalize
            self._env.finalize = original_finalize
