#!/usr/bin/env bash
#
# Tegufox Phase 2 Setup Script
# 
# Prepares Camoufox-based development environment for Tegufox C++ patches.
# Strategy: Build ON TOP of Camoufox (inherits 38 existing patches).
#
# Usage: ./phase2-setup.sh
#
# Requirements:
# - macOS 11+ or Linux Ubuntu 20.04+
# - 15GB free disk space (Camoufox source)
# - 8GB+ RAM recommended
#
# Author: Tegufox Browser Toolkit
# Date: April 14, 2026
# Phase: 2 - Week 1 Day 1 (Updated)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

# Check disk space (require 15GB for Camoufox)
check_disk_space() {
    log_info "Checking available disk space..."
    
    if [[ "$(detect_os)" == "macos" ]]; then
        available_gb=$(df -g . | tail -1 | awk '{print $4}')
    else
        available_gb=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
    fi
    
    if (( available_gb < 15 )); then
        log_error "Insufficient disk space. Need 15GB, have ${available_gb}GB"
        exit 1
    fi
    
    log_success "Disk space OK: ${available_gb}GB available"
}

# Install Mercurial (not needed for Git-based Camoufox, but kept for compatibility)
install_mercurial() {
    log_info "Checking Mercurial (hg)..."
    
    if command -v hg &> /dev/null; then
        log_success "Mercurial already installed: $(hg --version | head -1)"
        return
    fi
    
    log_warning "Mercurial not found (not required for Camoufox)"
    log_info "Skipping installation (Camoufox uses Git)"
}

# Verify build tools
verify_build_tools() {
    log_info "Verifying build tools..."
    
    local missing_tools=()
    
    # Check required tools
    if ! command -v rustc &> /dev/null; then
        missing_tools+=("rustc (Rust compiler)")
    fi
    
    if ! command -v clang &> /dev/null; then
        missing_tools+=("clang (C/C++ compiler)")
    fi
    
    if ! command -v cmake &> /dev/null; then
        missing_tools+=("cmake")
    fi
    
    if ! command -v ninja &> /dev/null; then
        missing_tools+=("ninja")
    fi
    
    if ! command -v python3 &> /dev/null; then
        missing_tools+=("python3")
    fi
    
    if ! command -v git &> /dev/null; then
        missing_tools+=("git")
    fi
    
    # Report missing tools
    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_error "Missing required build tools:"
        for tool in "${missing_tools[@]}"; do
            echo "  - $tool"
        done
        
        log_info "Install missing tools:"
        if [[ "$(detect_os)" == "macos" ]]; then
            echo "  brew install rust llvm cmake ninja python3 git"
        else
            echo "  sudo apt install rustc clang cmake ninja-build python3 git"
        fi
        
        exit 1
    fi
    
    # Show versions
    log_success "All build tools present:"
    echo "  - Rust: $(rustc --version)"
    echo "  - Clang: $(clang --version | head -1)"
    echo "  - CMake: $(cmake --version | head -1)"
    echo "  - Ninja: $(ninja --version)"
    echo "  - Python: $(python3 --version)"
    echo "  - Git: $(git --version)"
}

# Check if Camoufox source exists
check_camoufox_source() {
    log_info "Checking for Camoufox source directory..."
    
    local camoufox_path="/Users/lugon/dev/2026-3/camoufox-source"
    
    if [ ! -d "$camoufox_path" ]; then
        log_error "Camoufox source not found at: $camoufox_path"
        log_info "Expected location: /Users/lugon/dev/2026-3/camoufox-source"
        log_info ""
        log_info "To clone Camoufox source:"
        log_info "  cd /Users/lugon/dev/2026-3"
        log_info "  git clone https://github.com/daijro/camoufox camoufox-source"
        exit 1
    fi
    
    log_success "Camoufox source found: $camoufox_path"
    
    # Verify it's a valid Camoufox source
    if [ ! -d "$camoufox_path/patches" ]; then
        log_error "Invalid Camoufox source: patches/ directory not found"
        exit 1
    fi
    
    # Count existing patches
    local patch_count=$(find "$camoufox_path/patches" -name "*.patch" -type f | wc -l | tr -d ' ')
    log_info "Found $patch_count existing Camoufox patches"
}

