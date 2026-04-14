#!/usr/bin/env python3
"""
Test the tegufox-generate-patch tool with automated input
"""

import subprocess
import sys


def test_pattern_1():
    """Test Pattern 1: Simple Value Override"""
    print("🧪 Testing Pattern 1: Simple Value Override\n")

    # Simulate user input
    inputs = [
        "1",  # Pattern selection
        "mouse-jitter-intensity",  # Patch name
        "widget/nsBaseWidget.cpp",  # File path
        "nsBaseWidget",  # Class name
        "GetMouseJitterIntensity",  # Method name
        "double",  # Return type
        "mouse:jitter:intensity",  # Config key
        "1",  # Type: string -> actually let's use double (2)
        "",  # Params (optional)
        "return 0.0;",  # Original code
        "y",  # Save confirmation
    ]

    # Actually, let me fix the inputs - type "2" is for double
    inputs[7] = "5"  # double is index 5

    input_string = "\n".join(inputs)

    try:
        result = subprocess.run(
            ["python3", "./tegufox-generate-patch"],
            input=input_string,
            text=True,
            capture_output=True,
            cwd="/Users/lugon/dev/2026-3/tegufox-browser",
        )

        print("STDOUT:")
        print(result.stdout)

        if result.returncode != 0:
            print("\nSTDERR:")
            print(result.stderr)
            return False

        # Check if patch was created
        import os

        patch_file = "/Users/lugon/dev/2026-3/tegufox-browser/patches/mouse-jitter-intensity.patch"
        if os.path.exists(patch_file):
            print(f"\n✅ Patch file created: {patch_file}")

            # Show the content
            with open(patch_file, "r") as f:
                content = f.read()
            print("\n📄 Generated patch content:")
            print("─" * 60)
            print(content)
            print("─" * 60)

            return True
        else:
            print(f"\n❌ Patch file not created at {patch_file}")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_pattern_1()
    sys.exit(0 if success else 1)
