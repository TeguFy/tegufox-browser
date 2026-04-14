# Tegufox Patch: canvas-v2

**Type**: fingerprint  
**Created**: 2026-04-13 01:34:40  
**Target File**: dom/canvas/CanvasRenderingContext2D.cpp

## Description

Enhanced canvas fingerprint protection with improved noise injection

## MaskConfig Keys

Document the configuration keys this patch uses:

```json
{
  "canvas-v2:parameter1": "description",
  "canvas-v2:parameter2": "description"
}
```

## Example Configuration

```json
{
  "canvas-v2:parameter1": 42,
  "canvas-v2:parameter2": "value"
}
```

## Testing

1. Apply patch:
   ```bash
   cd /path/to/camoufox-source
   git apply ../tegufox-browser/patches/canvas-v2.patch
   ```

2. Build Camoufox:
   ```bash
   ./mach build
   ```

3. Test with configuration:
   ```python
   from camoufox import Camoufox
   
   config = {
       "canvas-v2:parameter1": 42
   }
   
   with Camoufox(config=config) as browser:
       # Test your patch
       pass
   ```

## Implementation Checklist

- [ ] Patch created and applied
- [ ] MaskConfig integration added
- [ ] Configuration keys documented
- [ ] Test script written
- [ ] Baseline metrics collected
- [ ] Patch tested in isolation
- [ ] Documentation updated

## Notes

Add any implementation notes, gotchas, or future improvements here.
