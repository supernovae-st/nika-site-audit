# Plan: 100% Native Dashboard + Interactive Graph

> Date: 2026-04-04
> Status: READY TO EXECUTE
> Repos: nika (engine), nika-site-audit (workflow)
> Prereq: feat(core) jq stdlib commit 2d1d9400d (already pushed)

---

## Part 1: Engine — `nika:jq` Builtin Tool

### Why
The `| jq()` transform works for simple expressions but FAILS for complex ones
(500+ chars with nested parens break the template parser). We need a TOOL form
that receives data + expression as params — no template escaping issues.

### Spec

```yaml
- id: example
  invoke:
    tool: "nika:jq"
    params:
      data: "{{with.pages}}"
      expr: |
        [group_by(.locale)[] | {
          name: .[0].locale,
          children: [group_by(.section)[] | {
            name: ("/" + .[0].section),
            value: length
          }] | sort_by(-.value)
        }] | sort_by(-(.children | map(.value) | add))
```

### Implementation

**File**: `tools/nika-engine/src/runtime/builtin/data_tools.rs`

Add a new tool `nika:jq` alongside existing data tools:

```rust
// In the tool registry (dispatch)
"nika:jq" => {
    let data = params.get("data")?;         // serde_json::Value
    let expr = params.get_str("expr")?;     // &str
    let result = crate::binding::transform::eval_jq(expr, data)?;
    Ok(result)
}
```

**File**: `tools/nika-core/src/binding/transform.rs`

Extract `compile_jq` into a public function:

```rust
/// Evaluate a jq expression on a JSON value (public API for nika:jq tool)
pub fn eval_jq(expr: &str, data: &serde_json::Value) -> Result<serde_json::Value, String> {
    let filter = compile_jq(expr)?;
    use jaq_interpret::FilterT as _;
    let inputs = jaq_interpret::RcIter::new(core::iter::empty());
    let jaq_val = jaq_interpret::Val::from(data.clone());
    let mut results: Vec<serde_json::Value> = Vec::new();
    for r in filter.run((jaq_interpret::Ctx::new([], &inputs), jaq_val)) {
        match r {
            Ok(val) => results.push(serde_json::Value::from(val)),
            Err(e) => return Err(format!("jq runtime error: {e}")),
        }
    }
    match results.len() {
        0 => Ok(serde_json::Value::Null),
        1 => Ok(results.into_iter().next().unwrap()),
        _ => Ok(serde_json::Value::Array(results)),
    }
}
```

### Tests (3 minimum)

1. `tool_jq_group_by` — basic group_by with count
2. `tool_jq_nested_tree` — the exact TREE pattern (nested group_by)
3. `tool_jq_graph_classification` — regex test for path classification

### Task count: 1 file modified (data_tools.rs), 1 function exposed (transform.rs), ~40 lines

---

## Part 2: Engine — `nika:tree_data` Builtin Tool

### Why
Nested group_by + count is the #1 pattern for treemap data. A dedicated tool is
cleaner than jq for this specific use case.

### Spec

```yaml
- id: tree
  invoke:
    tool: "nika:tree_data"
    params:
      array: "{{with.pages}}"
      group_by: "locale"
      sub_group_by: "section"
      name_prefix: "/"
      sort: "desc"
```

Returns:
```json
[
  {"name": "en", "children": [{"name": "/blog", "value": 156}, {"name": "/docs", "value": 230}]},
  {"name": "fr", "children": [{"name": "/tarifs", "value": 15}]}
]
```

### Implementation

**File**: `tools/nika-engine/src/runtime/builtin/data_tools.rs` (~50 lines)

Logic: group array by primary field, then for each group sub-group by secondary field
and count items. Sort children by value descending. Sort groups by total descending.

### Task count: ~50 lines in data_tools.rs + 3 tests

---

## Part 3: Workflow — 100% Native (no exec jq/awk)

### Current (exec jq + awk)
```
write_pages_json -> build_tree (exec jq) -> build_graph (exec jq) -> write_dashboard_js -> html_dashboard (exec awk)
```

### Target (100% native)
```
build_tree (nika:tree_data) -> build_graph (nika:jq) -> write_dashboard (nika:write)
```

### Tasks (YAML ready to copy)

