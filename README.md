# Nika Site Audit

Full website audit workflow powered by [Nika](https://github.com/supernovae-st/nika) — crawl any site, detect locales, validate hreflang, generate SEO reports.

**100% native. Zero Python. Zero jq. Zero awk. Zero external dependencies.**

## Quick Start

```bash
# Install nika
brew install supernovae-st/tap/nika

# Clone and enter
git clone https://github.com/supernovae-st/nika-site-audit.git
cd nika-site-audit

# Set your API key
export OPENAI_API_KEY=sk-...

# Run the audit
nika run site-audit.nika.yaml -i "url=https://htmx.org"

# Open the results
open artifacts/audit-dashboard.html
cat artifacts/crawl-report.md
```

### Other install methods

```bash
# macOS (Apple Silicon)
curl -fsSL https://github.com/supernovae-st/nika/releases/download/v0.65.1/nika-macos-arm64-0.65.1.tar.gz | tar xz
sudo cp nika-macos-arm64-0.65.1/nika /usr/local/bin/

# macOS (Intel)
curl -fsSL https://github.com/supernovae-st/nika/releases/download/v0.65.1/nika-macos-x64-0.65.1.tar.gz | tar xz
sudo cp nika-macos-x64-0.65.1/nika /usr/local/bin/

# Linux (x64)
curl -fsSL https://github.com/supernovae-st/nika/releases/download/v0.65.1/nika-linux-x64-0.65.1.tar.gz | tar xz
sudo cp nika-linux-x64-0.65.1/nika /usr/local/bin/

# Linux (ARM64)
curl -fsSL https://github.com/supernovae-st/nika/releases/download/v0.65.1/nika-linux-arm64-0.65.1.tar.gz | tar xz
sudo cp nika-linux-arm64-0.65.1/nika /usr/local/bin/

# From source
git clone https://github.com/supernovae-st/nika.git
cd nika/tools && cargo build --release -p nika
sudo cp target/release/nika /usr/local/bin/

# Verify installation
nika --version     # v0.65.1+
nika provider list # check API key status
```

## What It Does

```
nika run site-audit.nika.yaml -i "url=https://your-site.com"
```

1. Parses `sitemap.xml` (urlset + sitemapindex with sub-sitemaps)
2. Falls back to homepage links when no sitemap exists (spider mode)
3. Crawls all pages with `response:slim` (~800 bytes/page, 10 RPS)
4. Discovers new pages via Round 2 link extraction
5. Enriches each page: locale, depth, title, canonical, hreflang, soft 404
6. Analyzes: group by locale, aggregate stats, filter broken pages
7. Validates hreflang bidirectionality (LLM-powered sample audit)
8. Generates 4 artifacts in `artifacts/`

## Output

```
artifacts/
├── audit-dashboard.html  Interactive 8-tab HTML dashboard
├── crawl-report.md       SEO audit report (8 sections)
├── site-structure.md     Mermaid diagram by locale
└── sitemap.json          Full enriched page data
```

### Dashboard (8 interactive tabs)

| Tab | Description |
|-----|-------------|
| **Treemap** | Squarified layout — page distribution by locale and section |
| **Force Graph** | 5 layouts: Force, Radial, Hierarchy, Circular, Cluster |
| **Tree Layout** | SVG hierarchy from URL path structure |
| **3D Graph** | Three.js interactive 3D force-directed graph |
| **Report** | Rendered markdown audit report |
| **Page List** | Searchable, sortable, filterable data table |
| **Health** | Donut ring score, status bars, depth chart, AI crawler grid |
| **Status Chart** | Status code distribution visualization |

## Tested Sites

| Site | Pages | Locales | Time | Cost |
|------|-------|---------|------|------|
| qrcode-ai.com | 1,654 | 38 | ~4.5min | $1.21 |
| tailwindcss.com | 1,979 | 1 | ~4min | $0.14 |
| books.toscrape.com | 640 | 1 | ~2min | $0.12 |
| htmx.org | 278 | 1 | ~1.5min | $0.12 |
| astro.build | 208 | 1 | ~1min | $0.12 |
| remix.run | 118 | 2 | ~1min | $0.12 |

All sites pass with 44/44 tasks, zero failures.

## Requirements

- [Nika](https://github.com/supernovae-st/nika) v0.65.1+
- An OpenAI API key (4 LLM calls: geo analysis, hreflang audit, mermaid tree, SEO report)

## Usage

```bash
# Audit any website
nika run site-audit.nika.yaml -i "url=https://example.com"

# Use a different provider
nika run site-audit.nika.yaml -i "url=https://example.com" --provider anthropic

# Validate the workflow (no execution)
nika check site-audit.nika.yaml

# Dry run (see task plan, estimate cost)
nika run site-audit.nika.yaml --dry-run

# Use a different model
nika run site-audit.nika.yaml -i "url=https://example.com" --model gpt-4o
```

## Configuration

Edit `nika.toml` for project-level defaults:

```toml
[provider]
default = "anthropic"
model = "claude-sonnet-4-20250514"
```

Or edit `site-audit.nika.yaml` directly:

```yaml
provider: anthropic
model: claude-sonnet-4-20250514

inputs:
  url: "https://your-default-site.com"
```

## Workflow Architecture

```
44 tasks · 137 edges · 22 layers — 100% native

Layer 0:   fetch_robots + fetch_llmstxt             (GEO discovery)
Layer 1:   fetch_sitemap + fetch_homepage            (parallel seeds)
Layer 2:   fetch_sub_sitemaps                        (sitemapindex expansion)
Layer 3-5: URL merging + crawl_pages + Round 2       (for_each, concurrency 10)
Layer 6:   enriched_pages                            (nika:enrich, zero LLM)
Layer 7:   Analysis                                  (group_by, aggregate, filter)
Layer 8-9: Reports + Dashboard data                  (LLM + nika:jq + nika:tree_data)
Layer 10:  Dashboard HTML                            (nika:inject template)
```

## Native Tools Used

| Tool | Purpose |
|------|---------|
| `nika:jq` | Full jq expressions (graph nodes, stats, page slicing) |
| `nika:tree_data` | Nested group_by for treemap hierarchy |
| `nika:inject` | Template marker replacement for dashboard |
| `nika:enrich` | Add locale, depth, soft_404 to each page |
| `nika:map` | Extract and transform per array element |
| `nika:filter` | Broken pages, soft 404, domain filtering |
| `nika:group_by` | Pages by locale |
| `nika:aggregate` | Stats: count, avg, max on elapsed_ms |
| `nika:json_merge` | Combine URL arrays and build final JSON |
| `nika:set_diff` | Find URLs not in sitemap |
| `nika:read` / `nika:write` | File I/O for dashboard data |
| `extract: sitemap` | Native XML sitemap parsing |
| `extract: metadata` | Title, canonical, OG tags, hreflang |
| `extract: links` | Internal/external link classification |

## License

AGPL-3.0-or-later — Same as Nika.
