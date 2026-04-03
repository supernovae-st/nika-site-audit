# HANDOFF — Dashboard v11: Native Data + Better DAG

> Date: 2026-04-04
> Repo: github.com/supernovae-st/nika-site-audit
> Engine: nika v0.64.0 (51e0d2ba0)
> Status: Cards + legend perfect. Treemap + force graph EMPTY.

---

## Situation

Le site audit workflow produit **5 artifacts** pour n'importe quel site:
- `sitemap.json` — données enrichies complètes ✅
- `crawl-report.md` — rapport SEO + GEO ✅
- `site-structure.md` — Mermaid ✅
- `charts/status-distribution.png` — bar chart via `nika:chart` ✅
- `audit-dashboard.html` — dashboard interactif ❌ (treemap + graph vides)

Le template HTML est **prouvé** — ouvre `prototypes/03-combined-dashboard.html` pour voir
le treemap + force graph fonctionner parfaitement avec des données hardcodées (6 locales,
17 nodes, 22 links, drag + zoom + tooltip).

## Problème

Le LLM (gpt-5.2) génère `var TREE = {...}; var GRAPH = {...};` mais:

1. **GRAPH dangling refs**: les `links` référencent des `id` qui n'existent pas dans `nodes`
   → le template filtre les liens invalides → graph vide
2. **TREE valeurs fausses**: le LLM compte mal (dit 139 au lieu de 52 pour essays)
3. **Treemap invisible**: brightness CSS trop basse (fixé à 40-80% dans dernier commit)

**Le LLM ne peut PAS générer un graphe auto-cohérent** — c'est structurellement impossible
car la cohérence `links[i] ∈ nodes[].id` n'est pas enforceable par prompt.

## Solution: Données 100% Natives

**Principe**: le LLM ne touche JAMAIS aux données du dashboard. Tout est calculé par
les outils natifs Nika (déterministe, exact, reproductible).

### Architecture cible

```
enriched_pages ──→ pages_by_locale ──→ TREE data (native)  ──→ format JS ──→ inject template
                                                                    ↑
internal_link_objects ──→ GRAPH data (native) ──────────────────────┘
```

### TREE — Construit nativement

On a déjà tout:
- `pages_by_locale` = `{locale: [page_objects...]}` → exact counts
- `pages_by_section` = `{section: [page_objects...]}` → exact counts
- Chaque page a `locale` + `section` fields

La structure TREE attendue par le template:
```javascript
var TREE = {
  name: "domain.com",
  total_pages: 1654,
  health_score: 98,
  children: [
    {name: "en", children: [{name: "/pricing", value: 18}, {name: "/blog", value: 156}]},
    {name: "fr", children: [{name: "/tarifs", value: 15}, {name: "/blog", value: 120}]}
  ]
};
```

**Comment construire nativement**:

Option A — `nika:enrich` + `exec: awk` (zero LLM):
```yaml
# 1. Enrichir chaque page avec "locale_section" = locale + "/" + section
- id: pages_with_locale_section
  depends_on: [enriched_pages]
  with: { pages: $enriched_pages }
  invoke:
    tool: "nika:enrich"
    params:
      array: "{{with.pages}}"
      fields:
        locale_section: "locale | default('default')"

# 2. group_by locale → on a déjà pages_by_locale

# 3. Pour chaque locale, group_by section → comptages exacts
# PROBLÈME: on ne peut pas faire un "nested group_by" en une seule task
# SOLUTION: passer pages_by_locale + pages_by_section + total au LLM
#           pour FORMATER (pas calculer)
```

