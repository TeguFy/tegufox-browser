#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Tegufox Build Script
# Full pipeline: prepare → patch → rebrand → build → verify
# ─────────────────────────────────────────────────────────────
#
# Usage:
#   ./scripts/tegufox-build.sh              # Full build (incremental if possible)
#   ./scripts/tegufox-build.sh --clean      # Clean rebuild
#   ./scripts/tegufox-build.sh --patch-only # Apply patches without building
#   ./scripts/tegufox-build.sh --build-only # Build without re-patching
#
# Prerequisites:
#   - macOS with Xcode CLI tools
#   - Rust toolchain
#   - ~/.mozbuild bootstrapped (run: make bootstrap)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Config ──────────────────────────────────────────────────
FF_VERSION=$(grep "^version=" "$PROJECT_ROOT/camoufox-source/upstream.sh" | cut -d= -f2)
FF_RELEASE=$(grep "^release=" "$PROJECT_ROOT/camoufox-source/upstream.sh" | cut -d= -f2)
FF_SOURCE_DIR="$PROJECT_ROOT/camoufox-source/camoufox-${FF_VERSION}-${FF_RELEASE}"
PATCHES_DIR="$PROJECT_ROOT/patches/tegufox"
SERIES_FILE="$PATCHES_DIR/series"

# Detect arch
ARCH=$(uname -m)
case "$ARCH" in
    arm64)  TARGET="aarch64-apple-darwin" ;;
    x86_64) TARGET="x86_64-apple-darwin" ;;
    *)      echo "Unsupported arch: $ARCH"; exit 1 ;;
esac

OBJ_DIR="$FF_SOURCE_DIR/obj-${TARGET}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${BLUE}[tegufox]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# ── Parse args ──────────────────────────────────────────────
CLEAN=false
PATCH_ONLY=false
BUILD_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --clean)      CLEAN=true ;;
        --patch-only) PATCH_ONLY=true ;;
        --build-only) BUILD_ONLY=true ;;
        --help|-h)
            echo "Usage: $0 [--clean] [--patch-only] [--build-only]"
            exit 0 ;;
        *) warn "Unknown arg: $arg" ;;
    esac
done

# ── Step 0: Verify prerequisites ───────────────────────────
log "Checking prerequisites..."

command -v rustc >/dev/null 2>&1 || err "Rust not installed. Run: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"

if [ ! -d "$HOME/.mozbuild" ]; then
    warn "~/.mozbuild not found. Running bootstrap..."
    cd "$FF_SOURCE_DIR"
    MOZBUILD_STATE_PATH="$HOME/.mozbuild" ./mach --no-interactive bootstrap --application-choice=browser
    cd "$PROJECT_ROOT"
fi

if [ ! -d "$FF_SOURCE_DIR" ]; then
    log "Firefox source not found. Running camoufox setup..."
    make -C "$PROJECT_ROOT/camoufox-source" dir
fi

ok "Prerequisites OK ($(rustc --version), arch=$ARCH)"

# ── Step 1: Clean (optional) ───────────────────────────────
if $CLEAN; then
    log "Cleaning previous build..."
    if [ -d "$OBJ_DIR" ]; then
        cd "$FF_SOURCE_DIR"
        ./mach clobber || rm -rf "$OBJ_DIR"
        cd "$PROJECT_ROOT"
        ok "Build cleaned"
    else
        ok "No previous build to clean"
    fi
fi

