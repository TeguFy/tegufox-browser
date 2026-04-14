#!/bin/bash
# Test Pattern 5 and 6 generation

echo "=== Testing Pattern 5: Nested Config Access ==="
./tegufox-generate-patch <<EOF
5
webgl-parameter
dom/canvas/WebGLContext.cpp
WebGLContext
GetParameter
webGl:parameters
3379
std::string
std::string
y
EOF

echo ""
echo "=== Testing Pattern 6: Early Return Pattern ==="
./tegufox-generate-patch <<EOF
6
ua-override
dom/base/Navigator.cpp
Navigator
GetUserAgent
navigator.userAgent
1

y
EOF