Option B — LLM avec `structured:` + données exactes pré-calculées (recommandé):
```yaml
- id: dashboard_data
  depends_on: [pages_by_locale, pages_by_section, internal_link_objects, enriched_pages, broken_pages]
  with:
    by_locale: $pages_by_locale
    by_section: $pages_by_section
    links: $internal_link_objects
    pages: $enriched_pages
    broken: $broken_pages
  infer:
    prompt: |
      Format audit data as JavaScript. Use ONLY the exact numbers provided.

      SITE: {{inputs.url}}
      TOTAL: {{with.pages | length}}
      HEALTH: <compute from total - broken>
      BROKEN: {{with.broken | length}}

      LOCALE COUNTS (EXACT — use these numbers):
      {{with.pages | pluck('locale') | to_json}}

      SECTION COUNTS (EXACT — use these numbers):
      {{with.pages | pluck('section') | to_json}}

      REAL INTERNAL LINKS (use for graph — these are VERIFIED links):
      {{with.links | first(80) | to_json}}

      FORMAT: two var assignments, no markdown.
      var TREE = {name:"<domain>", total_pages:<N>, health_score:<N>, children:[...]};
      var GRAPH = {nodes:[...], links:[...]};

      TREE RULES:
      - Count locale occurrences from LOCALE COUNTS array above
      - For each locale, count section occurrences from SECTION COUNTS
      - values MUST match exact counts from the arrays

      GRAPH RULES:
      - nodes: extract url_path from REAL INTERNAL LINKS, deduplicate
      - links: create [from_path, to_path] from REAL INTERNAL LINKS
      - CRITICAL: ONLY use url_paths that exist in your nodes array
      - g (group): extract first path segment as group name
    temperature: 0.0
    max_tokens: 16000
  structured:
    schema:
      type: object
      required: [tree, graph]
      properties:
        tree:
          type: object
          required: [name, total_pages, health_score, children]
          properties:
            name: { type: string }
            total_pages: { type: integer }
            health_score: { type: integer, minimum: 0, maximum: 100 }
            children:
              type: array
              items:
                type: object
                required: [name, children]
                properties:
                  name: { type: string }
                  children:
                    type: array
                    items:
                      type: object
                      required: [name, value]
                      properties:
                        name: { type: string }
                        value: { type: integer, minimum: 0 }
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
                minItems: 2
                maxItems: 2
                items: { type: string }
    enable_repair: true
    max_retries: 3
```

Puis convertir le JSON structuré en JS et injecter:
```yaml
- id: html_dashboard
  depends_on: [dashboard_data]
  with: { data: $dashboard_data }
  exec:
    command: >-
      printf 'var TREE = %s;\nvar GRAPH = %s;\n'
      '{{with.data.tree | to_json}}'
      '{{with.data.graph | to_json}}'
      > ./artifacts/tmp/dashboard-data.js &&
      awk '/\/\/ ===== END DATA/{skip=0} !skip{print} /\/\/ ===== DATA/{skip=1;
      while((getline line < "./artifacts/tmp/dashboard-data.js")>0) print line}'
      ./templates/dashboard.html > ./artifacts/audit-dashboard.html &&
      echo 'Dashboard built'
    shell: true
```

**L'avantage clé du `structured:`**: la 5-layer defense de Nika valide le JSON schema,
retry automatiquement si invalide, et fait du LLM repair si nécessaire. Le LLM ne peut
pas retourner un objet qui ne match pas le schema.

**Le problème restant**: `structured:` valide la STRUCTURE (types, required fields) mais
pas la SÉMANTIQUE (les IDs dans links doivent exister dans nodes). Pour ça, il faut
passer les VRAIS liens internes au LLM (pas lui demander d'inventer).

### GRAPH — Données réelles du Round 2

On a déjà les vrais liens internes dans `internal_link_objects`:
```json
[
  {"url": "https://qrcode-ai.com/en/pricing", "anchor": "Pricing", "rel": ""},
  {"url": "https://qrcode-ai.com/en/docs", "anchor": "Docs", "rel": ""}
]
```

Les transformer en GRAPH data:
- `nodes`: extraire les url_path uniques → `{id: "/en/pricing", g: "en"}`
- `links`: pour chaque page source (les 20 sample pages), créer des edges
  `[source_path, target_path]`

Le problème: `internal_link_objects` n'a PAS le `source_url` (la page d'origine du lien).
On sait juste VERS quoi ça pointe, pas DEPUIS quoi. Pour avoir les edges réels, il faut
modifier la pipeline Round 2:

