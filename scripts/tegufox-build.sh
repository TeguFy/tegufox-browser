#!/usr/bin/env bash
# Build Tegufox with Camoufox + Tegufox patches
set -e

cd camoufox-source
make build
cd ..

echo ""
echo "Build complete! Binary location:"
make -C camoufox-source path
