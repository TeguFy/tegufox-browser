# Tegufox Browser - Build Orchestration
#
# Quick start:
#   make tegufox          → Full pipeline (patch + build)
#   make run              → Launch browser
#
# Pipeline:
#   make camoufox-dir     → Apply Camoufox patches to Firefox source
#   make tegufox-patch    → Apply Tegufox patches + branding on top
#   make build            → Compile browser (incremental)
#   make run              → Launch browser
#
# Development:
#   make tegufox-repatch  → Re-apply Tegufox patches (revert first)
#   make generate-patches → Regenerate patches from source tree
#   make gui              → Launch Tegufox GUI
#   make status           → Show source tree state

FF_VERSION := $(shell grep "^version=" camoufox-source/upstream.sh | cut -d= -f2)
FF_RELEASE := $(shell grep "^release=" camoufox-source/upstream.sh | cut -d= -f2)
FF_DIR     := camoufox-source/camoufox-$(FF_VERSION)-$(FF_RELEASE)
ARCH       := $(shell uname -m)

ifeq ($(ARCH),arm64)
  TARGET := aarch64-apple-darwin
else
  TARGET := x86_64-apple-darwin
endif

OBJ_DIR      := $(FF_DIR)/obj-$(TARGET)
BUILD_OUTPUT := build
APP_BUNDLE   := $(OBJ_DIR)/dist/Tegufox.app
BINARY       := $(BUILD_OUTPUT)/Tegufox.app/Contents/MacOS/tegufox
# Fallback if binary is still named camoufox after first build
BINARY_ALT   := $(BUILD_OUTPUT)/Camoufox.app/Contents/MacOS/camoufox
# Source paths (where mach builds to)
SRC_APP_BUNDLE := $(OBJ_DIR)/dist/Tegufox.app
SRC_APP_ALT    := $(OBJ_DIR)/dist/Camoufox.app

.PHONY: help tegufox all camoufox-dir tegufox-patch tegufox-unpatch tegufox-repatch \
        build rebuild run clean generate-patches status gui cli api bootstrap

help:
	@echo "Tegufox Browser Build System"
	@echo ""
	@echo "  make tegufox          - Full pipeline: patch + build (recommended)"
	@echo "  make tegufox --clean  - Clean rebuild from scratch"
	@echo "  make run              - Launch Tegufox browser"
	@echo ""
	@echo "User Interfaces:"
	@echo "  make gui              - Launch Tegufox GUI (profile manager + automation)"
	@echo "  make cli              - Show CLI help"
	@echo "  make api              - Start REST API server (port 8420)"
	@echo ""
	@echo "Build Pipeline:"
	@echo "  make camoufox-dir     - Apply Camoufox patches to Firefox source"
	@echo "  make tegufox-patch    - Apply Tegufox patches + branding"
	@echo "  make build            - Build browser (output: ./build/)"
	@echo "  make rebuild          - Clean + full rebuild (fixes naming)"
	@echo "  make tegufox-repatch  - Revert + re-apply Tegufox patches"
	@echo "  make generate-patches - Regenerate patches from source tree"
	@echo "  make bootstrap        - Setup build environment"
	@echo "  make status           - Show current source tree state"

# ── Main target ─────────────────────────────────────────────
tegufox:
	@bash scripts/tegufox-build.sh

# Legacy alias
all: camoufox-dir tegufox-patch build

# ── Bootstrap ───────────────────────────────────────────────
bootstrap:
	@if [ ! -d "$(FF_DIR)" ]; then \
		echo "=== Fetching Firefox source ==="; \
		$(MAKE) -C camoufox-source setup; \
	fi
	@echo "=== Bootstrapping build environment ==="
	cd $(FF_DIR) && MOZBUILD_STATE_PATH=$$HOME/.mozbuild ./mach --no-interactive bootstrap --application-choice=browser

# ── Camoufox base ───────────────────────────────────────────
camoufox-dir:
	@echo "=== Applying Camoufox patches ==="
	$(MAKE) -C camoufox-source dir

# ── Tegufox patches ─────────────────────────────────────────
tegufox-patch:
	@echo "=== Applying Tegufox patches ==="
	@bash scripts/tegufox-apply-patches.sh
	@echo "=== Updating mozconfig ==="
	@sed -i '' 's/--with-app-name=camoufox/--with-app-name=tegufox/' $(FF_DIR)/mozconfig 2>/dev/null || true
	@echo "Tegufox patches applied + mozconfig updated."

tegufox-unpatch:
	@echo "=== Reverting Tegufox patches ==="
	@cd "$(FF_DIR)" && \
	git checkout -- . && \
	git clean -fd > /dev/null 2>&1 || true
	@rm -f "$(FF_DIR)/.tegufox-patched"
	@echo "Reverted to Camoufox-patched state."

