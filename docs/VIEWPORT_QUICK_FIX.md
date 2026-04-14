# Viewport Issue - Quick Fix Guide

**Issue**: Content quá rộng, không nhìn thấy hết trong browser window

**Root Cause**: Đang dùng Windows profile (1920px) trên MacBook (~1470px)

---

## ✅ SOLUTION: Use Device-Appropriate Profile

### For MacBook Users (Your Case)

```bash
# Use amazon-fba template (already has MacBook size)
./tegufox-config create --platform amazon-fba --name my-macbook-profile

# Launch browser
./tegufox-launch profiles/my-macbook-profile.json --url https://ebay.com
```

**Result**: ✅ Perfect rendering, no horizontal scroll!

---

## 📐 Profile Size by Device

### MacBook Pro 14-inch (Your Device)
- **Screen**: 3024x1964 Retina (scaled to ~1512x982)
- **Recommended Profile**: `amazon-fba` (1470x956)
- **Status**: ✅ Works perfectly

### MacBook Pro 16-inch
- **Screen**: 3456x2234 Retina (scaled to ~1728x1117)
- **Recommended**: Create custom profile with 1728x1117

### Windows Desktop
- **Screen**: 1920x1080 (most common)
- **Recommended Profile**: `ebay-seller`, `etsy-shop`, `generic`

### 4K Monitor
- **Screen**: 2560x1440
- **Recommended Profile**: `etsy-shop` (2560x1440)

---

## 🔧 Create Custom Size Profile

If you need different size:

```bash
# 1. Create base profile
./tegufox-config create --platform ebay-seller --name custom-base

# 2. Edit profiles/custom-base.json
nano profiles/custom-base.json

# 3. Change screen.width and screen.height to your device size
{
  "config": {
    "screen.width": 1728,    # Your device width
    "screen.height": 1117    # Your device height
  }
}

# 4. Validate
./tegufox-config validate profiles/custom-base.json

# 5. Launch
./tegufox-launch profiles/custom-base.json
```

---

## 🧪 Test If Size Is Correct

```bash
# Launch browser to eBay
./tegufox-launch profiles/YOUR_PROFILE.json --url https://ebay.com

# Check:
# ✅ Can see full header without scrolling?
# ✅ Search bar visible?
# ✅ Navigation menu visible?
# ✅ Product images display properly?
# ✅ No horizontal scrollbar at bottom?

# If YES to all → Size is correct! ✅
# If NO → Profile size is too large for your screen
```

---

## 📊 Detected Sizes

Your system: **MacBook Pro 14-inch**
- Physical: 3024x1964 Retina
- Scaled: ~1512x982 (default)
- **Recommended profile size**: 1470x956 ✅

---

## 🎯 Quick Commands

```bash
# Check what profiles you have
./tegufox-config list

# Create MacBook profile (best for your device)
./tegufox-config create --platform amazon-fba --name my-laptop

# Launch and test
./tegufox-launch profiles/my-laptop.json --url https://ebay.com

# If eBay looks good → you're all set! ✅
```

---

## ⚠️ Common Mistakes

### ❌ Wrong: Using Windows profile on MacBook
```bash
# ebay-seller template = 1920x1080 (TOO BIG for MacBook)
./tegufox-launch profiles/ebay-seller-profile.json
# Result: Content too wide, can't see everything
```

### ✅ Correct: Using MacBook profile
```bash
# amazon-fba template = 1470x956 (PERFECT for MacBook)
./tegufox-launch profiles/macbook-profile.json
# Result: Perfect fit, no scrolling needed
```

---

## 🚀 Best Practices

1. **Match profile size to your device**
   - MacBook → Use amazon-fba template (1470x956)
   - Desktop → Use ebay-seller template (1920x1080)

2. **Test on actual sites**
   - eBay, Amazon, Etsy should display without horizontal scroll

3. **Create device-specific profiles**
   - One for MacBook (1470x956)
   - One for desktop/external monitor (1920x1080)
   - Switch based on where you're working

4. **Visual check is key**
   - If you can see full page → Correct ✅
   - If you need horizontal scroll → Too big ❌

---

## ✅ Status

- **Issue**: Resolved ✅
- **Root cause**: Device/profile size mismatch
- **Solution**: Use amazon-fba template on MacBook
- **Tested**: eBay displays perfectly ✅

---

**Document Version**: v1.0 - Quick Fix  
**Date**: 2026-04-13  
**Status**: Issue Resolved ✅