```yaml
# TREE: native nested group_by
- id: build_tree
  depends_on: [enriched_pages, broken_pages, soft_404_pages]
  with: { pages: $enriched_pages }
  invoke:
    tool: "nika:tree_data"
    params:
      array: "{{with.pages}}"
      group_by: "locale"
      sub_group_by: "section"
      name_prefix: "/"
      sort: "desc"

# Wrap tree with metadata
- id: tree_with_meta
  depends_on: [build_tree, enriched_pages, broken_pages, soft_404_pages]
  with:
    children: $build_tree
    pages: $enriched_pages
    broken: $broken_pages
    soft_404: $soft_404_pages
  invoke:
    tool: "nika:json_merge"
    params:
      items:
        - name: "{{inputs.url | url_host}}"
          total_pages: "{{with.pages | length}}"
          broken_count: "{{with.broken | length}}"
          soft_404_count: "{{with.soft_404 | length}}"
          children: "{{with.children}}"
      mode: "deep_merge"

# GRAPH: extract paths natively
- id: graph_paths
  depends_on: [enriched_pages]
  with: { pages: $enriched_pages }
  invoke:
    tool: "nika:map"
    params:
      array: "{{with.pages | first(80)}}"
      selector: "url"
      transform: "| url_path | default('/')"

# GRAPH: classify + build edges via nika:jq
- id: build_graph
  depends_on: [graph_paths]
  with: { paths: $graph_paths }
  invoke:
    tool: "nika:jq"
    params:
      data: "{{with.paths | unique}}"
      expr: |
        . as $p | {
          nodes: [.[] | {
            id: (if . == "/" then "/" else rtrimstr("/") end),
            g: (
              if . == "/" then "root"
              elif test("^/(docs?|api|reference|guides?|learn|tutorials?|examples?|faq|handbook|getting-started|changelog|attributes?|specs?|schemas?)(/|$)") then "doc"
              elif test("^/(blog|news|articles?|posts?|essays|stories|interviews|updates|press|newsletter|talks?)(/|$)") then "cnt"
              elif test("^/(about|contact|careers|legal|terms|privacy|team|company|imprint|jobs|lore|webring)(/|$)") then "co"
              elif test("^/(pricing|features|solutions|enterprise|plans|tarifs|preise)(/|$)") then "mkt"
              elif test("^/(app|dashboard|console|product|tools|extensions|plugins|integrations|packages?)(/|$)") then "prod"
              elif test("^/(login|sign-?up|register|auth|account|profile|settings|sso)(/|$)") then "auth"
              else "cnt"
              end
            )
          }],
          links: [.[] | select(. != "/") | rtrimstr("/") | . as $c |
            ($c | split("/") | .[:-1] | join("/") | if . == "" then "/" else . end) as $par |
            select([$p[] | if . == "/" then "/" else rtrimstr("/") end | select(. == $par)] | length > 0) |
            [$par, $c]
          ]
        }

# Write JS + inject into HTML (nika:write replaces awk)
- id: write_dashboard_js
  depends_on: [tree_with_meta, build_graph]
  with:
    tree: $tree_with_meta
    graph: $build_graph
  invoke:
    tool: "nika:write"
    params:
      file_path: "artifacts/tmp/dashboard-data.js"
      content: "var TREE = {{with.tree | to_json}};\nvar GRAPH = {{with.graph | to_json}};"
      overwrite: true

# NOTE: Still needs awk or nika:edit to inject into HTML template.
# Options for removing awk:
# A. nika:edit with string replacement (if tool supports regex replace)
# B. Template the HTML to use Nika {{...}} syntax directly
# C. Keep exec: awk (1 remaining exec, standard Unix tool)
```

---

## Part 4: Dashboard — Interactive Multi-Layout Graph

### 5 Layout Modes

| # | Layout | Algorithm | Best For |
|---|--------|-----------|----------|
| 1 | **Force** | Spring + repulsion physics | General structure, clusters |
| 2 | **Radial** | Root center, layers by depth | Hierarchy depth visualization |
| 3 | **Hierarchical** | Top-down tree (BFS layers) | Parent-child relationships |
| 4 | **Circular** | Nodes on circle, grouped | Group distribution overview |
| 5 | **Cluster** | Separate force per group | Group isolation, comparison |

### UI: Layout Switcher

Sub-toolbar within Force Graph tab:
```
[Force] [Radial] [Hierarchy] [Circular] [Cluster]
```

Small buttons below the main tabs, styled like pills.

### Layout Algorithm Specs

**Radial**: BFS from root assigns depth. Nodes at same depth placed on concentric
ring. Ring radius = depth * 100 + 30. Angle = index / count * 2*PI.

**Hierarchical**: BFS layers. Within each layer, barycenter ordering to minimize
crossings. x = layer * horizontalSpacing, y = position * verticalSpacing.

**Circular**: Group nodes into buckets by `g` field. Place group centroids evenly
on a circle (radius 180). Within each group, place nodes in a smaller circle
around the centroid.

**Cluster**: Run independent force simulations per group (100 iterations offline),
then arrange group bounding boxes in a grid.

### Transition Animation

When switching layouts, animate from current positions to target positions using
easeOutCubic over 60 frames (~1s). Disable physics during transition, re-enable
for force layout.

### Node Click: Info Panel

