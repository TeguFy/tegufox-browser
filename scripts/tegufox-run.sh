#!/usr/bin/env bash
# Run Tegufox browser
set -e

cd camoufox-source
make run args="$@"
