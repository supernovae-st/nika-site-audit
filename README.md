# Nika Site Audit

Full website audit workflow powered by [Nika](https://github.com/supernovae-st/nika) — crawl any site, detect locales, validate hreflang, generate SEO reports. Zero Python, zero external scripts.

## What It Does

```
ANY URL → sitemap parsing → page crawl → enrichment → analysis → 4 artifacts
```

- Parses `sitemap.xml` (urlset + sitemapindex with sub-sitemaps)
- Falls back to homepage links when no sitemap exists (spider mode)
- Crawls all pages with `response:slim` (~800 bytes/page, 10 RPS)
- Discovers new pages via Round 2 link extraction
- Enriches each page: locale, depth, title, canonical, hreflang, soft 404
- Analyzes: group by locale, aggregate stats, filter broken pages
- Validates hreflang bidirectionality (LLM-powered sample audit)
- Generates 4 artifacts: JSON data, Mermaid diagram, Markdown report, HTML dashboard

## Requirements

- [Nika](https://github.com/supernovae-st/nika) v0.64.0+
- An OpenAI API key (for 3 LLM calls: hreflang audit + mermaid tree + SEO report)

## Quick Start

```bash
# Install nika
brew install supernovae-st/tap/nika
# or: cargo install nika

# Clone this repo
git clone https://github.com/supernovae-st/nika-site-audit.git
cd nika-site-audit

# Set your API key
export OPENAI_API_KEY=sk-...

# Run on any site
nika run site-audit.nika.yaml

# Run on a specific site
nika run site-audit.nika.yaml -i url=https://kubernetes.io

# Check output
ls artifacts/
# sitemap.json          — Full enriched page data
# site-structure.md     — Mermaid diagram by locale
# crawl-report.md       — SEO audit report (8 sections)
# audit-dashboard.html  — Interactive HTML dashboard
```

## Tested Sites

| Site | Pages | Locales | Time | Status |
|------|-------|---------|------|--------|
| htmx.org | 278 | 1 | ~2min | Sitemap (urlset) |
| qrcode-ai.com | 1,654 | 37 | ~5min | Sitemapindex (36 subs) |
| kubernetes.io | 6,138 | 15 | ~12min | Sitemapindex (16 locales) |
| books.toscrape.com | 640 | 1 | ~3min | Spider mode (no sitemap) |

All 4 sites pass 52/52 automated verification checks.

## Verification

```bash
# Run the automated test suite against your results
python3 tests/verify.py artifacts/ https://htmx.org
```

The test suite checks 12 properties:
1. Artifact existence (sitemap.json, crawl-report.md, site-structure.md)
2. Page count within expected range
3. Zero null entries in pages array
4. All pages on same domain (no off-domain crawl)
5. Locale validation (ISO codes only via regex)
6. Enriched fields present (url, status, locale, depth, title, is_soft_404)
7. Stats coherence (count matches total)
8. Hreflang audit ran (if applicable)
9. Broken pages are real 4xx/5xx
10. Locale breakdown sums to total

## Workflow Architecture

```
33 tasks · 19 layers · 100 edges

Layer 1:  fetch_sitemap + fetch_homepage          (parallel seeds)
Layer 2:  fetch_sub_sitemaps                      (sitemapindex expansion)
Layer 3:  URL combination                         (map + json_merge + set_diff)
Layer 4:  crawl_pages                             (for_each, concurrency 10)
Layer 5:  Round 2 link discovery                  (sample 20 pages → filter → crawl new)
Layer 6:  enriched_pages                          (nika:enrich, zero LLM)
Layer 7:  Analysis                                (group_by, aggregate, filter — parallel)
Layer 8:  Hreflang audit + Mermaid + Dashboard    (LLM + template injection)
Layer 9:  build_sitemap + crawl_report            (json_merge + LLM report)
```

**Zero Python. Zero jq. Zero external scripts.**
3 LLM calls for analysis/reports. All data processing via native Nika tools.

## Engine Features Used

| Tool | Purpose |
|------|---------|
| `nika:enrich` | Add locale, depth, soft_404 fields to each page |
| `nika:map` + `transform` | Extract + transform per element |
| `nika:filter` | Broken pages, soft 404, domain filtering |
| `nika:group_by` | Pages by locale |
| `nika:aggregate` | Stats (count, avg, max on elapsed_ms) |
| `nika:json_merge` | Combine URL arrays + build final JSON |
| `nika:set_diff` | Find new URLs not in sitemap |
| `nika:json_query` | JSONPath extraction from nested data |
| `extract: sitemap` | Native XML sitemap parsing + hreflang |
| `extract: metadata` | Title, description, canonical, OG, hreflang |
| `extract: links` | Internal/external link classification |
| `response: slim` | ~800 bytes/page instead of 400KB |

## Configuration

Edit `site-audit.nika.yaml` to customize:

```yaml
# Change default provider/model
provider: anthropic
model: claude-sonnet-4-20250514

# Change crawl concurrency (max 10, governor rate-limited)
concurrency: 5

# Change default target
inputs:
  url: "https://your-site.com"
```

## License

AGPL-3.0-or-later — Same as Nika.