Slide-in panel on the right (300px) showing:
- Path (as clickable link if it's a real URL)
- Group classification + color dot
- Connection count
- List of connected nodes (clickable to select)
- Parent node (if edge exists)
- Children nodes (if edges exist)

Close on click outside or Escape key.

### Edge Interaction

- Hover: thicken edge + show tooltip with source/target
- Click: show edge detail in info panel
- Double-click node: zoom to node, highlight 1-hop neighborhood

### Node highlighting

- Hover: dim unconnected, highlight connected (already implemented)
- Click (select): persist highlight until click elsewhere
- Selected node: white ring, bold label, connected edges bright

---

## Execution Order

### Sprint 1: Engine (nika repo) ~1h
1. Make `eval_jq()` public in transform.rs
2. Register `nika:jq` tool in data_tools.rs
3. Register `nika:tree_data` tool in data_tools.rs
4. Write 6 tests
5. `cargo test --package nika-core --lib && cargo test --package nika-engine --lib`
6. Commit + push

### Sprint 2: Workflow native (nika-site-audit) ~30min
7. Replace exec tasks with nika:tree_data + nika:jq
8. `nika check && nika run -i url=https://htmx.org`
9. Verify dashboard output matches previous (same TREE/GRAPH data)
10. Commit + push

### Sprint 3: Dashboard interactivity (nika-site-audit) ~2h
11. Add layout switcher (5 layouts) to Force Graph tab
12. Implement radial, hierarchical, circular, cluster algorithms
13. Add transition animation between layouts
14. Add info panel (slide-in right)
15. Add node click -> info panel
16. Add edge hover + click
17. Add selected node persistence
18. Test with htmx.org + qrcode-ai.com
19. Commit + push

### Sprint 4: Cleanup + verify ~30min
20. Remove HANDOFF-DASHBOARD-FIX.md
21. Run full test suite
22. Run site-audit on 2 sites, verify all views
23. Final push

---

## Verification Checklist

- [ ] `nika:jq` tool works with nested group_by expression
- [ ] `nika:tree_data` produces exact locale/section counts
- [ ] `nika check site-audit.nika.yaml` passes with zero exec in dashboard pipeline
- [ ] Treemap shows colored sections with correct counts
- [ ] Force graph has 5 selectable layouts
- [ ] Radial layout shows depth rings from root
- [ ] Clicking node opens info panel with connections
- [ ] Hovering edge shows tooltip with source/target
- [ ] Transition between layouts is animated (easeOutCubic)
- [ ] Works on htmx.org (single locale, 278 pages)
- [ ] Works on qrcode-ai.com (37 locales, 1654 pages)
- [ ] No external tool dependencies (no jq, no awk)
- [ ] DOM uses safe methods (textContent, createElement) — no innerHTML with untrusted data

---

## Part 5: Dashboard — Embedded Report + Artifacts

### Why
The dashboard should be a SINGLE self-contained file showing ALL audit results.
Currently you need to open 5 separate files. Everything should be in one place.

### New Tabs

| Tab | Data Source | Rendering |
|-----|-----------|-----------|
| **Report** | `var REPORT = "...markdown..."` | Minimal markdown-to-HTML (headings, bold, tables, lists, code blocks) |
| **Status Chart** | `var CHART = "data:image/png;base64,..."` | Centered `<img>` element |
| **Page List** | `var PAGES = [...]` | Searchable, sortable table (URL, status, locale, depth, title) |
| **Health** | Computed from TREE data | SVG donut ring (health score), status bar, depth heatmap, AI crawler grid |

### Data Variables (add to dashboard-data.js)

```javascript
var TREE = {...};           // existing
var GRAPH = {...};          // existing
var REPORT = "# Report..."; // NEW: raw markdown string
var CHART = "data:...";     // NEW: base64 PNG
var PAGES = [...];          // NEW: slim page array (url, status, title, locale, section, depth)
var STATS = {...};          // NEW: {status: {ok,redirect,error}, depth: {0:N,1:N,...}, geo: {...}}
```

### Workflow Changes for Extra Data

```yaml
# Prepare slim page list (drop heavy extracted sub-objects)
- id: slim_pages
  depends_on: [enriched_pages]
  with: { pages: $enriched_pages }
  invoke:
    tool: "nika:jq"
    params:
      data: "{{with.pages}}"
      expr: "[.[] | {url, status, title, locale, section, depth, elapsed_ms}]"

# Base64 encode the chart PNG
- id: chart_b64
  depends_on: [status_chart]
  exec:
    command: "echo -n 'data:image/png;base64,' && base64 < ./artifacts/charts/status-distribution.png"
    shell: true

# Write all data variables
- id: write_dashboard_js
  depends_on: [tree_with_meta, build_graph, crawl_report, slim_pages, chart_b64, geo_analysis]
  with:
    tree: $tree_with_meta
    graph: $build_graph
    report: $crawl_report
    pages: $slim_pages
    chart: $chart_b64
    geo: $geo_analysis
  invoke:
    tool: "nika:write"
    params:
      file_path: "artifacts/tmp/dashboard-data.js"
      content: |
        var TREE = {{with.tree | to_json}};
        var GRAPH = {{with.graph | to_json}};
        var REPORT = {{with.report | to_json}};
        var CHART = {{with.chart | to_json}};
        var PAGES = {{with.pages | to_json}};
        var GEO = {{with.geo | to_json}};
      overwrite: true
```

### Markdown Renderer (inline, ~60 lines JS)

Safe DOM-based renderer using textContent and createElement (no innerHTML):
- `#` to `<h1>` through `######` to `<h6>`
- `**bold**` to `<strong>`, `*italic*` to `<em>`
- `- item` to `<ul><li>` lists
- `| col | col |` to `<table>` with styled rows
- ``` code blocks ``` to `<pre><code>`
- `---` to `<hr>`

### Page List (searchable table)

- Columns: URL (truncated), Status (colored badge), Title, Locale, Section, Depth
- Search input filters by URL/title substring
- Click column header to sort
- Status filter chips (2xx/3xx/4xx/5xx)
- Show "X of Y pages" count

### Health Overview

- SVG donut ring for health score (green/yellow/red)
- Horizontal stacked bar for status distribution
- Vertical bars for depth distribution
- AI crawler access grid (green/red dots per bot)

---

## Part 6: CI/Homebrew/Release

### Questions Socratiques

1. **La version nika sur Homebrew match-t-elle le binaire?** Le dernier tag est v0.64.0.
   Apres les changements moteur (jaq stdlib), il faut bumper a v0.65.0 et mettre a jour
   la formula Homebrew.

2. **Les CI passent?** Le daemon a des erreurs pre-existantes (auth_token). Le nika-py
   a un link error. Ces erreurs sont-elles bloquantes pour la release?

3. **Le Cargo.lock est a jour?** Oui, `jaq-core 1.5.1` et `jaq-std 1.6.0` sont lockes.

4. **Les nouveaux builtins (nika:jq, nika:tree_data) sont-ils documentes?** Il faut
   mettre a jour AGENTS.md, la doc des builtins, et le nika.md rules file.

### Checklist CI/Release

- [ ] Bump version a v0.65.0 dans Cargo.toml
- [ ] `cargo test --workspace --lib --exclude nika-py --exclude nika-daemon` PASS
- [ ] Update CHANGELOG.md avec les nouveaux builtins
- [ ] Update AGENTS.md: ajouter nika:jq et nika:tree_data a la liste des builtins
- [ ] Tag v0.65.0 + push tag
- [ ] Verifier que CI release workflow se declenche
- [ ] Mettre a jour homebrew-tap formula (SHA256 du nouveau binaire)
- [ ] `brew upgrade nika` fonctionne
- [ ] `nika doctor` passe

---

## Questions Socratiques

1. **Pourquoi pas upgrader a jaq 3.x?** Parce que l'API est incompatible (jaq-core 3.x
   utilise `Compiler` au lieu de `ParseCtx`). Le gain serait minimal vs le risque de regression
   sur les 1089 tests existants. jaq-core 1.5.1 + jaq-std 1.6.0 suffisent.