```yaml
# AU LIEU de json_query $..links[*] (perd le contexte source)
# UTILISER nika:enrich pour ajouter le source_url à chaque lien

- id: links_with_source
  depends_on: [sample_links]
  with: { results: $sample_links }
  invoke:
    tool: "nika:enrich"
    params:
      array: "{{with.results}}"
      fields:
        source_url: "url | url_path"  # La page source
        link_targets: "links | pluck('url')"  # Les URLs cibles
```

Ou plus simplement: faire un `for_each` sur les sample pages qui retourne
`{source: url_path, targets: [target_paths]}` via `nika:enrich`.

---

## Nika Features à Utiliser

### Déjà utilisés
| Feature | Où | Pourquoi |
|---------|-----|---------|
| `nika:enrich` | enriched_pages | locale, depth, section, soft_404 |
| `nika:group_by` | pages_by_locale, pages_by_section | comptages exacts |
| `nika:filter` | broken_pages, soft_404, hreflang, domain filter | filtrage natif |
| `nika:aggregate` | stats | count, avg, max |
| `nika:chart` | status_chart | PNG bar chart |
| `nika:map` | URL extraction | avec transform |
| `nika:json_merge` | URL combination, build_sitemap | concat + deep_merge |
| `nika:set_diff` | R2 new URLs, homepage diff | set difference |
| `nika:json_query` | JSONPath extraction | sub_urls, link objects |
| `extract: sitemap` | sitemap parsing | XML → JSON natif |
| `extract: metadata` | page crawl | title, desc, canonical, hreflang |
| `extract: links` | Round 2 sample | link discovery |
| `extract: text` | robots.txt, llms.txt | GEO analysis |
| `response: slim` | crawl, sitemap | ~800 bytes/page |
| `skills:` | seo-auditor.md | injected in all infer prompts |
| `context:` | dashboard template | loaded once |

### À ajouter pour le dashboard fix
| Feature | Usage | Détail |
|---------|-------|--------|
| `structured:` | dashboard_data | JSON schema enforcement, 5-layer defense |
| `nika:enrich` | links_with_source | ajouter source_url aux liens |
| `| url_path` transform | graph nodes | extraire paths des URLs |
| `| unique` transform | graph nodes | dédupliquer |

### Features disponibles mais pas encore exploités
| Feature | Potentiel |
|---------|----------|
| `agent:` verb | Deep analysis multi-turn par page (H1, word count, schema.org) |
| `nika:readability` | Extraction article pour word count / thin content |
| `nika:css_select` | Extraire H1, JSON-LD, éléments spécifiques |
| `nika:phash` | Détection images dupliquées |
| `nika:svg_render` | Rendre des SVG en PNG |
| `for_each + agent` | Audit deep par page avec tools |
| `nika:run` | Nested workflow pour analyse modulaire |

---

## Template Dashboard — Référence

Le template `templates/dashboard.html` (290 lignes) attend:

```javascript
// ===== DATA — Replace these two objects in your workflow =====
var TREE = {
  name: "domain",         // string
  total_pages: 1586,      // int
  health_score: 98,       // int 0-100
  children: [             // array of locale objects
    {
      name: "en",         // locale code
      children: [         // array of section objects
        {name: "/blog", value: 156},  // section + page count
        {name: "/docs", value: 230}
      ]
    }
  ]
};
var GRAPH = {
  nodes: [
    {id: "/", g: "root"},         // id = url_path, g = group
    {id: "/blog", g: "cnt"},
    {id: "/docs", g: "doc"}
  ],
  links: [
    ["/", "/blog"],               // [from_path, to_path]
    ["/", "/docs"],               // BOTH from AND to MUST exist in nodes
    ["/blog", "/docs"]
  ]
};
// ===== END DATA =====
```

**Groupes valides pour g**: `root`, `mkt`, `cnt`, `doc`, `co`, `prod`, `auth`
(le template a une color map `GC` pour ces groupes).

**Le template fait**:
1. **Cards** (line 98-116): 4 cards from TREE (total_pages, children.length, health, name)
2. **Treemap** (line 118-187): squarified algorithm, cellules colorées par locale
3. **Legend** (line 190-199): une entrée par locale avec count
4. **Force Graph** (line 202-276): canvas, physics simulation, drag + zoom + tooltip
5. **Tabs** (line 280-286): switch Treemap ↔ Link Graph

