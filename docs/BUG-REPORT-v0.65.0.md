# Bug Report — nika-site-audit v0.65.0 E2E

> Date: 2026-04-04
> Binary: nika 0.65.0-dev (acda8a7)
> Test: Clean env on Desktop, release binary, fresh clone

## E2E Results

| Site | Pages | Time | Cost | Status |
|------|-------|------|------|--------|
| books.toscrape.com | 640 | ~2min | $0.12 | **PASS** (43/43 tasks) |
| htmx.org | TBD | ~3min | TBD | Running... |

## BUG-041: jaq-core 1.5.x regex panic on null input

**Severity**: MEDIUM (caught by catch_unwind, returns clean error)
**Impact**: `build_graph` fails with `--provider mock` because mock data URLs may trigger jaq-core regex `test()` to panic on null/non-string input at `jaq-core/src/regex.rs:96`.
**Workaround**: `catch_unwind` in `eval_jq()` converts panic to error. Works fine with real data.
**Root cause**: jaq-core 1.5.x calls `.unwrap()` on regex match result without null check.
**Fix options**:
1. Upgrade to jaq-core 3.x (breaking API: `ParseCtx` → `Compiler`) — HIGH effort
2. Pre-filter non-string values before passing to jq — MEDIUM effort
3. Accept (mock-only issue) — done, catch_unwind prevents crash

## BUG-042: 1 exec awk remaining (not 100% native)

**Severity**: LOW (awk is standard POSIX, always available)
**Impact**: `html_dashboard` task uses `exec: awk` to inject JS data into HTML template.
**Root cause**: No `nika:template` or `nika:inject` builtin tool exists.
**Fix**: Implement `nika:inject` tool that reads a file, replaces content between markers, writes output. ~30 lines in data_tools.rs.

Spec:
```yaml
- id: html_dashboard
  invoke:
    tool: "nika:inject"
    params:
      template: "./templates/dashboard.html"
      output: "./artifacts/audit-dashboard.html"
      start_marker: "// DATA —"
      end_marker: "// CONSTANTS & HELPERS"
      content: "{{with.dashboard_js}}"
```

## BUG-043: gpt-5.2 model not in pricing catalog

**Severity**: COSMETIC (warns but works)
**Impact**: `Unknown model — using default pricing ($5/$15 per M tokens)` warning on every LLM call.
**Fix**: Add gpt-5.2 to `nika-core/src/catalogs/models.rs` pricing table.

## Observations

- Dashboard HTML renders correctly (1601 lines, 8 tabs)
- `nika check` validates in 36ms from fresh clone
- `nika provider list` shows correct status
- Artifacts: sitemap.json (4.3M), crawl-report.md (13K), site-structure.md (1.9K), audit-dashboard.html (280K)
- Total cost: $0.12 for full 640-page audit (4 LLM calls only)
