# Nika Site Audit

Full website audit workflow powered by [Nika](https://github.com/supernovae-st/nika) — crawl any site, detect locales, validate hreflang, generate interactive dashboards, AI images, and podcast narration.

**100% native. Zero Python. Zero jq. Zero external dependencies.**

## Quick Start (A to Z)

### 1. Install Nika

```bash
brew install supernovae-st/tap/nika
nika --version   # v0.65.1+
```

<details>
<summary>Other install methods (Linux, Intel Mac, source)</summary>

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

# From source
git clone https://github.com/supernovae-st/nika.git
cd nika/tools && cargo build --release -p nika
sudo cp target/release/nika /usr/local/bin/
```

</details>

### 2. Clone the project

```bash
git clone https://github.com/supernovae-st/nika-site-audit.git
cd nika-site-audit
```

### 3. Set your API keys

Three API keys, only the first is required:

| Key | Required | Purpose | Get it at |
|-----|----------|---------|-----------|
| `OPENAI_API_KEY` | **Yes** | LLM for report, analysis, mermaid | [platform.openai.com](https://platform.openai.com) |
| `GEMINI_API_KEY` | Optional | Nano Banana AI image generation | [ai.dev](https://ai.dev) (enable billing) |
| `ELEVENLABS_API_KEY` | Optional | Podcast audio narration (TTS) | [elevenlabs.io](https://elevenlabs.io) |

```bash
export OPENAI_API_KEY=sk-proj-...
export GEMINI_API_KEY=AIzaSy...        # optional, for AI images
export ELEVENLABS_API_KEY=sk_...       # optional, for podcast audio
```

Verify:

```bash
nika provider list
```

### 4. Run the audit

```bash
nika run site-audit.nika.yaml -i "url=https://your-site.com"
```

### 5. Open the results

```bash
open artifacts/audit-dashboard.html    # Interactive dashboard
open artifacts/crawl-report.md         # SEO audit report
open artifacts/audio/site-audit-podcast.mp3  # Podcast (if ElevenLabs key set)
```

## What It Does

```
nika run site-audit.nika.yaml -i "url=https://example.com"
```

50 tasks in 22 layers:

1. **Crawl** — parses sitemap.xml + homepage links, discovers sub-sitemaps, crawls all pages (10 RPS)
2. **Round 2** — extracts internal links from 20 sample pages, finds new URLs, crawls them
3. **Enrich** — detects locale, depth, section, title, canonical, hreflang, soft 404 for each page
4. **Analyze** — groups by locale/section, computes stats, filters broken pages, validates hreflang
5. **GEO Audit** — checks AI crawler access (GPTBot, ClaudeBot, etc.), llms.txt, citability
6. **Image Gen** — generates header banner + metrics infographic via Nano Banana (Gemini)
7. **Report** — writes 10-section, 3000+ word professional audit with locale counts and health grade
8. **Podcast** — creates 5-min narration script, generates MP3 via ElevenLabs TTS
9. **Dashboard** — builds interactive 10-tab HTML with locale filter and embedded AI images

## Output

```
artifacts/
├── audit-dashboard.html     Interactive 10-tab dashboard (with AI images)
├── crawl-report.md          Professional 10-section SEO audit report
├── site-structure.md         Mermaid diagram with locale breakdown
├── sitemap.json              Full enriched page data (JSON)
├── charts/
│   └── status-distribution.png   HTTP status bar chart
└── audio/
    └── site-audit-podcast.mp3    AI-narrated podcast (~5-9 min)
```

## Dashboard (10 interactive tabs)

| Tab | Description |
|-----|-------------|
| **Overview** | Landing view: status grid, top locales (clickable), issues index, depth chart |
| **Treemap** | Squarified layout — page distribution by locale and section |
| **Force Graph** | 5 layouts: Force, Radial, Hierarchy, Circular, Cluster |
| **Tree Layout** | SVG hierarchy from URL path structure |
| **3D Graph** | Three.js interactive 3D force-directed graph |
| **Locales** | Per-locale health score cards (clickable to filter) |
| **Report** | Rendered markdown audit report |
| **Page List** | Searchable, sortable, filterable data table |
| **Health** | Donut score, status bars, depth chart, AI crawler grid, response time |
| **Status Chart** | Status code distribution PNG |

### Locale Filter

A global locale filter bar sits above all tabs. Click any locale pill to filter **all views** simultaneously — treemap, page list, health stats, and cards all react instantly.

## Tested Sites

| Site | Pages | Locales | Time | Cost | Status |
|------|-------|---------|------|------|--------|
| qrcode-ai.com | 1,654 | 38 | ~10min | ~$2.50 | 50/50 tasks |
| htmx.org | 278 | 1 | ~3min | ~$0.30 | 50/50 tasks |
| tailwindcss.com | ~1,900 | 1 | ~5min | ~$0.50 | 50/50 tasks |

## Requirements

- [Nika](https://github.com/supernovae-st/nika) v0.65.1+
- **Required**: OpenAI API key (LLM calls: report, GEO analysis, hreflang audit, mermaid, audio script)
- **Optional**: Gemini API key with billing enabled (Nano Banana image generation)
- **Optional**: ElevenLabs API key (podcast audio narration)

## Usage

```bash
# Audit any website
nika run site-audit.nika.yaml -i "url=https://example.com"

# Use a different LLM provider
nika run site-audit.nika.yaml -i "url=https://example.com" --provider anthropic

# Validate the workflow (no execution)
nika check site-audit.nika.yaml

# Dry run (see task plan, estimate cost)
nika run site-audit.nika.yaml --dry-run
```

## Configuration

Edit `nika.toml`:

```toml
[provider]
default = "openai"
model = "gpt-5.2"
```

Or override per-run:

```bash
nika run site-audit.nika.yaml -i "url=https://example.com" --provider anthropic --model claude-sonnet-4-20250514
```

## Architecture

```
50 tasks · 179 edges · 22 layers

Layer 0:    fetch_robots + fetch_llmstxt              (GEO seeds)
Layer 1:    fetch_sitemap + fetch_homepage             (parallel crawl seeds)
Layer 2:    fetch_sub_sitemaps                          (sitemapindex expansion)
Layer 3-5:  URL merge + crawl_pages + Round 2          (for_each, concurrency 10)
Layer 6:    enriched_pages                              (nika:enrich, zero LLM)
Layer 7:    Analysis + locale_counts                    (group_by, aggregate, filter, jq)
Layer 8:    Mermaid + status chart + Nano Banana images (parallel)
Layer 9:    Report (3000+ words) + audio script         (LLM)
Layer 10:   Dashboard HTML + podcast MP3                (nika:inject + curl)
```

## License

AGPL-3.0-or-later — Same as Nika.
