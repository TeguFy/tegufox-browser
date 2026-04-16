#!/usr/bin/env bash
# Regenerate Tegufox patches from the current source tree.
#
# This script diffs the current source tree against the camoufox-patched tag
# to produce per-feature patch files.
#
# Prerequisites:
#   - Source tree must have all Tegufox changes applied
#   - The 'camoufox-patched' git tag must exist in the source tree
#
# Usage:
#   ./scripts/tegufox-generate-patches.sh
#
# Must be run from the tegufox-browser project root.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

FF_VERSION=$(grep "^version=" "$PROJECT_ROOT/camoufox-source/upstream.sh" | cut -d= -f2)
FF_RELEASE=$(grep "^release=" "$PROJECT_ROOT/camoufox-source/upstream.sh" | cut -d= -f2)
FF_SOURCE_DIR="$PROJECT_ROOT/camoufox-source/camoufox-${FF_VERSION}-${FF_RELEASE}"

PATCHES_DIR="$PROJECT_ROOT/patches/tegufox"

if [ ! -d "$FF_SOURCE_DIR" ]; then
    echo "Error: Firefox source not found at $FF_SOURCE_DIR"
    exit 1
fi

cd "$FF_SOURCE_DIR"

# Verify camoufox-patched tag exists
if ! git rev-parse camoufox-patched >/dev/null 2>&1; then
    echo "Error: 'camoufox-patched' tag not found in source tree."
    echo "Run 'make camoufox-dir' first to set up the baseline."
    exit 1
fi

# Stage all current changes so we can diff against the index
git add -A

echo "Generating Tegufox patches..."
echo ""

# Feature 1: Canvas v2
echo "  01-canvas-v2.patch"
git diff camoufox-patched --cached -- \
    dom/canvas/TegufoxCanvasNoise.cpp \
    dom/canvas/TegufoxCanvasNoise.h \
    dom/canvas/CanvasRenderingContext2D.cpp \
    dom/canvas/moz.build \
    > "$PATCHES_DIR/01-canvas-v2.patch"

# Feature 2: WebGL Enhanced
echo "  02-webgl-enhanced.patch"
git diff camoufox-patched --cached -- \
    dom/canvas/TegufoxGPUProfiles.cpp \
    dom/canvas/TegufoxGPUProfiles.h \
    dom/canvas/ClientWebGLContext.cpp \
    > "$PATCHES_DIR/02-webgl-enhanced.patch"

# Feature 3: Audio Context v2
echo "  03-audio-context-v2.patch"
git diff camoufox-patched --cached -- \
    dom/media/webaudio/TegufoxAudioNoise.cpp \
    dom/media/webaudio/TegufoxAudioNoise.h \
    dom/media/webaudio/AnalyserNode.cpp \
    dom/media/webaudio/moz.build \
    > "$PATCHES_DIR/03-audio-context-v2.patch"

# Feature 4: TLS JA3/JA4
echo "  04-tls-ja3-ja4.patch"
git diff camoufox-patched --cached -- \
    security/nss/lib/ssl/TegufoxTLSNoise.c \
    security/nss/lib/ssl/TegufoxTLSNoise.h \
    security/nss/lib/ssl/ssl3con.c \
    security/nss/lib/ssl/manifest.mn \
    security/nss/lib/ssl/ssl.gyp \
    > "$PATCHES_DIR/04-tls-ja3-ja4.patch"

# Feature 5: WebRTC ICE v2
echo "  05-webrtc-ice-v2.patch"
git diff camoufox-patched --cached -- \
    dom/media/webrtc/transport/third_party/nICEr/src/ice/ice_candidate.c \
    dom/media/webrtc/transport/third_party/nICEr/src/ice/ice_ctx.c \
    dom/media/webrtc/jsep/JsepSessionImpl.cpp \
    > "$PATCHES_DIR/05-webrtc-ice-v2.patch"

# Feature 6: Font Metrics v2
echo "  06-font-metrics-v2.patch"
git diff camoufox-patched --cached -- \
    gfx/thebes/TegufoxFontNoise.cpp \
    gfx/thebes/TegufoxFontNoise.h \
    gfx/thebes/moz.build \
    layout/style/GeckoBindings.cpp \
    > "$PATCHES_DIR/06-font-metrics-v2.patch"

# Feature 7: HTTP/2 Settings
echo "  07-http2-settings.patch"
git diff camoufox-patched --cached -- \
    netwerk/protocol/http/Http2Session.cpp \
    netwerk/protocol/http/Http2Compression.cpp \
    > "$PATCHES_DIR/07-http2-settings.patch"

# Feature 8: Navigator v2
echo "  08-navigator-v2.patch"
git diff camoufox-patched --cached -- \
    dom/base/Navigator.cpp \
    > "$PATCHES_DIR/08-navigator-v2.patch"

echo ""
echo "All 8 patches regenerated in $PATCHES_DIR"

# Verify no files were missed
TOTAL_DIFFED=$(git diff camoufox-patched --cached --name-only | wc -l | xargs)
echo "Total files with tegufox changes: $TOTAL_DIFFED"
