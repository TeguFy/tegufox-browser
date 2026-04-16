# Tegufox Browser - Top-level Build Orchestration
#
# Pipeline:
#   make camoufox-dir    → Apply Camoufox patches to Firefox source
#   make tegufox-patch   → Apply Tegufox patches on top
#   make build           → Compile browser
#   make run             → Launch browser
#
# Full rebuild:
#   make all             → camoufox-dir + tegufox-patch + build
#
# Development:
#   make tegufox-unpatch → Remove Tegufox patches (keep Camoufox)
#   make tegufox-repatch → Remove and re-apply Tegufox patches
#   make generate-patches → Regenerate patches from source tree

.PHONY: help all camoufox-dir tegufox-patch tegufox-unpatch tegufox-repatch \
        build run clean generate-patches status

help:
	@echo "Tegufox Browser Build System"
	@echo ""
	@echo "  make all              - Full pipeline: camoufox-dir + tegufox-patch + build"
	@echo "  make camoufox-dir     - Apply Camoufox patches to Firefox source"
	@echo "  make tegufox-patch    - Apply Tegufox patches on top of Camoufox"
	@echo "  make tegufox-unpatch  - Remove Tegufox patches (revert to Camoufox-only)"
	@echo "  make tegufox-repatch  - Remove and re-apply Tegufox patches"
	@echo "  make build            - Build browser (incremental)"
	@echo "  make run              - Run browser"
	@echo "  make clean            - Full clean (revert to vanilla Firefox)"
	@echo "  make generate-patches - Regenerate Tegufox patches from source"
	@echo "  make status           - Show current source tree state"

all: camoufox-dir tegufox-patch build

camoufox-dir:
	@echo "=== Applying Camoufox patches ==="
	$(MAKE) -C camoufox-source dir

tegufox-patch:
	@echo "=== Applying Tegufox patches ==="
	bash scripts/tegufox-apply-patches.sh

tegufox-unpatch:
	@echo "=== Reverting Tegufox patches ==="
	@FF_VERSION=$$(grep "^version=" camoufox-source/upstream.sh | cut -d= -f2) && \
	FF_RELEASE=$$(grep "^release=" camoufox-source/upstream.sh | cut -d= -f2) && \
	FF_DIR="camoufox-source/camoufox-$${FF_VERSION}-$${FF_RELEASE}" && \
	cd "$$FF_DIR" && \
	git checkout -- . && \
	git clean -fd > /dev/null 2>&1 || true
	@echo "Tegufox patches reverted to camoufox-patched state."

tegufox-repatch: tegufox-unpatch tegufox-patch

build:
	@echo "=== Building Tegufox ==="
	$(MAKE) -C camoufox-source build

run:
	$(MAKE) -C camoufox-source run

clean:
	@echo "=== Cleaning source tree ==="
	$(MAKE) -C camoufox-source revert

generate-patches:
	@echo "=== Regenerating Tegufox patches ==="
	bash scripts/tegufox-generate-patches.sh

status:
	@FF_VERSION=$$(grep "^version=" camoufox-source/upstream.sh | cut -d= -f2) && \
	FF_RELEASE=$$(grep "^release=" camoufox-source/upstream.sh | cut -d= -f2) && \
	FF_DIR="camoufox-source/camoufox-$${FF_VERSION}-$${FF_RELEASE}" && \
	echo "Source: $$FF_DIR" && \
	cd "$$FF_DIR" && \
	echo "Branch: $$(git branch --show-current)" && \
	echo "HEAD: $$(git log --oneline -1)" && \
	echo "Modified files: $$(git status --short | wc -l | xargs)" && \
	echo "Untracked files: $$(git status --short | grep '^?' | wc -l | xargs)"
