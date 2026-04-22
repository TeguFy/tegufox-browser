#!/usr/bin/env python3
"""
Semi-automatic WebGL dataset refresh tool.

What this script does:
1. Fetches public WebGL renderer pages.
2. Extracts renderer candidates.
3. Normalizes renderer strings with project rules.
4. Proposes entries for `chrome/windows/*` buckets.
5. Optionally applies the merge directly to `tegufox_core/webgl_dataset.py`.

Examples:
- Preview candidates only:
  python scripts/refresh_webgl_dataset.py

- Apply merge to dataset file:
  python scripts/refresh_webgl_dataset.py --apply

- Use a local HTML snapshot (repeatable CI/dev):
  python scripts/refresh_webgl_dataset.py --source-file /tmp/webgl_values.html --apply
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import html
import json
import pprint
import re
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tegufox_core.webgl_dataset import WEBGL_CONFIGS

DEFAULT_SOURCES = [
    "https://deviceandbrowserinfo.com/learning_zone/articles/webgl_renderer_values",
    "https://blog.castle.io/the-role-of-webgl-renderer-in-browser-fingerprinting/",
]

NOISE_KEYWORDS = (
    "or similar",
    "not available",
    "unknown",
    "microsoft basic render",
    "swiftshader",
    "llvmpipe",
    "softpipe",
)

WEIRD_TOKEN_PATTERN = re.compile(r"(^|\s)[A-Za-z0-9]{7,}#[A-Za-z0-9]{3,}|\b[0-9]{4}\b$")


def normalize_renderer(renderer: str) -> str:
    """Apply project-level normalization for renderer strings."""
    normalized = renderer.replace(", or similar", "")
    normalized = normalized.replace("AMD Radeon R9 200 Series", "AMD Radeon R9 270")
    normalized = normalized.replace("AMD Radeon R7 200 Series", "AMD Radeon R7 270")
    normalized = normalized.replace("AMD Radeon RX 580 Series", "AMD Radeon RX 580")
    normalized = re.sub(r"(AMD Radeon (?:R[0-9]\s+[0-9]{3}|RX\s*[0-9]{3,4}(?:\s+XT)?))\s+Series", r"\1", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def fetch_url(url: str, timeout: int = 20) -> str:
    """Fetch URL contents with a browser-like User-Agent."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="ignore")
    return raw


def extract_renderer_lines(text: str) -> List[str]:
    """Extract likely renderer lines from HTML/plain text."""
    text = html.unescape(text)
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", "\n", text)

    candidates: List[str] = []
    for line in text.splitlines():
        line = line.strip(" \t\r\n-•")
        if not line:
            continue
        # Keep high-confidence renderer formats:
        # - ANGLE + Direct3D11 + shader model (Windows)
        # - ANGLE + OpenGL with Mesa/PCIe (Linux)
        # - ANGLE Metal Renderer: Apple M* (macOS)
        # - ANGLE (Apple, Apple M*, OpenGL 4.1) (macOS)
        # - Apple GPU (Safari iOS)
        if (
            ("ANGLE (" in line and "Direct3D11" in line and "vs_5_0" in line)
            or ("ANGLE (" in line and "OpenGL" in line and ("Mesa" in line or "/PCIe/SSE2" in line))
            or ("ANGLE (Apple" in line and "ANGLE Metal Renderer" in line)
            or ("ANGLE (Apple" in line and "OpenGL 4.1" in line and "Apple M" in line)
            or line == "Apple GPU"
        ):
            candidates.append(line)

    # Keep order but deduplicate.
    dedup: List[str] = []
    seen = set()
    for item in candidates:
        if item in seen:
            continue
        seen.add(item)
        dedup.append(item)
    return dedup


def infer_gpu_bucket(renderer: str) -> Tuple[str, str]:
    """Infer GPU bucket and vendor label for project dataset entries."""
    lower = renderer.lower()
    if lower == "apple gpu":
        return "apple", "Apple Inc."
    if "apple m" in lower and "angle (apple" in lower:
        return "apple", "Google Inc. (Apple)"
    if "nvidia" in lower or "geforce" in lower or "quadro" in lower:
        return "nvidia", "Google Inc. (NVIDIA)"
    if "intel" in lower:
        return "intel", "Google Inc. (Intel)"
    if "amd" in lower or "radeon" in lower or "ati technologies" in lower:
        return "amd", "Google Inc. (AMD)"
    return "", ""


def is_high_quality_renderer(renderer: str) -> bool:
    """Drop noisy/fake renderer strings before candidate mapping."""
    value = (renderer or "").strip()
    if len(value) < 12:
        return False

    lower = value.lower()
    if any(token in lower for token in NOISE_KEYWORDS):
        return False

    if WEIRD_TOKEN_PATTERN.search(value):
        return False

    # ANGLE entries should be structurally sane.
    if "ANGLE (" in value:
        if value.count("(") != value.count(")"):
            return False
        if "direct3d11" in lower and "vs_5_0" not in lower:
            return False

    # Apple family should explicitly mention Apple M-series chip or Apple GPU.
    if "apple" in lower and "angle (apple" in lower and "apple m" not in lower and lower != "apple gpu":
        return False

    return True


