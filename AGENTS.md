# AGENTS.md — nika-site-audit (v1 workflow · runs on the released engine)

Vendor-neutral agent entry per the AGENTS.md convention (agents.md).

## What this repo is

A **legacy-era demonstration** of a large real-world Nika workflow —
crawl a site, detect locales, validate hreflang, generate dashboards
and reports. It shows the SCALE a workflow can reach; it does NOT show
current syntax. **Never learn the language from this repo** — the
current language lives in
[`supernovae-st/nika-spec`](https://github.com/supernovae-st/nika-spec)
and its showcase examples ship inside the engine (`nika examples`).

## Load-bearing facts (verify in-repo · never from memory)

- This legacy workflow's envelope is `schema: nika/workflow@0.12` · the
  current language (envelope `nika: v1`) is defined in
  [`supernovae-st/nika-spec`](https://github.com/supernovae-st/nika-spec)
  (Apache-2.0) · counts live in its `canon.yaml` (the SSOT — never
  hardcode them in prose).
- ⚠️ **Era caveat** · this workflow was written against the
  pre-consolidation builtin surface. The stdlib v0.1 canonical set was
  consolidated (one data language — several former builtins such as
  `nika:map` / `nika:filter` / `nika:enrich` are now `nika:jq` recipes per
  the spec's builtins doc). A modernization pass to the v0.1 surface is
  landed with the v1 rewrite (2026-07). Do NOT treat builtins used here as
  canonical — `canon.yaml` in nika-spec is the truth.
- The engine ships real releases (v0.105.0 as of 2026-07-20 — brew
  `supernovae-st/tap/nika` · the live number is `nika --version`, never
  this file). `site-audit.nika.yaml` is the V1 SURFACE — modernized
  2026-07-10, checks clean and runs end-to-end on the released binary
  (check · golden `nika test` · live run · `nika trace verify`). The
  brouillon-era (April 2026) 1072-line pipeline is preserved at
  `legacy/site-audit-v10.nika.yaml` (pre-v1 dialect · read-only
  reference · does not parse on current engines — by design).

## Editing rules

1. Workflow changes must keep `site-audit.nika.yaml` valid against the
   spec's JSON Schema + conformance runner (`nika-spec/conformance/`).
2. Commit trailer: `Co-Authored-By: Nika 🦋 <nika@supernovae.studio>`.
