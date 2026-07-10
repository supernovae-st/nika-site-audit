# AGENTS.md — nika-site-audit (legacy-era demonstration · read-only)

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
  queued before the engine tags. Do NOT treat builtins used here as
  canonical — `canon.yaml` in nika-spec is the truth.
- The engine ships real releases (v0.99.0 as of 2026-07-10 — brew
  `supernovae-st/tap/nika` · 27 builtins · check-before-run with the
  MODELS rung; the live number is `nika --version`, never this file).
  This repo remains a read-only reference until its workflow is
  modernized: `site-audit.nika.yaml` predates the v1 envelope and
  PARSE-fails on current engines (`schema` is no longer an envelope
  field) — probed 2026-07-10, expected, and exactly why the note above
  says do NOT treat this repo's surface as canonical.

## Editing rules

1. Workflow changes must keep `site-audit.nika.yaml` valid against the
   spec's JSON Schema + conformance runner (`nika-spec/conformance/`).
2. Commit trailer: `Co-Authored-By: Nika 🦋 <nika@supernovae.studio>`.
