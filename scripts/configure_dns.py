"""Importable alias for configure-dns.py (hyphen not valid in module names)."""
import importlib.util
import sys
from pathlib import Path

_src = Path(__file__).parent / "configure-dns.py"
_spec = importlib.util.spec_from_file_location("configure_dns", _src)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# Re-export all public names
from types import ModuleType as _MT
_g = globals()
for _name in dir(_mod):
    if not _name.startswith("_"):
        _g[_name] = getattr(_mod, _name)

DNSConfigurator = _mod.DNSConfigurator