# Fork Camoufox source into tegufox-browser
fork_camoufox() {
    log_info "Forking Camoufox source into tegufox-browser..."
    
    local source_path="/Users/lugon/dev/2026-3/camoufox-source"
    local dest_path="camoufox-source"
    
    if [ -d "$dest_path" ]; then
        log_warning "camoufox-source already exists in tegufox-browser"
        read -p "Delete and recreate? (y/N): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Removing existing camoufox-source..."
            rm -rf "$dest_path"
        else
            log_info "Keeping existing camoufox-source"
            return
        fi
    fi
    
    log_info "Copying Camoufox source (this may take 1-2 minutes)..."
    cp -r "$source_path" "$dest_path"
    
    log_success "Camoufox forked to: $dest_path"
    
    # Count patches
    local patch_count=$(find "$dest_path/patches" -name "*.patch" -type f | wc -l | tr -d ' ')
    log_info "Inherited $patch_count Camoufox patches"
}

# Prepare Camoufox for Tegufox development
prepare_camoufox() {
    log_info "Preparing Camoufox for Tegufox development..."
    
    cd camoufox-source
    
    # Check if Firefox source was already downloaded
    local ff_version=$(grep "^version=" upstream.sh | cut -d= -f2)
    local ff_release=$(grep "^release=" upstream.sh | cut -d= -f2)
    local ff_source_dir="camoufox-${ff_version}-${ff_release}"
    
    log_info "Firefox version: $ff_version (release: $ff_release)"
    
    if [ -d "$ff_source_dir" ]; then
        log_success "Firefox source already exists: $ff_source_dir"
    else
        log_warning "Firefox source not found. Run 'make setup' in camoufox-source/"
        log_info "This will download ~3GB Firefox source and apply Camoufox patches"
    fi
    
    cd ..
}

# Create Tegufox patch directory
create_patch_dir() {
    log_info "Setting up Tegufox patch directory..."
    
    mkdir -p patches/tegufox
    mkdir -p patches/applied
    
    # Create README
    cat > patches/tegufox/README.md << 'EOF'
# Tegufox Patches

This directory contains Tegufox-specific C++ patches that extend Camoufox.

## Patch Priority

### Priority 1 (Week 1-3)
1. **canvas-v2.patch** - Per-domain canvas noise injection
2. **webgl-enhanced.patch** - GPU consistency matrix
3. **audio-context.patch** - Timing noise injection
4. **tls-ja3.patch** - Cipher suite randomization
5. **webrtc-ice-v2.patch** - C++ level ICE interception

### Applying Patches

```bash
cd camoufox-source/camoufox-<version>-<release>
patch -p1 < ../../patches/tegufox/canvas-v2.patch
```

### Generating Patches

```bash
cd camoufox-source/camoufox-<version>-<release>
# Make changes to C++ files
git add -A
git commit -m "Canvas v2: Per-domain noise"
git format-patch -1 HEAD -o ../../patches/tegufox/
```

## See Also

- `TEGUFOX_ARCHITECTURE.md` - Overall architecture
- `PHASE2_PLAN.md` - 3-week development plan
- `CANVAS_V2_SPEC.md` - Canvas v2 technical specification
EOF
    
    log_success "Created patches/tegufox/ directory"
}