# ── Step 2: Apply Tegufox patches ──────────────────────────
if ! $BUILD_ONLY; then
    log "Applying Tegufox patches..."

    # Check if patches are already applied by looking for a marker
    MARKER="$FF_SOURCE_DIR/.tegufox-patched"

    if [ -f "$MARKER" ]; then
        warn "Patches already applied. Re-applying..."
        # Revert to camoufox-patched state first
        cd "$FF_SOURCE_DIR"
        git checkout -- . 2>/dev/null || true
        git clean -fd >/dev/null 2>&1 || true
        cd "$PROJECT_ROOT"
    fi

    # Apply all patches from series
    APPLIED=0
    while IFS= read -r line; do
        line="$(echo "$line" | sed 's/#.*//' | xargs)"
        [ -z "$line" ] && continue
        PATCH_FILE="$PATCHES_DIR/$line"
        if [ ! -f "$PATCH_FILE" ]; then
            err "Patch not found: $PATCH_FILE"
        fi
        echo -n "  $line ... "
        if patch -d "$FF_SOURCE_DIR" -p1 --forward -l --binary -i "$PATCH_FILE" > /dev/null 2>&1; then
            echo -e "${GREEN}OK${NC}"
        else
            # May already be applied
            if patch -d "$FF_SOURCE_DIR" -p1 --forward -l --binary -i "$PATCH_FILE" --dry-run > /dev/null 2>&1; then
                echo -e "${GREEN}OK${NC}"
            else
                echo -e "${YELLOW}SKIP (already applied or conflict)${NC}"
            fi
        fi
        APPLIED=$((APPLIED + 1))
    done < "$SERIES_FILE"

    # ── Step 2b: Rebrand mozconfig ──────────────────────────
    log "Updating mozconfig for Tegufox branding..."
    MOZCONFIG="$FF_SOURCE_DIR/mozconfig"
    if [ -f "$MOZCONFIG" ]; then
        # Change app-name from camoufox to tegufox (branding dir stays camoufox/)
        sed -i '' 's/--with-app-name=camoufox/--with-app-name=tegufox/' "$MOZCONFIG"
        ok "mozconfig: app-name → tegufox"
    else
        err "mozconfig not found at $MOZCONFIG"
    fi

    # Mark as patched
    date > "$MARKER"
    ok "All $APPLIED patches applied + mozconfig updated"
fi

if $PATCH_ONLY; then
    log "Patch-only mode. Skipping build."
    exit 0
fi

# ── Step 3: Build ──────────────────────────────────────────
log "Building Tegufox (this may take 30-90 minutes on first build)..."
log "Target: $TARGET"
log "Source: $FF_SOURCE_DIR"

cd "$FF_SOURCE_DIR"

# Use mach build (incremental if obj-dir exists)
START_TIME=$(date +%s)
./mach build 2>&1 | tee "$PROJECT_ROOT/build.log"
BUILD_EXIT=${PIPESTATUS[0]}
END_TIME=$(date +%s)
ELAPSED=$(( END_TIME - START_TIME ))

cd "$PROJECT_ROOT"

if [ $BUILD_EXIT -ne 0 ]; then
    err "Build failed after ${ELAPSED}s. Check build.log for details."
fi

ok "Build completed in ${ELAPSED}s"

# ── Step 4: Verify ────────────────────────────────────────
log "Verifying build..."

# Find the binary
if [ "$(uname)" = "Darwin" ]; then
    # macOS: look for .app bundle
    APP_BUNDLE=$(find "$OBJ_DIR/dist" -name "*.app" -maxdepth 1 2>/dev/null | head -1)
    if [ -n "$APP_BUNDLE" ]; then
        BINARY="$APP_BUNDLE/Contents/MacOS/tegufox"
        if [ ! -f "$BINARY" ]; then
            # Fallback: might still be named camoufox binary inside
            BINARY="$APP_BUNDLE/Contents/MacOS/camoufox"
        fi
    else
        BINARY="$OBJ_DIR/dist/bin/tegufox"
    fi
else
    BINARY="$OBJ_DIR/dist/bin/tegufox"
fi

if [ -f "$BINARY" ]; then
    ok "Binary found: $BINARY"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Tegufox build complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Binary:  $BINARY"
    echo "  Run:     $BINARY --version"
    echo "  Or:      make run"
    echo ""
    echo "  Set in automation:"
    echo "    export TEGUFOX_BINARY=\"$BINARY\""
    echo ""
    echo "  Or in tegufox_gui.py → Custom Build path"
    echo ""
else
    warn "Binary not found at expected path."
    warn "Checking alternative locations..."
    find "$OBJ_DIR/dist" -name "tegufox" -o -name "camoufox" 2>/dev/null | head -5
    echo ""
    warn "Build may have succeeded but binary name differs. Check obj-dir manually."
fi
