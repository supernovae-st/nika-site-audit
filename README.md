# Nika Site Audit

Full website audit workflow powered by [Nika](https://github.com/supernovae-st/nika) — crawl any site, detect locales, validate hreflang, generate SEO reports.

**100% native. Zero Python. Zero jq. Zero awk. Zero external dependencies.**

## Quick Start

```bash
# 1. Install nika (macOS)
brew install supernovae-st/tap/nika

# 2. Clone this repo
git clone https://github.com/supernovae-st/nika-site-audit.git
cd nika-site-audit

# 3. Set your API key
export OPENAI_API_KEY=sk-...

# 4. Audit any site
./audit https://htmx.org

# 5. Open the dashboard
open artifacts/audit-dashboard.html
```

That's it. One command, 4 artifacts, full SEO report.

### Other install methods

```bash
# Linux (x64)
curl -fsSL https://github.com/supernovae-st/nika/releases/latest/download/nika-linux-x64-*.tar.gz | tar xz
sudo mv nika /usr/local/bin/

# Linux (ARM64)
curl -fsSL https://github.com/supernovae-st/nika/releases/latest/download/nika-linux-arm64-*.tar.gz | tar xz
sudo mv nika /usr/local/bin/

# From source
git clone https://github.com/supernovae-st/nika.git
cd nika/tools && cargo build --release -p nika
cp target/release/nika /usr/local/bin/

# Verify
nika --version    # should show v0.65.1+
nika provider list # check API key status
```

## What It Does

```
ANY URL → sitemap parsing → page crawl → enrichment → analysis → 4 artifacts
```

1. Parses `sitemap.xml` (urlset + sitemapindex with sub-sitemaps)
2. Falls back to homepage links when no sitemap exists (spider mode)
3. Crawls all pages with `response:slim` (~800 bytes/page, 10 RPS)
4. Discovers new pages via Round 2 link extraction
5. Enriches each page: locale, depth, title, canonical, hreflang, soft 404
6. Analyzes: group by locale, aggregate stats, filter broken pages
7. Validates hreflang bidirectionality (LLM-powered sample audit)
8. Generates 4 artifacts: JSON data, Mermaid diagram, Markdown report, interactive HTML dashboard

## Output

```
artifacts/
├── audit-dashboard.html  Interactive 8-tab HTML dashboard
├── crawl-report.md       SEO audit report (8 sections)
├── site-structure.md     Mermaid diagram by locale
└── sitemap.json          Full enriched page data
```

### Dashboard (8 tabs)

| Tab | Description |
|-----|-------------|
| **Treemap** | Squarified layout — page distribution by locale/section |
| **Force Graph** | 5 layouts (Force, Radial, Hierarchy, Circular, Cluster) |
| **Tree Layout** | SVG hierarchy from URL structure |
| **3D Graph** | Three.js interactive 3D force graph |
| **Report** | Rendered markdown audit report |
| **Page List** | Searchable, sortable, filterable data table |
| **Health** | Donut ring score, status bars, depth chart, AI crawler grid |
| **Status Chart** | Status code distribution visualization |

## Tested Sites

| Site | Pages | Locales | Time | Cost | Status |
|------|-------|---------|------|------|--------|
| qrcode-ai.com | 1,654 | 38 | ~4.5min | $1.21 | Sitemapindex (37 sub-sitemaps) |
| tailwindcss.com | 1,979 | 1 | ~4min | $0.14 | Sitemap (urlset) |
| htmx.org | 278 | 1 | ~1.5min | $0.12 | Sitemap (urlset) |
| astro.build | 208 | 1 | ~1min | $0.12 | Sitemap (urlset) |
| remix.run | 118 | 2 | ~1min | $0.12 | Sitemap (urlset) |
| books.toscrape.com | 640 | 1 | ~2min | $0.12 | Spider mode (no sitemap) |

All sites pass with 44/44 tasks, zero failures.

## Requirements

- [Nika](https://github.com/supernovae-st/nika) v0.65.1+
- An OpenAI API key (for 4 LLM calls: geo analysis, hreflang audit, mermaid tree, SEO report)

## Workflow Architecture

```
44 tasks · 137 edges · 22 layers — 100% native

Layer 0:  fetch_robots + fetch_llmstxt             (GEO discovery)
Layer 1:  fetch_sitemap + fetch_homepage            (parallel seeds)
Layer 2:  fetch_sub_sitemaps                        (sitemapindex expansion)
Layer 3:  URL combination                           (map + json_merge + set_diff)
Layer 4:  crawl_pages                               (for_each, concurrency 10)
Layer 5:  Round 2 link discovery                    (sample 20 pages → filter → crawl new)
Layer 6:  enriched_pages                            (nika:enrich, zero LLM)
Layer 7:  Analysis                                  (group_by, aggregate, filter — parallel)
Layer 8:  Hreflang audit + Mermaid + Dashboard data (LLM + nika:jq + nika:tree_data)
Layer 9:  build_sitemap + crawl_report              (json_merge + LLM report)
Layer 10: Dashboard HTML                            (nika:inject template)
```

## Engine Features Used (all native, zero exec)

| Tool | Purpose |
|------|---------|
| `nika:jq` | Full jq expressions (graph classification, stats, page slicing) |
| `nika:tree_data` | Nested group_by for treemap hierarchy |
| `nika:inject` | Template marker replacement (dashboard HTML) |
| `nika:enrich` | Add locale, depth, soft_404 fields to each page |
| `nika:map` + `transform` | Extract + transform per element |
| `nika:filter` | Broken pages, soft 404, domain filtering |
| `nika:group_by` | Pages by locale |
| `nika:aggregate` | Stats (count, avg, max on elapsed_ms) |
| `nika:json_merge` | Combine URL arrays + build final JSON |
| `nika:set_diff` | Find new URLs not in sitemap |
| `nika:json_query` | JSONPath extraction from nested data |
| `nika:read` / `nika:write` | File I/O for dashboard data |
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

## Verification

```bash
# Validate workflow syntax
nika check site-audit.nika.yaml

# Dry run (no API calls)
nika run site-audit.nika.yaml --dry-run

# Run with mock provider (deterministic, no API key)
nika run site-audit.nika.yaml --provider mock
```

## License

AGPL-3.0-or-later — Same as Nika.
