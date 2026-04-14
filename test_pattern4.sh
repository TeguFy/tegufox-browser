#!/bin/bash
# Test Pattern 4 generation with automated input

./tegufox-generate-patch <<EOF
4
screen-dimensions
widget/nsBaseScreen.cpp
nsBaseScreen
GetRect


screen.left, screen.top, screen.width, screen.height
int32
nsRect
return nsRect(values[0], values[1], values[2], values[3]);
y
EOF