---

## DAG Actuel (38 tasks)

```
LAYER 0: fetch_robots, fetch_llmstxt (GEO seeds)
LAYER 1: fetch_sitemap, fetch_homepage (crawl seeds)
LAYER 2: fetch_sub_sitemaps, main_urls, homepage_urls_raw, homepage_link_objects
LAYER 3: sub_urls, homepage_urls → sitemap_urls → new_homepage_urls → all_urls
LAYER 4: crawl_pages (for_each, concurrency 10) + sample_urls
LAYER 5: sample_links → all_link_objects → internal_link_objects → discovered_urls
         → r2_new_urls → crawl_r2
LAYER 6: all_results → valid_results → enriched_pages
LAYER 7: pages_by_locale, pages_by_section, stats, broken_pages, soft_404_pages,
         hreflang_pages (all parallel, all native)
LAYER 8: hreflang_audit, geo_analysis, status_chart, mermaid_tree, dashboard_data
LAYER 9: build_sitemap, crawl_report, html_dashboard
```

**Ce qui doit changer**:
- `dashboard_data` doit dépendre de `internal_link_objects` (pour le graph)
- `dashboard_data` doit utiliser `structured:` au lieu de texte libre
- `html_dashboard` doit convertir le JSON structuré en JS puis injecter

---

## Tests de Vérification

Après le fix, ces 4 sites DOIVENT passer:

```bash
# Smoke test (rapide, 1 locale)
nika run site-audit.nika.yaml -i url=https://htmx.org
# → treemap: 1 gros bloc "default" avec sections (essays, attributes, posts...)
# → graph: 10+ nodes connectés

# Multi-locale (le vrai test)
nika run site-audit.nika.yaml -i url=https://qrcode-ai.com
# → treemap: 38 blocs colorés, un par locale
# → graph: 20+ nodes, liens entre sections

# Scale (6000+ pages)
nika run site-audit.nika.yaml -i url=https://kubernetes.io
# → treemap: 15 locales avec tailles proportionnelles
# → graph: docs hierarchy visible

# Spider mode (pas de sitemap)
nika run site-audit.nika.yaml -i url=https://books.toscrape.com
# → treemap: 1 locale "default", sections par catégorie de livres
# → graph: catalogue hierarchy
```

**Vérification visuelle**:
```bash
open artifacts/audit-dashboard.html
# 1. Cards: 4 cards avec bonnes valeurs
# 2. Treemap tab: blocs colorés proportionnels, hover = tooltip
# 3. Link Graph tab: nodes avec labels, edges visibles, drag fonctionne, zoom wheel
# 4. Legend: locales avec comptages corrects
```

**Vérification programmatique**:
```bash
# Les données du dashboard doivent matcher sitemap.json
python3 -c "
import json, re
html = open('artifacts/audit-dashboard.html').read()
data = json.load(open('artifacts/sitemap.json'))
# Check TREE has all locales
locales_in_html = re.findall(r'name:\"(\w+)\"', html[:5000])
locales_in_data = list(data['pages_by_locale'].keys())
print(f'Locales in HTML: {len(set(locales_in_html))}')
print(f'Locales in data: {len(locales_in_data)}')
# Check GRAPH has nodes
nodes = re.findall(r'id:\"([^\"]+)\"', html)
links_from = re.findall(r'\[\"([^\"]+)\",', html)
print(f'Graph nodes: {len(nodes)}, links: {len(links_from)}')
dangling = [l for l in links_from if l not in [n for n in nodes]]
print(f'Dangling refs: {len(dangling)}')
"
```

---

## Résumé Exécutif

| Ce qui marche | Ce qui marche pas | Solution |
|---------------|-------------------|----------|
| 37/38 tasks passent | dashboard treemap vide | Passer vrais comptages, pas sample |
| 5 artifacts générés | dashboard graph vide | Utiliser vrais liens de Round 2 |
| 4 sites testés (52/52) | LLM invente des URLs | `structured:` + vrais liens |
| GEO + SEO skill | Données non déterministes | Natif = reproductible |
| nika:chart PNG | Template prouvé, données fausses | Séparer template (fixe) / données (native) |
