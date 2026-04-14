#!/usr/bin/env python3
"""
Debug script to test profile loading
"""

from pathlib import Path
import json

profiles_dir = Path("profiles")
print(f"📁 Profiles directory: {profiles_dir.absolute()}")
print(f"📁 Exists: {profiles_dir.exists()}\n")

if profiles_dir.exists():
    profiles = list(profiles_dir.glob("*.json"))
    print(f"✅ Found {len(profiles)} profile files:\n")

    for profile_file in profiles:
        try:
            with open(profile_file) as f:
                data = json.load(f)
                name = data.get("name", "NO NAME")
                platform = data.get("platform", "NO PLATFORM")
                created = data.get("created", "NO DATE")
                config_count = len(data.get("config", {}))

                print(f"Profile: {name}")
                print(f"  File: {profile_file.name}")
                print(f"  Platform: {platform}")
                print(f"  Created: {created[:19] if created else 'N/A'}")
                print(f"  Config keys: {config_count}")
                print()
        except Exception as e:
            print(f"❌ Error loading {profile_file.name}: {e}\n")
else:
    print("❌ Profiles directory doesn't exist!")
