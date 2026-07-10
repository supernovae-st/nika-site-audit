# Enriched Plan: 100% Native Dashboard + Interactive Multi-View Graph

> Date: 2026-04-04
> Status: EXECUTING
> Base: 2026-04-04-native-dashboard-plan.md (enriched + brainstormed)
> Repos: nika (engine), nika-site-audit (workflow + dashboard)

---

## Sprint 1: Engine — nika:jq + nika:tree_data (~1h)

### 1A. Make `eval_jq` public in transform.rs

The `compile_jq()` function at line 1086 is private. We need a public `eval_jq()` wrapper:

```rust
/// Evaluate a jq expression on a JSON value.
/// Used by the `| jq()` transform AND the `nika:jq` builtin tool.
pub fn eval_jq(expr: &str, data: &serde_json::Value) -> Result<serde_json::Value, String> {
    let filter = compile_jq(expr)?;
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

### 1B. Register `nika:jq` tool in data_tools.rs + router.rs

JqTool struct: deserialize `data` (Value) + `expr` (String), call `eval_jq()`.

### 1C. Register `nika:tree_data` tool in data_tools.rs + router.rs

Pure Rust nested group_by → hierarchical tree. No LLM.
Params: `array`, `group_by`, `sub_group_by`, `name_prefix`, `sort`.

### 1D. Tests (6 minimum)

1. `tool_jq_basic_group_by` — group array by field
2. `tool_jq_nested_tree` — nested group_by for treemap data
3. `tool_jq_graph_classification` — regex test() for path classification
4. `tool_jq_error_on_bad_expr` — invalid jq expression
5. `tool_tree_data_basic` — 2-level grouping
6. `tool_tree_data_sort_desc` — sort children by value descending

---

## Sprint 2: Dashboard — 8-Tab Interactive Multi-View (~3h)

### Current tabs (4): Treemap, Force Graph, Tree Layout, 3D Graph
### New tabs (4): Report, Page List, Health Overview, Status Chart

### 2A. Force Graph: 5 Layout Modes

Sub-toolbar with pill buttons below Force Graph tab:
`[Force] [Radial] [Hierarchy] [Circular] [Cluster]`

| Layout | Algorithm | Description |
|--------|-----------|-------------|
| Force | Spring+repulsion (existing) | General structure |
| Radial | BFS depth rings from root | Hierarchy visualization |
| Hierarchical | Top-down BFS layers | Parent-child tree |
| Circular | Group centroids on circle | Group distribution |
| Cluster | Per-group force sim | Isolated group comparison |

Smooth easeOutCubic transition animation (60 frames, ~1s).

### 2B. Node Info Panel (slide-in right, 320px)

Click node → panel slides in showing:
- Path (clickable link)
- Group badge with color dot
- Connection count
- Connected nodes list (clickable)
- Parent/children breakdown

Close on Escape or click outside.

### 2C. Report Tab

Minimal safe markdown→HTML renderer (~80 lines):
- Headings (# through ######)
- Bold/italic (**text**, *text*)
- Unordered lists (- item)
- Tables (| col | col |)
- Code blocks (```)
- Horizontal rules (---)
- Links ([text](url))
All using createElement + textContent (zero innerHTML with untrusted data).

### 2D. Page List Tab

Searchable, sortable, filterable data table:
- Columns: URL (truncated to 60ch), Status (colored badge), Title, Locale, Section, Depth
- Search input (filters by URL/title substring, debounced)
- Column header click → sort (asc/desc toggle)
- Status filter chips: [All] [2xx] [3xx] [4xx] [5xx]
- "Showing X of Y pages" counter
- Virtual scrolling for 1000+ pages (render visible rows only)

### 2E. Health Overview Tab

- SVG donut ring: overall health score (green/yellow/red gradient)
- Horizontal stacked bar: status code distribution (2xx/3xx/4xx/5xx)
- Vertical bar chart: crawl depth distribution (0-5+)
- AI Crawler grid: green/red dots for Googlebot, Bingbot, GPTBot, ClaudeBot, etc.
- Key metrics: avg response time, orphan pages count, redirect chains

### 2F. Status Chart Tab

Embedded base64 PNG chart from nika:chart tool.
Centered `<img>` element with zoom on click.

### 2G. Enhanced Interactions (all graph views)

- Edge hover: thicken + tooltip (source → target)
- Edge click: detail in info panel
- Double-click node: zoom + highlight 1-hop neighborhood
- Selected node: white ring, persists until click elsewhere
- Keyboard: Arrow keys to navigate selected node's neighbors

### 2H. New Data Variables

```javascript
var TREE = {...};      // existing — treemap hierarchy
var GRAPH = {...};     // existing — nodes + links
var REPORT = "...";   // NEW — raw markdown string
var PAGES = [...];    // NEW — [{url, status, title, locale, section, depth, elapsed_ms}]
var STATS = {...};    // NEW — {health_score, status:{ok,redirect,error}, depths:{0:N,...}, crawlers:{...}}
var CHART = "data:…"; // NEW — base64 PNG (optional)
```

### Brainstorm Additions

- **Broken links highlight**: Red pulsing edges in graph for 4xx/5xx links
- **Orphan pages indicator**: Nodes with 0 inbound links get dashed border
- **Link equity flow**: Edge thickness proportional to PageRank-like score
- **Depth heatmap on treemap**: Color brightness = crawl depth (deeper = darker)
- **Response time overlay**: Node size proportional to response time (slow = bigger = red)
- **Redirect chain viz**: Orange dashed edges for 3xx chains
- **Export button**: Download dashboard data as JSON, or screenshot as PNG (html2canvas)
- **Dark/light toggle**: Quick theme switch
- **Responsive**: Mobile-friendly layout with touch zoom/pan

---

## Sprint 3: Workflow — 100% Native (~30min)

Replace exec-based tasks with native builtins:

```
BEFORE: write_pages_json → exec jq → exec jq → exec awk → html
AFTER:  nika:tree_data → nika:jq → nika:write → nika:write
```

Zero external tool dependencies (no jq, no awk, no python).

---

## Sprint 4: Verification + Push (~30min)

1. `cargo test --workspace --lib --exclude nika-py` — all green
2. `nika check site-audit.nika.yaml` — validates
3. Push nika engine changes
4. Update memory with session context
5. Update CHANGELOG if version bump needed

---

## Verification Checklist

- [ ] `nika:jq` works with complex nested group_by expressions
- [ ] `nika:tree_data` produces correct locale/section hierarchy
- [ ] Dashboard loads with all 8 tabs
- [ ] Force graph switches between 5 layouts with smooth animation
- [ ] Clicking node opens info panel
- [ ] Report tab renders markdown safely
- [ ] Page List tab is searchable and sortable
- [ ] Health tab shows donut ring + status bars
- [ ] Broken links highlighted in red in graph views
- [ ] No external tool dependencies in workflow pipeline
- [ ] All tests pass