def _extract_apple_chip(renderer: str) -> Optional[str]:
    """Extract Apple chip name from ANGLE strings."""
    m = re.search(r"ANGLE Metal Renderer:\s*(Apple\s+M[0-9][^,)]*)", renderer)
    if m:
        return m.group(1).strip()
    m = re.search(r"ANGLE\s*\(Apple,\s*(Apple\s+M[0-9][^,)]*)", renderer)
    if m:
        return m.group(1).strip()
    return None


def _extract_gpu_from_d3d_angle(renderer: str) -> str:
    """Extract plain GPU model from ANGLE Direct3D11 renderer for Firefox buckets."""
    m = re.search(r"ANGLE\s*\([^,]+,\s*(.+?)\s+Direct3D11", renderer)
    if not m:
        return ""
    gpu = m.group(1)
    gpu = re.sub(r"\s*\(0x[0-9A-Fa-f]+\)", "", gpu)
    return gpu.strip()


def _extract_gpu_from_angle_opengl(renderer: str) -> str:
    """Extract GPU segment from ANGLE OpenGL renderer strings."""
    m = re.search(r"ANGLE\s*\([^,]+,\s*(.+?),\s*OpenGL", renderer)
    if not m:
        return ""
    return m.group(1).strip()


def infer_merge_targets(bucket: str, renderer: str) -> List[Tuple[str, str, Optional[str], str, str]]:
    """Map one candidate renderer into concrete dataset targets.

    Returns tuples: (browser, os, gpu_bucket_or_none_for_list, vendor, renderer)
    """
    targets: List[Tuple[str, str, Optional[str], str, str]] = []
    lower = renderer.lower()

    if bucket == "apple":
        if lower == "apple gpu":
            targets.append(("safari", "ios", None, "Apple Inc.", "Apple GPU"))
            return targets

        chip = _extract_apple_chip(renderer)
        if not chip:
            return targets

        targets.append(("chrome", "macos", "apple", "Google Inc. (Apple)", renderer))
        targets.append(("firefox", "macos", "apple", "Apple", chip))
        targets.append(("safari", "macos", "apple", "Apple Inc.", chip))
        return targets

    # Windows D3D11 ANGLE -> Chrome + Firefox windows buckets.
    if "angle (" in lower and "direct3d11" in lower and "vs_5_0" in lower:
        chrome_vendor = {
            "intel": "Google Inc. (Intel)",
            "nvidia": "Google Inc. (NVIDIA)",
            "amd": "Google Inc. (AMD)",
        }.get(bucket, "")
        firefox_vendor = {
            "intel": "Intel",
            "nvidia": "NVIDIA Corporation",
            "amd": "AMD",
        }.get(bucket, "")

        if chrome_vendor:
            targets.append(("chrome", "windows", bucket, chrome_vendor, renderer))

        firefox_gpu = _extract_gpu_from_d3d_angle(renderer)
        if firefox_vendor and firefox_gpu:
            targets.append(("firefox", "windows", bucket, firefox_vendor, firefox_gpu))

    # Linux ANGLE OpenGL (Mesa/PCIe) -> Chrome + Firefox linux buckets.
    if "angle (" in lower and "opengl" in lower and ("mesa" in lower or "/pcie/sse2" in lower):
        chrome_vendor = {
            "intel": "Google Inc. (Intel)",
            "nvidia": "Google Inc. (NVIDIA)",
            "amd": "Google Inc. (AMD)",
        }.get(bucket, "")
        firefox_vendor = {
            "intel": "Intel",
            "nvidia": "NVIDIA Corporation",
            "amd": "AMD",
        }.get(bucket, "")

        if chrome_vendor:
            targets.append(("chrome", "linux", bucket, chrome_vendor, renderer))

        firefox_gpu = _extract_gpu_from_angle_opengl(renderer)
        if firefox_vendor and firefox_gpu:
            targets.append(("firefox", "linux", bucket, firefox_vendor, firefox_gpu))

    return targets


def build_candidates(lines: List[str]) -> Dict[str, List[Dict[str, str]]]:
    """Convert raw renderer lines into dataset entry candidates."""
    by_bucket: Dict[str, List[Dict[str, str]]] = {
        "intel": [],
        "nvidia": [],
        "amd": [],
        "apple": [],
    }
    stamp = dt.date.today().isoformat()

    for line in lines:
        renderer = normalize_renderer(line)
        if not is_high_quality_renderer(renderer):
            continue
        bucket, vendor = infer_gpu_bucket(renderer)
        if not bucket:
            continue

        by_bucket[bucket].append(
            {
                "vendor": vendor,
                "renderer": renderer,
                "common_on": f"Observed in public fingerprints {stamp}",
            }
        )

    for bucket in by_bucket:
        unique: List[Dict[str, str]] = []
        seen_renderers = set()
        for item in by_bucket[bucket]:
            key = item["renderer"]
            if key in seen_renderers:
                continue
            seen_renderers.add(key)
            unique.append(item)
        by_bucket[bucket] = unique

    return by_bucket


