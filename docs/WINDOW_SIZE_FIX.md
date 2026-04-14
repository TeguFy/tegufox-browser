# Tegufox Browser - Window Size Issue - FINAL SOLUTION

**Issue**: Không thấy hết content trong browser window, phải resize window manually

**Root Cause**: Browser window size không match với screen profile size

---

## ✅ SOLUTION: Profile Size Phải Match Với Màn Hình

### Vấn đề Gốc

1. **Profile có screen size** (e.g., 1920x1080)
2. **Camoufox tạo browser window** theo profile size
3. **Màn hình MacBook** chỉ có ~1512px width (scaled)
4. **Kết quả**: Window quá rộng, content bị cut off

### Giải pháp

**Use profile với size phù hợp với màn hình của bạn:**

```bash
# MacBook Pro 14-inch → Use amazon-fba template
./tegufox-config create --platform amazon-fba --name my-laptop
./tegufox-launch profiles/my-laptop.json --url https://ebay.com

# ✅ Window size: 1470x956 → Fits perfectly on your screen!
```

---

## 📐 Profile Templates by Device

| Your Device         | Screen Size | Profile Template | Window Size |
| ------------------- | ----------- | ---------------- | ----------- |
| **MacBook Pro 14"** | 3024x1964   | `amazon-fba`     | 1470x956    |
| **MacBook Pro 16"** | 3456x2234   | Custom           | 1728x1117   |
| **Windows Desktop** | 1920x1080   | `ebay-seller`    | 1920x1080   |
| **4K Monitor**      | 2560x1440   | `etsy-shop`      | 2560x1440   |

---

## 🎯 Quick Fix

### Step 1: Check Your Screen Size

```bash
system_profiler SPDisplaysDataType | grep Resolution
# Output: Resolution: 3024 x 1964 Retina (MacBook Pro 14-inch)
```

### Step 2: Choose Right Profile

**For MacBook 14-inch** (Your Device):
```bash
./tegufox-config create --platform amazon-fba --name macbook-profile
```

**For Windows Desktop**:
```bash
./tegufox-config create --platform ebay-seller --name desktop-profile
```

### Step 3: Launch Browser

```bash
./tegufox-launch profiles/macbook-profile.json --url https://ebay.com
```

**Result**: ✅ Window fits screen perfectly, no manual resize needed!

---

## 🔧 If Window Still Too Large

### Option 1: Edit Profile Size (Recommended)

```bash
# Edit profile JSON file
nano profiles/your-profile.json

# Change screen dimensions:
{
  "config": {
    "screen.width": 1280,    # Smaller width
    "screen.height": 800     # Smaller height
  }
}

# Launch again
./tegufox-launch profiles/your-profile.json
```

### Option 2: Create Custom Size Profile

```bash
# For your specific screen, use smaller safe size
./tegufox-config create --platform generic --name safe-size

# Edit to set size:
# screen.width: 1280 (safe for most laptops)
# screen.height: 800
```

---

## 📱 Android/Mobile Profiles

**Note**: Mobile sizes (360x800) không work với Camoufox - too small for header generation.

**Minimum working size**: ~1024x768

For mobile testing, use desktop browser với mobile User-Agent thay vì tiny window.

---

## ✅ Verification

After launching, check:

- [ ] Can see full eBay header without scrolling?
- [ ] Can see search bar and navigation?
- [ ] Window fits in your screen?
- [ ] No need to manually resize?

**If YES to all** → Profile size is correct! ✅

---

## 📝 Profile Recommendations

### Your MacBook Pro 14-inch

**Best profiles**:
1. `amazon-fba` - 1470x956 ✅ (Perfect fit)
2. `generic` with custom 1280x800 (Safe smaller size)

**Avoid**:
- `ebay-seller` - 1920x1080 (Too wide!)
- `etsy-shop` - 2560x1440 (Way too wide!)

### Why amazon-fba Works

- MacBook 14" scaled resolution: ~1512x982
- amazon-fba profile: 1470x956
- Difference: Only 42px → **Perfect fit!**

---

## 🚀 Complete Workflow

```bash
# 1. Create profile for your device
./tegufox-config create --platform amazon-fba --name my-work-profile

# 2. Validate it
./tegufox-config validate profiles/my-work-profile.json

# 3. Launch browser
./tegufox-launch profiles/my-work-profile.json --url https://ebay.com

# 4. Check if window fits
# ✅ If yes → You're all set!
# ❌ If no → Edit profile to smaller size
```

---

## 📊 Size Guidelines

| Screen Width | Recommended Profile Width | Headroom |
| ------------ | ------------------------- | -------- |
| 1512px       | 1470px                    | 42px     |
| 1728px       | 1680px                    | 48px     |
| 1920px       | 1920px                    | 0px      |
| 2560px       | 2560px                    | 0px      |

**Rule**: Profile width ≤ (Screen width - 50px) for comfortable viewing

---

## ⚠️ Common Mistakes

### ❌ Wrong: Using Windows profile on MacBook

```bash
./tegufox-config create --platform ebay-seller --name test
# ebay-seller = 1920x1080 → TOO BIG for MacBook 14-inch (1512px)
# Result: Window extends beyond screen, can't see right side
```

### ✅ Correct: Using MacBook profile

```bash
./tegufox-config create --platform amazon-fba --name test  
# amazon-fba = 1470x956 → Perfect for MacBook 14-inch
# Result: Window fits perfectly, full content visible
```

---

## 📸 Visual Check

After launching browser:

**✅ Good** (amazon-fba on MacBook):
- Full header visible
- Search bar visible
- All buttons visible
- Window fits screen
- No manual resize needed

**❌ Bad** (ebay-seller on MacBook):
- Header cut off on right
- Can't see some buttons
- Need to scroll horizontally (if allowed)
- Or need to manually resize window smaller

---

## 🎯 Summary

**Problem**: Content không nhìn thấy hết, phải resize window

**Solution**: 
1. Use `amazon-fba` profile for MacBook 14-inch ✅
2. Use `ebay-seller` profile for Windows desktop ✅
3. Match profile size với màn hình của bạn

**Result**: Browser window fits perfectly, không cần manual resize!

---

## 📝 Template Summary

| Template        | Size        | Best For                 |
| --------------- | ----------- | ------------------------ |
| `amazon-fba`    | 1470x956    | MacBook 14-inch ✅       |
| `ebay-seller`   | 1920x1080   | Windows desktop          |
| `etsy-shop`     | 2560x1440   | 4K monitors              |
| `generic`       | 1920x1080   | Standard desktop         |
| `android-mobile`| 360x800     | ❌ Too small (not supported) |

---

**Status**: Issue Resolved ✅  
**Date**: 2026-04-13  
**Device**: MacBook Pro 14-inch (3024x1964 Retina)  
**Solution**: Use amazon-fba template (1470x956)
