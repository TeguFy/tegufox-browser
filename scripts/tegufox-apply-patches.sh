#!/usr/bin/env bash
# Apply all Tegufox-specific patches on top of Camoufox
#
# Usage:
#   ./scripts/tegufox-apply-patches.sh           # Apply all patches from series
#   ./scripts/tegufox-apply-patches.sh <patch>    # Apply a single patch
#
# Must be run from the tegufox-browser project root.
# Expects Camoufox patches to already be applied (via `make -C camoufox-source dir`).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Resolve source directory from upstream.sh
FF_VERSION=$(grep "^version=" "$PROJECT_ROOT/camoufox-source/upstream.sh" | cut -d= -f2)
FF_RELEASE=$(grep "^release=" "$PROJECT_ROOT/camoufox-source/upstream.sh" | cut -d= -f2)
FF_SOURCE_DIR="$PROJECT_ROOT/camoufox-source/camoufox-${FF_VERSION}-${FF_RELEASE}"

PATCHES_DIR="$PROJECT_ROOT/patches/tegufox"
SERIES_FILE="$PATCHES_DIR/series"

if [ ! -d "$FF_SOURCE_DIR" ]; then
    echo "Error: Firefox source not found at $FF_SOURCE_DIR"
    echo "Run 'make camoufox-dir' first."
    exit 1
fi

apply_patch() {
    local patch_file="$1"
    local patch_name
    patch_name="$(basename "$patch_file")"

    if [ ! -f "$patch_file" ]; then
        echo "Error: Patch file not found: $patch_file"
        exit 1
    fi

    echo "  Applying: $patch_name"
    if ! patch -d "$FF_SOURCE_DIR" -p1 --forward -l --binary -i "$patch_file" > /dev/null 2>&1; then
        echo "  ERROR: Failed to apply $patch_name"
        echo "  Trying verbose apply for diagnostics..."
        patch -d "$FF_SOURCE_DIR" -p1 --forward -l --binary -i "$patch_file"
        exit 1
    fi
}

if [ $# -ge 1 ]; then
    # Single patch mode
    PATCH_FILE="$1"
    if [[ "$PATCH_FILE" != /* ]]; then
        PATCH_FILE="$PROJECT_ROOT/$PATCH_FILE"
    fi
    apply_patch "$PATCH_FILE"
    echo "Done."
    exit 0
fi

# Apply all patches from series file
if [ ! -f "$SERIES_FILE" ]; then
    echo "Error: Series file not found: $SERIES_FILE"
    exit 1
fi

echo "Applying Tegufox patches to: $FF_SOURCE_DIR"
echo ""

APPLIED=0
TOTAL=0

while IFS= read -r line; do
    # Skip comments and empty lines
    line="$(echo "$line" | sed 's/#.*//' | xargs)"
    [ -z "$line" ] && continue

    TOTAL=$((TOTAL + 1))
    apply_patch "$PATCHES_DIR/$line"
    APPLIED=$((APPLIED + 1))
done < "$SERIES_FILE"

echo ""
echo "Successfully applied $APPLIED/$TOTAL Tegufox patches."