tegufox-repatch: tegufox-unpatch tegufox-patch

# ── Build ───────────────────────────────────────────────────
build:
	@echo "=== Building Tegufox ==="
	cd $(FF_DIR) && ./mach build
	@# Copy properties.json next to binary (camoufox Python package expects it there)
	@cp -f $(SRC_APP_BUNDLE)/Contents/Resources/properties.json $(SRC_APP_BUNDLE)/Contents/MacOS/properties.json 2>/dev/null || \
	 cp -f $(SRC_APP_ALT)/Contents/Resources/properties.json $(SRC_APP_ALT)/Contents/MacOS/properties.json 2>/dev/null || true
	@echo "=== Copying build output to ./build/ ==="
	@mkdir -p $(BUILD_OUTPUT)
	@if [ -d "$(SRC_APP_BUNDLE)" ]; then \
		rm -rf $(BUILD_OUTPUT)/Tegufox.app; \
		cp -R $(SRC_APP_BUNDLE) $(BUILD_OUTPUT)/; \
		echo "✓ Copied Tegufox.app to ./build/"; \
	elif [ -d "$(SRC_APP_ALT)" ]; then \
		rm -rf $(BUILD_OUTPUT)/Camoufox.app; \
		cp -R $(SRC_APP_ALT) $(BUILD_OUTPUT)/; \
		echo "✓ Copied Camoufox.app to ./build/ (run 'make rebuild' to fix naming)"; \
	else \
		echo "✗ Build failed: no app bundle found"; \
		exit 1; \
	fi

rebuild: clean build
	@echo "=== Full rebuild complete ==="

# ── Run ─────────────────────────────────────────────────────
run:
	@if [ -f "$(BINARY)" ]; then \
		echo "Launching: $(BINARY)"; \
		$(BINARY) --no-remote & \
	elif [ -f "$(BINARY_ALT)" ]; then \
		echo "Launching: $(BINARY_ALT)"; \
		$(BINARY_ALT) --no-remote & \
	else \
		echo "Binary not found. Run 'make tegufox' first."; \
		exit 1; \
	fi

# ── User Interfaces ─────────────────────────────────────────
gui:
	@echo "=== Launching Tegufox GUI ==="
	@venv/bin/python3 tegufox-gui

cli:
	@echo "=== Tegufox CLI ==="
	@python3 tegufox-cli --help

api:
	@echo "=== Starting Tegufox API Server ==="
	@echo "Docs: http://localhost:8420/docs"
	@python3 tegufox-cli api start --port 8420

# ── Clean ───────────────────────────────────────────────────
clean:
	@echo "=== Cleaning build artifacts ==="
	@if [ -d "$(OBJ_DIR)" ]; then \
		cd $(FF_DIR) && ./mach clobber; \
	fi
	@rm -rf $(BUILD_OUTPUT)
	@echo "✓ Cleaned ./build/ directory"

distclean:
	@echo "=== Full clean (revert to vanilla Firefox) ==="
	$(MAKE) -C camoufox-source revert

# ── Patches ─────────────────────────────────────────────────
generate-patches:
	@echo "=== Regenerating Tegufox patches ==="
	@bash scripts/tegufox-generate-patches.sh

# ── Status ──────────────────────────────────────────────────
status:
	@echo "Tegufox Browser Status"
	@echo "─────────────────────────────────"
	@echo "Firefox:  $(FF_VERSION)"
	@echo "Release:  $(FF_RELEASE)"
	@echo "Arch:     $(ARCH) ($(TARGET))"
	@echo "Source:   $(FF_DIR)"
	@echo ""
	@if [ -f "$(FF_DIR)/.tegufox-patched" ]; then \
		echo "Patches:  ✓ Applied ($$(cat $(FF_DIR)/.tegufox-patched))"; \
	else \
		echo "Patches:  ✗ Not applied"; \
	fi
	@if [ -f "$(BINARY)" ]; then \
		echo "Binary:   ✓ $(BINARY)"; \
	elif [ -f "$(BINARY_ALT)" ]; then \
		echo "Binary:   ✓ $(BINARY_ALT) (camoufox name)"; \
	else \
		echo "Binary:   ✗ Not built"; \
	fi
	@if [ -d "$(BUILD_OUTPUT)" ]; then \
		echo "Output:   ✓ ./build/ ($$(du -sh $(BUILD_OUTPUT) | cut -f1))"; \
	else \
		echo "Output:   ✗ ./build/ not found"; \
	fi
	@echo ""
	@cd "$(FF_DIR)" && \
	echo "Modified: $$(git status --short | wc -l | xargs) files" && \
	echo "HEAD:     $$(git log --oneline -1)"
