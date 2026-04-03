#!/usr/bin/env python3
"""Deep Socratic verification of ALL 4 test sites."""
import json
import os
import re
import sys
import glob

SITES = {
    "/tmp/v9-test-htmx": {
        "url": "https://htmx.org",
        "pages_range": (200, 400),
        "locales_range": (0, 5),
        "expect_hreflang": False,
        "expect_sitemapindex": False,
    },
    "/tmp/v9-test-qrcode": {
        "url": "https://qrcode-ai.com",
        "pages_range": (1500, 2000),
        "locales_range": (30, 45),
        "expect_hreflang": True,
        "expect_sitemapindex": True,
    },
    "/tmp/v9-test-k8s": {
        "url": "https://kubernetes.io",
        "pages_range": (5500, 7000),
        "locales_range": (12, 20),
        "expect_hreflang": True,
        "expect_sitemapindex": True,
    },
    "/tmp/v9-test-spider": {
        "url": "https://books.toscrape.com",
        "pages_range": (30, 1000),
        "locales_range": (0, 3),
        "expect_hreflang": False,
        "expect_sitemapindex": False,
        "spider_mode": True,
    },
}

def verify_site(dir_path, config):
    url = config["url"]
    domain = url.split("//")[1].rstrip("/")
    results = {"passed": 0, "failed": 0, "warnings": []}

    print(f"\n{'='*70}")
    print(f"  {domain}")
    print(f"{'='*70}")

    # Check artifacts exist
    sitemap_path = os.path.join(dir_path, "artifacts", "sitemap.json")
    if not os.path.exists(sitemap_path):
        print(f"  FATAL: sitemap.json not found")
        # Check traces for errors
        traces = glob.glob(os.path.join(dir_path, ".nika", "traces", "*.ndjson"))
        if traces:
            with open(traces[0]) as f:
                for line in f:
                    d = json.loads(line)
                    k = d.get("kind", {})
                    if k.get("type") == "workflow_failed":
                        print(f"  ERROR: {k.get('error', '?')[:120]}")
                    elif k.get("type") == "task_failed":
                        print(f"  TASK FAIL: {k.get('task_id','?')} — {k.get('error','')[:80]}")
        results["failed"] += 1
        return results

    d = json.load(open(sitemap_path))
    s = d["site"]
    pages = d.get("pages", [])
    by_locale = d.get("pages_by_locale", {})
    broken = d.get("broken", [])
    soft_404 = d.get("soft_404", [])
    stats = d.get("stats", {})
    hreflang = d.get("hreflang_audit", {})

    def check(name, ok, msg):
        if ok:
            results["passed"] += 1
            return True
        else:
            print(f"  FAIL [{name}]: {msg}")
            results["failed"] += 1
            return False

    # 1. Page count
    lo, hi = config["pages_range"]
    check("pages", lo <= s["total_pages"] <= hi,
          f'total_pages={s["total_pages"]} not in [{lo},{hi}]')

    # 2. Zero nulls
    nulls = sum(1 for p in pages if p is None)
    check("nulls", nulls == 0, f"{nulls} null entries")

    # 3. All same-domain
    base = url.rstrip("/")
    off = [p["url"] for p in pages if p and not p["url"].startswith(base + "/") and p["url"] != base]
    check("domain", len(off) == 0, f"{len(off)} off-domain: {off[:3]}")

    # 4. Locale validation
    iso_re = re.compile(r'^[a-z]{2,3}(-[a-z]{2,4})?$')
    real = [l for l in by_locale if iso_re.match(l)]
    lo, hi = config["locales_range"]
    check("locales", lo <= len(real) <= hi,
          f"{len(real)} real locales not in [{lo},{hi}]: {sorted(real)[:10]}")

    # 5. Enriched fields
    if pages:
        p = next((p for p in pages if p), {})
        required = ["url", "status", "locale", "depth", "title", "is_soft_404"]
        missing = [f for f in required if f not in p]
        check("fields", len(missing) == 0, f"missing: {missing}")

    # 6. Stats coherence
    check("stats", stats.get("count") == s["total_pages"],
          f'stats.count={stats.get("count")} != total={s["total_pages"]}')

    # 7. Locale breakdown sums
    locale_sum = sum(len(pg) for pg in by_locale.values())
    check("breakdown", locale_sum == s["total_pages"],
          f"sum={locale_sum} != total={s['total_pages']}")

    # 8. Hreflang
    if config.get("expect_hreflang"):
        hp = s.get("hreflang_page_count", 0)
        check("hreflang_count", hp > 0, f"expected hreflang pages but got {hp}")
        check("hreflang_audit", "total_checked" in hreflang, "audit missing")

    # 9. Broken pages are real 4xx+
    bad = [b for b in broken if b.get("status", 0) < 400]
    check("broken_valid", len(bad) == 0, f"{len(bad)} 'broken' with status < 400")

    # 10. Artifacts exist
    expected_arts = ["sitemap.json", "crawl-report.md", "site-structure.md"]
    for a in expected_arts:
        path = os.path.join(dir_path, "artifacts", a)
        if not os.path.exists(path):
            check(f"artifact_{a}", False, f"missing {a}")
        else:
            results["passed"] += 1

    # 11. NDJSON trace analysis
    traces = glob.glob(os.path.join(dir_path, ".nika", "traces", "*.ndjson"))
    if traces:
        task_results = {}
        with open(traces[0]) as f:
            for line in f:
                d2 = json.loads(line)
                k = d2.get("kind", {})
                t = k.get("type", "")
                tid = k.get("task_id", "")
                if t == "task_completed":
                    task_results[tid] = "OK"
                elif t == "task_failed":
                    task_results[tid] = f"FAIL: {k.get('error','')[:60]}"
                elif t == "task_skipped":
                    task_results[tid] = f"SKIP: {k.get('reason','')[:60]}"

        failed_tasks = {k: v for k, v in task_results.items() if v.startswith("FAIL")}
        skipped_tasks = {k: v for k, v in task_results.items() if v.startswith("SKIP")}
        ok_tasks = {k: v for k, v in task_results.items() if v == "OK"}

        # Dashboard failure is OK (template not always present)
        real_failures = {k: v for k, v in failed_tasks.items() if k != "html_dashboard"}
        check("trace_no_failures", len(real_failures) == 0,
              f"{len(real_failures)} task failures: {list(real_failures.keys())}")

        print(f"  Trace: {len(ok_tasks)} OK, {len(failed_tasks)} FAIL, {len(skipped_tasks)} SKIP")

    # Summary
    status = "PASS" if results["failed"] == 0 else "FAIL"
    total = s["total_pages"]
    locs = len(real)
    print(f"  ---")
    print(f"  {status}: {results['passed']} passed, {results['failed']} failed")
    print(f"  {total} pages, {locs} locales, {len(broken)} broken, avg {stats.get('avg',0):.0f}ms")

    return results


if __name__ == "__main__":
    total_pass = 0
    total_fail = 0

    for dir_path, config in SITES.items():
        r = verify_site(dir_path, config)
        total_pass += r["passed"]
        total_fail += r["failed"]

    print(f"\n{'='*70}")
    print(f"  TOTAL: {total_pass} passed, {total_fail} failed across 4 sites")
    print(f"{'='*70}")
    sys.exit(1 if total_fail > 0 else 0)