def merge_candidates(
    base: Dict[str, Dict],
    candidates: Dict[str, List[Dict[str, str]]],
) -> Tuple[Dict[str, Dict], Dict[str, int]]:
    """Merge candidates into browser/os buckets with rule-based mapping."""
    merged = copy.deepcopy(base)

    stats = {
        "added_intel": 0,
        "added_nvidia": 0,
        "added_amd": 0,
        "added_apple": 0,
        "added_chrome": 0,
        "added_firefox": 0,
        "added_safari": 0,
    }

    for bucket, entries in candidates.items():
        for cand in entries:
            mapped_targets = infer_merge_targets(bucket, cand["renderer"])
            for browser, os_name, target_bucket, vendor, target_renderer in mapped_targets:
                if os_name not in merged.get(browser, {}):
                    continue

                os_node = merged[browser][os_name]
                payload = {
                    "vendor": vendor,
                    "renderer": target_renderer,
                    "common_on": cand["common_on"],
                }

                if isinstance(os_node, list):
                    existing_renderers = {item["renderer"] for item in os_node}
                    if target_renderer in existing_renderers:
                        continue
                    os_node.append(payload)
                else:
                    if not target_bucket or target_bucket not in os_node:
                        continue
                    existing = os_node[target_bucket]
                    existing_renderers = {item["renderer"] for item in existing}
                    if target_renderer in existing_renderers:
                        continue
                    existing.append(payload)

                stats[f"added_{bucket}"] += 1
                stats[f"added_{browser}"] += 1

    return merged, stats


def write_dataset_file(dataset: Dict[str, Dict], output_path: Path) -> None:
    """Write Python module with deterministic pretty formatting."""
    content = (
        '"""\n'
        "WebGL renderer dataset.\n\n"
        "This module stores raw/curated renderer entries only.\n"
        "Selection, weighting, and normalization logic lives in `webgl_database.py`.\n"
        '"""\n\n'
        "WEBGL_CONFIGS = "
        + pprint.pformat(dataset, width=120, sort_dicts=False)
        + "\n"
    )
    output_path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh WebGL dataset from public sources.")
    parser.add_argument("--apply", action="store_true", help="Apply merged candidates to tegufox_core/webgl_dataset.py")
    parser.add_argument("--source-url", action="append", default=[], help="Extra source URL (can be used multiple times)")
    parser.add_argument("--source-file", action="append", default=[], help="Local HTML/text file to parse (can be used multiple times)")
    parser.add_argument(
        "--output-candidates",
        default="",
        help="Optional path to write extracted candidate JSON for review",
    )
    args = parser.parse_args()

    sources = list(DEFAULT_SOURCES)
    if args.source_url:
        sources.extend(args.source_url)

    combined_texts: List[str] = []
    for url in sources:
        try:
            text = fetch_url(url)
            combined_texts.append(text)
            print(f"[ok] fetched: {url}")
        except Exception as exc:
            print(f"[warn] failed fetching {url}: {exc}")

    for path_str in args.source_file:
        path = Path(path_str)
        if not path.exists():
            print(f"[warn] source file missing: {path}")
            continue
        combined_texts.append(path.read_text(encoding="utf-8", errors="ignore"))
        print(f"[ok] loaded file: {path}")

    if not combined_texts:
        print("[error] no usable sources")
        return 2

    all_lines: List[str] = []
    for text in combined_texts:
        all_lines.extend(extract_renderer_lines(text))

    lines = list(dict.fromkeys(all_lines))
    candidates = build_candidates(lines)

    total_candidates = sum(len(v) for v in candidates.values())
    print(f"[info] extracted renderer candidates: {total_candidates}")
    print(
        "[info] bucket counts: "
        f"intel={len(candidates['intel'])}, "
        f"nvidia={len(candidates['nvidia'])}, "
        f"amd={len(candidates['amd'])}, "
        f"apple={len(candidates['apple'])}"
    )

    merged, stats = merge_candidates(WEBGL_CONFIGS, candidates)
    print(
        "[info] merge preview: "
        f"added_intel={stats['added_intel']}, "
        f"added_nvidia={stats['added_nvidia']}, "
        f"added_amd={stats['added_amd']}, "
        f"added_apple={stats['added_apple']}, "
        f"added_chrome={stats['added_chrome']}, "
        f"added_firefox={stats['added_firefox']}, "
        f"added_safari={stats['added_safari']}"
    )

    if args.output_candidates:
        out = Path(args.output_candidates)
        out.write_text(json.dumps(candidates, indent=2), encoding="utf-8")
        print(f"[ok] wrote candidates: {out}")

    if args.apply:
        dataset_path = REPO_ROOT / "tegufox_core" / "webgl_dataset.py"
        write_dataset_file(merged, dataset_path)
        print(f"[ok] applied merge to: {dataset_path}")
    else:
        print("[info] dry-run mode: no dataset file changed (use --apply to write)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