2. **Faut-il un `nika:template` builtin?** Pour remplacer l'awk injection, un tool qui
   lit un fichier template et fait du string replacement entre markers serait utile. Plus
   generique qu'un hack awk. A evaluer.

3. **Le dashboard devrait-il etre genere par un template engine?** Actuellement on injecte
   du JS entre des markers. Alternative: un vrai template HTML avec `{{TREE_DATA}}` syntax.
   Probleme: conflit avec le JS qui utilise aussi `{{...}}` (template literals).

4. **Les 80 nodes suffisent-ils?** Pour kubernetes.io (6138 pages), 80 nodes ne montre que
   1.3% du site. Faut-il un sampling plus intelligent (top N par groupe)?

5. **Le 3D Graph via CDN est-il acceptable?** Three.js (170.0) est charge depuis jsdelivr.
   Si l'utilisateur est offline, l'onglet 3D ne marche pas. Alternative: embarquer Three.js
   minifie dans le HTML (~600KB). Trop lourd?

6. **La classification regex est-elle suffisante?** `/attributes` etait classe "mkt" avant
   le fix. Faut-il permettre aux utilisateurs de passer leur propre mapping de classification?

7. **Faut-il un mode "diff" entre deux audits?** Comparer deux sitemap.json pour voir les
   pages ajoutees/supprimees/changees. Feature future mais architecture-relevant.
