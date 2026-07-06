# AGENTS.md — nika-site-audit (canonical reference workflow)

Vendor-neutral agent entry per the AGENTS.md convention (agents.md).

## What this repo is

The **canonical end-to-end reference workflow** for
[Nika](https://github.com/supernovae-st/nika) — crawl a site, detect
locales, validate hreflang, generate dashboards and reports. Read it as
« what a real Nika workflow looks like ».

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
- The engine has a public release-candidate (`0.90.0`) and continues toward
  the 1.0 public API lock. This repo remains a read-only reference until its
  workflow is modernized to the current stdlib surface.

## Editing rules

1. Workflow changes must keep `site-audit.nika.yaml` valid against the
   spec's JSON Schema + conformance runner (`nika-spec/conformance/`).
2. Commit trailer: `Co-Authored-By: Nika 🦋 <nika@supernovae.studio>`.
