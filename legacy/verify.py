#!/usr/bin/env python3
"""Comprehensive verification suite for sitemap-crawler-v9 artifacts."""
import json
import os
import re
import sys

def load(path):
    with open(path) as f:
        return json.load(f)

def verify(name, condition, msg):
    if not condition:
        print(f"  FAIL: {msg}")
        return False
    return True

def run_checks(artifacts_dir, site_url, expected):
    """Run all checks. Returns (passed, failed, warnings)."""
    passed = 0
    failed = 0
    warnings = []

    sitemap_path = os.path.join(artifacts_dir, "sitemap.json")
    if not os.path.exists(sitemap_path):
        print(f"FATAL: {sitemap_path} not found")
        return 0, 1, []

    d = load(sitemap_path)
    s = d["site"]
    pages = d.get("pages", [])
    by_locale = d.get("pages_by_locale", {})
    broken = d.get("broken", [])
    soft_404 = d.get("soft_404", [])
    stats = d.get("stats", {})
    hreflang = d.get("hreflang_audit", {})

    print(f"\n{'='*60}")
    print(f"VERIFYING: {site_url}")
    print(f"{'='*60}")

    # ── 1. Artifacts exist ────────────────────────────────────
    print("\n[1] Artifact existence")
    for f in ["sitemap.json", "crawl-report.md", "site-structure.md"]:
        path = os.path.join(artifacts_dir, f)
        if verify(f, os.path.exists(path), f"missing {f}"):
            size = os.path.getsize(path)
            print(f"  OK: {f} ({size:,} bytes)")
            passed += 1
        else:
            failed += 1

    # ── 2. Page count ─────────────────────────────────────────
    print("\n[2] Page count")
    min_p, max_p = expected["pages_range"]
    total = s["total_pages"]
    if verify("count", min_p <= total <= max_p, f"total_pages={total} not in [{min_p},{max_p}]"):
        print(f"  OK: {total} pages (expected {min_p}-{max_p})")
        passed += 1
    else:
        failed += 1

    # ── 3. Zero null entries ──────────────────────────────────
    print("\n[3] Null entries in pages")
    nulls = sum(1 for p in pages if p is None)
    if verify("nulls", nulls == 0, f"{nulls} null entries in pages array"):
        print(f"  OK: 0 null entries")
        passed += 1
    else:
        failed += 1

    # ── 4. All pages same-domain ──────────────────────────────
    print("\n[4] Domain integrity")
    # Normalize: site_url might not have trailing slash
    base = site_url.rstrip("/")
    off_domain = [p["url"] for p in pages if p and not p["url"].startswith(base + "/") and p["url"] != base]
    if verify("domain", len(off_domain) == 0, f"{len(off_domain)} off-domain pages"):
        print(f"  OK: all {total} pages are on {base}")
        passed += 1
    else:
        for u in off_domain[:5]:
            print(f"    -> {u[:80]}")
        failed += 1

    # ── 5. Locale validation ──────────────────────────────────
    print("\n[5] Locale accuracy")
    iso_re = re.compile(r'^[a-z]{2,3}(-[a-z]{2,4})?$')
    real_locales = sorted([l for l in by_locale if iso_re.match(l)])
    non_locales = [l for l in by_locale if not iso_re.match(l) and l != "default"]

    exp_locales = expected.get("locales_range", (0, 100))
    if verify("locale_count", exp_locales[0] <= len(real_locales) <= exp_locales[1],
              f"{len(real_locales)} real locales not in [{exp_locales[0]},{exp_locales[1]}]"):
        print(f"  OK: {len(real_locales)} real locales")
        passed += 1
    else:
        failed += 1

    if non_locales:
        # Known false positives: "cdn-cgi", "null", "seo-man", etc.
        warnings.append(f"Non-ISO locale keys: {non_locales}")
        print(f"  WARN: non-ISO locales: {non_locales}")

    # ── 6. Enriched fields present ────────────────────────────
    print("\n[6] Enriched fields")
    required = ["url", "status", "locale", "locale_raw", "depth", "title",
                "description", "canonical", "hreflang_count", "is_soft_404"]
    p = pages[0] if pages else {}
    missing = [f for f in required if f not in p]
    if verify("fields", len(missing) == 0, f"missing fields: {missing}"):
        print(f"  OK: all {len(required)} enriched fields present")
        passed += 1
    else:
        failed += 1

    # ── 7. Stats coherence ────────────────────────────────────
    print("\n[7] Stats coherence")
    if verify("stats_count", stats.get("count") == total,
              f"stats.count={stats.get('count')} != total_pages={total}"):
        print(f"  OK: stats.count={total}, avg={stats.get('avg',0):.0f}ms, max={stats.get('max')}ms")
        passed += 1
    else:
        failed += 1

    # ── 8. Hreflang audit ─────────────────────────────────────
    print("\n[8] Hreflang audit")
    if verify("hreflang", "total_checked" in hreflang, "hreflang_audit missing"):
        checked = hreflang["total_checked"]
        issues = len(hreflang.get("issues", []))
        hp_count = s.get("hreflang_page_count", 0)
        print(f"  OK: {checked} checked (sample), {hp_count} total with hreflang, {issues} issues")
        passed += 1
    else:
        failed += 1

    # ── 9. Broken pages are real 4xx/5xx ──────────────────────
    print("\n[9] Broken pages")
    bad_broken = [b for b in broken if b.get("status", 0) < 400]
    if verify("broken", len(bad_broken) == 0,
              f"{len(bad_broken)} 'broken' pages with status < 400"):
        print(f"  OK: {len(broken)} broken pages, all status >= 400")
        passed += 1
    else:
        for b in bad_broken[:3]:
            print(f"    [{b.get('status')}] {b.get('url','?')[:60]}")
        failed += 1

    # ── 10. Locale breakdown sums to total ────────────────────
    print("\n[10] Locale breakdown consistency")
    locale_sum = sum(len(pg) for pg in by_locale.values())
    if verify("breakdown", locale_sum == total,
              f"sum of locale pages ({locale_sum}) != total ({total})"):
        print(f"  OK: locale breakdown sums to {total}")
        passed += 1
    else:
        failed += 1

    # ── Summary ───────────────────────────────────────────────
    print(f"\n{'='*60}")
    status = "PASS" if failed == 0 else "FAIL"
    print(f"  {status}: {passed} passed, {failed} failed, {len(warnings)} warnings")
    if warnings:
        for w in warnings:
            print(f"  WARN: {w}")
    print(f"{'='*60}\n")

    return passed, failed, warnings


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: verify.py <artifacts_dir> [site_url]")
        sys.exit(1)

    artifacts_dir = sys.argv[1]
    site_url = sys.argv[2] if len(sys.argv) > 2 else "https://htmx.org"

    # Default expectations by site
    expectations = {
        "https://htmx.org": {
            "pages_range": (200, 400),
            "locales_range": (0, 5),
        },
        "https://qrcode-ai.com": {
            "pages_range": (1500, 2000),
            "locales_range": (30, 45),
        },
        "https://kubernetes.io": {
            "pages_range": (5500, 7000),
            "locales_range": (12, 20),
        },
    }

    expected = expectations.get(site_url, {"pages_range": (1, 100000), "locales_range": (0, 100)})
    passed, failed, warnings = run_checks(artifacts_dir, site_url, expected)
    sys.exit(1 if failed > 0 else 0)
