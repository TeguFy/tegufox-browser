"""
Tegufox Core - Browser Fingerprinting Engine

Core business logic for profile management, consistency validation,
fingerprint generation, and anti-correlation tracking.
"""

from .consistency_engine import ConsistencyEngine, ConsistencyReport, RuleResult, default_rules
from .fingerprint_registry import FingerprintRegistry
from .profile_manager import ProfileManager, ValidationLevel, BROWSER_TEMPLATES, DOH_PROVIDERS
from .generator_v2 import generate_profile, generate_fleet, sample_browser_os, MARKET_DISTRIBUTIONS
from .webgl_database import WEBGL_CONFIGS

__all__ = [
    # Consistency Engine
    "ConsistencyEngine",
    "ConsistencyReport",
    "RuleResult",
    "default_rules",
    
    # Fingerprint Registry
    "FingerprintRegistry",
    
    # Profile Management
    "ProfileManager",
    "ValidationLevel",
    "BROWSER_TEMPLATES",
    "DOH_PROVIDERS",
    
    # Profile Generation
    "generate_profile",
    "generate_fleet",
    "sample_browser_os",
    "MARKET_DISTRIBUTIONS",
    
    # WebGL Database
    "WEBGL_CONFIGS",
]