# Create Tegufox helper scripts
create_helper_scripts() {
    log_info "Creating Tegufox helper scripts..."
    
    # Tegufox build script
    cat > scripts/tegufox-build.sh << 'EOF'
#!/usr/bin/env bash
# Build Tegufox with Camoufox + Tegufox patches
set -e

cd camoufox-source
make build
cd ..

echo ""
echo "Build complete! Binary location:"
make -C camoufox-source path
EOF
    chmod +x scripts/tegufox-build.sh
    
    # Tegufox run script
    cat > scripts/tegufox-run.sh << 'EOF'
#!/usr/bin/env bash
# Run Tegufox browser
set -e

cd camoufox-source
make run args="$@"
EOF
    chmod +x scripts/tegufox-run.sh
    
    # Apply Tegufox patches script
    cat > scripts/tegufox-apply-patches.sh << 'EOF'
#!/usr/bin/env bash
# Apply Tegufox-specific patches on top of Camoufox
set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <patch-file>"
    echo "Example: $0 patches/tegufox/canvas-v2.patch"
    exit 1
fi

PATCH_FILE="$1"

if [ ! -f "$PATCH_FILE" ]; then
    echo "Error: Patch file not found: $PATCH_FILE"
    exit 1
fi

# Find Camoufox source directory
FF_VERSION=$(grep "^version=" camoufox-source/upstream.sh | cut -d= -f2)
FF_RELEASE=$(grep "^release=" camoufox-source/upstream.sh | cut -d= -f2)
FF_SOURCE_DIR="camoufox-source/camoufox-${FF_VERSION}-${FF_RELEASE}"

if [ ! -d "$FF_SOURCE_DIR" ]; then
    echo "Error: Firefox source not found. Run 'make setup' in camoufox-source/ first"
    exit 1
fi

echo "Applying patch: $PATCH_FILE"
echo "To: $FF_SOURCE_DIR"

cd "$FF_SOURCE_DIR"
patch -p1 < "../../$PATCH_FILE"

echo "Patch applied successfully!"
EOF
    chmod +x scripts/tegufox-apply-patches.sh
    
    log_success "Created helper scripts in scripts/"
}

# Summary and next steps
show_summary() {
    echo ""
    echo "=========================================="
    echo "  Tegufox Phase 2 Setup Complete! ✅"
    echo "=========================================="
    echo ""
    echo "Build Environment:"
    echo "  - Camoufox source: camoufox-source/"
    echo "  - Tegufox patches: patches/tegufox/"
    echo "  - Architecture doc: TEGUFOX_ARCHITECTURE.md"
    echo ""
    echo "Helper Scripts:"
    echo "  - ./scripts/tegufox-build.sh              # Build Tegufox"
    echo "  - ./scripts/tegufox-run.sh                # Run Tegufox"
    echo "  - ./scripts/tegufox-apply-patches.sh      # Apply patch"
    echo ""
    echo "Next Steps:"
    echo ""
    echo "  1. Download Firefox source & apply Camoufox patches:"
    echo "     cd camoufox-source"
    echo "     make setup                # Downloads ~3GB, takes 15-30 min"
    echo "     make dir                  # Applies 32 Camoufox patches"
    echo ""
    echo "  2. (Optional) Bootstrap build environment:"
    echo "     make mozbootstrap         # Installs Firefox build deps"
    echo ""
    echo "  3. Start developing Canvas v2 patch:"
    echo "     cd camoufox-source/camoufox-<version>-<release>"
    echo "     vim dom/canvas/CanvasRenderingContext2D.cpp"
    echo ""
    echo "  4. Build Tegufox (1-2 hours first time):"
    echo "     cd ../../"
    echo "     ./scripts/tegufox-build.sh"
    echo ""
    echo "  5. Test run:"
    echo "     ./scripts/tegufox-run.sh"
    echo ""
    echo "See TEGUFOX_ARCHITECTURE.md for detailed workflow."
    echo ""
}

# Main execution
main() {
    echo ""
    echo "=========================================="
    echo "  Tegufox Phase 2 Setup"
    echo "  Fork Camoufox + Add Tegufox Patches"
    echo "=========================================="
    echo ""
    
    check_disk_space
    install_mercurial
    verify_build_tools
    check_camoufox_source
    
    # Ask before forking (copies ~3GB)
    read -p "Fork Camoufox into tegufox-browser? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        fork_camoufox
        prepare_camoufox
    else
        log_warning "Skipped Camoufox fork"
        log_info "You can run this script again to fork later"
    fi
    
    create_patch_dir
    create_helper_scripts
    
    show_summary
}

# Run main if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
