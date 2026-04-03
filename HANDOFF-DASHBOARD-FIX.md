# HANDOFF — Fix Dashboard Treemap + Force Graph

> Priority: HIGH — Dashboard cards work (correct data), treemap + graph are empty
> Root cause: LLM generates inconsistent GRAPH data (dangling node refs)
> Solution: Compute TREE + GRAPH natively, no LLM for data

---

## Current State

The dashboard template (`templates/dashboard.html`) is PROVEN — prototype with hardcoded
data shows perfect treemap + interactive force graph with drag/zoom/tooltip.

The problem: the LLM generates `var TREE` and `var GRAPH` JS objects, but:
1. GRAPH links reference node IDs that don't exist in nodes array
2. Template filters these out → empty graph
3. TREE values are sometimes wrong (LLM miscounts from arrays)
4. Treemap cells exist but are too dark/small to see

## Root Cause

The LLM cannot reliably generate a self-consistent graph where every `links[i][0]`
and `links[i][1]` exists in `nodes[].id`. It invents URLs or uses different formats
(trailing slash vs no slash, full URL vs path).

## Solution: Native Data Computation

### TREE — Already solvable with current tools

We have `pages_by_locale` (group_by locale) and each page has `section` field.
Build TREE natively:

```yaml
# Option A: Use nika:enrich to build per-locale section counts
# Then format as JS with a simple exec: awk/jq

# Option B: Use an infer with STRUCTURED OUTPUT (not free text)
# Force the LLM to output valid JSON via schema enforcement
- id: dashboard_data
  infer:
    prompt: "Format this data as dashboard JSON: ..."
  structured:
    schema:
      type: object
      required: [tree, graph]
      properties:
        tree:
          type: object
          required: [name, total_pages, health_score, children]
          ...
        graph:
          type: object
          required: [nodes, links]
          ...
```

### GRAPH — Needs real link data

The graph should use REAL internal links, not LLM-invented ones.
We already have `sample_links` from Round 2 (20 pages → extract:links).
The `internal_link_objects` task filters to same-domain links.

```yaml
# Use actual crawl link data for graph edges
- id: graph_edges
  depends_on: [internal_link_objects]
  with: { links: $internal_link_objects }
  invoke:
    tool: "nika:map"
    params:
      array: "{{with.links | first(60)}}"
      selector: "url"
      transform: "| url_path"
```

Then build the JS natively:

```yaml
- id: build_dashboard_js
  depends_on: [pages_by_locale, pages_by_section, graph_edges]
  exec:
    command: |
      awk 'BEGIN { ... build TREE from section data ... print GRAPH from link edges ... }'
    shell: true
```

### Alternative: Structured Output Enforcement

If keeping the LLM approach, use `structured:` with a strict JSON schema.
The 5-layer defense system will validate that:
- Every node has id + g
- Every link references existing node IDs
- All values > 0
- Values sum correctly

```yaml
- id: dashboard_data
  infer:
    prompt: "..."
  structured:
    schema:
      type: object
      required: [tree, graph]
      properties:
        tree: { ... }
        graph:
          type: object
          required: [nodes, links]
          properties:
            nodes:
              type: array
              items:
                type: object
                required: [id, g]
                properties:
                  id: { type: string }
                  g: { type: string }
            links:
              type: array
              items:
                type: array
                items: { type: string }
                minItems: 2
                maxItems: 2
    enable_repair: true
    max_retries: 3
```

BUT: schema can enforce structure, not semantic consistency (link refs → node IDs).

## Recommended Approach

1. **TREE**: Use `structured:` output with the locale + section counts passed as
   exact data. The LLM just formats, doesn't compute. Schema enforces structure.

2. **GRAPH**: Compute entirely natively from Round 2 link data:
   - `internal_link_objects` already has `{url, anchor}` pairs
   - Map to `{id: url_path, g: locale}` for nodes
   - Map to `[from_path, to_path]` for links
   - Guaranteed consistency — real data, no invention

3. **Template injection**: Keep awk approach (no python dependency)

## Files to Modify

- `site-audit.nika.yaml` — restructure dashboard_data + html_dashboard tasks
- `templates/dashboard.html` — maybe increase treemap brightness more (line 177)

## Key Context

- Template file: `templates/dashboard.html` (290 lines, proven JS)
- Prototype with working data: `prototypes/03-combined-dashboard.html`
- The template expects: `var TREE = {...};` and `var GRAPH = {...};` between markers
- awk injection works: tested and committed
- Round 2 sample_links already extracts internal links from 20 pages
- `internal_link_objects` has filtered same-domain link objects

## Test Command

```bash
cd ~/Desktop
git clone https://github.com/supernovae-st/nika-site-audit.git test-fix
cd test-fix
nika run site-audit.nika.yaml -i url=https://qrcode-ai.com
open artifacts/audit-dashboard.html
# Treemap should show colored blocks per locale
# Force graph should show connected nodes with drag + zoom
```

## What WORKS Already

- Cards: 1,654 pages, 38 locales, 98% health ✓
- Legend: all locales with correct counts ✓
- Crawl: 1,654 pages crawled, 37 real locales ✓
- Report: 14KB markdown with GEO analysis ✓
- Chart: status-distribution.png (21KB) ✓
- sitemap.json: full enriched data ✓
- Template JS: treemap + force graph code proven with example data ✓
