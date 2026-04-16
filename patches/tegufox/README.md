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
