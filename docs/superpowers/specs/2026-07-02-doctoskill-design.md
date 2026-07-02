# DocToSkill — Design

## Purpose

A Python CLI script that crawls a live framework/library documentation website
and converts it into an Agent Skill: a `SKILL.md` router plus a `references/`
folder of markdown files, following the standard progressive-disclosure skill
pattern. The output is plain markdown + YAML frontmatter with no
vendor-specific runtime dependency — any agent/tool that can read
instructions from files (Claude, or otherwise) can consume the generated
skill. The generator itself also has no required LLM/API dependency; it does
pure HTML→markdown conversion, not AI-driven rewriting, so it produces
deterministic output and runs with no API key.

## Non-Goals

This is intentionally a small, single-purpose script, not a platform.
Explicitly out of scope: GitHub repo / PDF / video ingestion, multi-platform
export formats (Gemini/OpenAI/LangChain/etc.), an MCP server, agent-specific
installers, or a plugin/preset ecosystem. The value proposition is
simplicity and auditability — one script, one input type (a doc site URL),
one output format (a plain markdown skill folder) — not feature breadth.

## Scope

One skill = one crawl root. A "doc site" for this tool means whatever
nav-tree/path-prefix the user-supplied starting URL belongs to — not
necessarily the whole domain. Many real doc sites host multiple independent
sections under one domain (e.g. Unity's `.../manual/` guide vs
`.../api/` scripting reference) with separate nav trees and different content
shapes (prose guide vs API reference entries). Each such section should be
crawled separately by running the script again with a different start URL,
producing a separate skill. The script does not attempt to discover or merge
sibling sections automatically.

## CLI Interface

```
doctoskill.py <start-url> --output <dir> --name <skill-name> [--max-pages N] [--delay SECONDS] [--config <file>] [--skip-scrape] [--zip]
```

- `start-url` (required, positional) — first page of the docs to crawl.
- `--output` — directory to write the skill folder into. Default: `./skills`.
- `--name` — skill folder / `SKILL.md` name. Default: derived from the
  start URL's domain + path (slugified).
- `--max-pages` — safety cap on number of pages crawled. Default: 500.
- `--delay` — seconds to wait between requests. Default: 0.5.
- `--config` — optional path to a JSON override file (see Override Config
  below). Omit for fully automatic zero-config operation.
- `--skip-scrape` — reuse cached raw page data from a previous run instead
  of re-crawling (see Caching below); jump straight to convert/assemble.
- `--zip` — after assembling the skill folder, also produce a `.zip` of it
  alongside the output directory, for tools that expect a packaged upload.
- `--enhance` — optional post-processing pass using the Anthropic API to
  improve `SKILL.md` (pick 5-10 representative code examples across the
  crawled pages, sharpen the overview/index copy). Off by default; requires
  `ANTHROPIC_API_KEY`. The deterministic HTML→markdown conversion output is
  untouched either way — this only rewrites `SKILL.md` itself, so the tool's
  core guarantee (works with no API key, no vendor lock-in) holds without
  the flag.

## Override Config (escape hatch)

Auto-discovery (nav-tree → sitemap → path-prefix crawl) is the default and
requires no configuration. For sites where auto-discovery guesses wrong, an
optional `--config <file>` JSON file can override specific pipeline
decisions:

```json
{
  "include": ["/docs/", "/guide/"],
  "exclude": ["/docs/changelog/"],
  "content_selector": "main.article-content",
  "nav_selector": "nav.sidebar"
}
```

All fields are optional; any field present overrides the corresponding
auto-detected behavior, fields absent keep automatic detection. This exists
purely as a fallback for uncooperative sites — it is never required for a
normal run.

## Caching

Raw fetched page HTML is cached to disk under `<output>/<name>/.cache/`,
keyed by URL, on every crawl. `--skip-scrape` reuses this cache instead of
re-fetching, so the convert/assemble steps (or a changed `--config`) can be
re-run quickly without hitting the target site again. The cache is
per-skill-name and is not committed as part of the skill output (excluded
from the `.zip`).

## Zip Packaging

With `--zip`, after the skill folder is assembled, it's archived to
`<output>/<name>.zip` (skill folder contents at the zip root, `.cache/`
excluded) for tools/workflows that expect a single uploadable package rather
than a directory.

## Pipeline

1. **Politeness check** — fetch `robots.txt` for the start URL's domain.
   If it disallows the entire path prefix of the start URL, abort with a
   clear error before crawling anything. Otherwise respect per-path
   disallow rules during discovery/crawl.

2. **Discovery** — determine the full set of pages to crawl and, where
   possible, their hierarchy. If `--config` supplies `include`/`exclude`
   patterns or a `nav_selector`, those take precedence over the
   corresponding auto-detection step below. Otherwise, strategies are tried
   in order, first success wins:
   - **llms.txt**: check for `llms-full.txt` then `llms.txt` at the domain
     root. When present, this is a pre-curated, LLM-ready markdown document
     maintained by the site itself — use it directly instead of
     scraping/parsing HTML at all. Skips discovery, fetch, and convert
     entirely for whatever it covers; only Assemble (step 5, splitting it
     into reference files) still runs. If it only partially covers the
     requested path prefix, fall through to the remaining strategies for the
     rest.
   - **Nav-tree parsing**: look for a site-generator-specific TOC/sidebar
     structure and parse it directly. This is the preferred path because it
     gives both the page list *and* the true hierarchy (which often does not
     match URL path structure — e.g. DocFX sites use flat URLs under one
     directory with all nesting expressed only in the TOC). DocFX's
     `toc.html` format is the first-class supported case, since it's common
     among framework/engine doc sites (Unity, .NET, etc.). Generic heuristics
     (common sidebar/nav markup patterns used by MkDocs, Docusaurus, Sphinx)
     are attempted as secondary nav-tree parsers before giving up on this
     strategy.
   - **Sitemap.xml**: fetch `sitemap.xml` (or the one referenced in
     `robots.txt`), filter URLs to those under the start URL's path prefix.
     Gives a flat page list, no hierarchy — hierarchy falls back to URL path
     segments.
   - **Path-prefix link crawling**: breadth-first crawl following in-page
     links, keeping only URLs whose path starts with the start URL's path
     prefix, same domain. Last resort. Hierarchy falls back to URL path
     segments (or a single flat folder if the site uses flat URLs, as
     detected by all discovered pages sharing one directory).

3. **Fetch** — for each discovered page: plain HTTP GET + parse, or read from
   cache if `--skip-scrape`. If the resulting content looks like a
   JS-rendering shell (body text below a minimum length threshold, or
   missing an expected main-content selector), retry that single page with a
   headless browser (Playwright) render. Playwright is imported lazily, only
   the first time it's actually needed. Raw fetched HTML is written to the
   cache (see Caching) as each page is fetched.

4. **Convert** — strip nav/header/footer/sidebar/ad/boilerplate elements
   (using `content_selector` from `--config` if supplied, otherwise
   auto-detected), convert the remaining main-content HTML to clean
   markdown, one page per file.

5. **Assemble skill**:
   - Reference files are placed at `references/<hierarchy-path>/<page>.md`,
     where the hierarchy comes from the nav tree when available, otherwise
     from URL path segments, otherwise flat.
   - Folder and file names are slugified from the nav item / page title
     (not raw URL slugs, which are often inconsistent with the displayed
     title).
   - `SKILL.md` is generated with:
     - YAML frontmatter (`name`, `description` — what the framework is and
       when this skill is relevant) using plain, vendor-neutral fields so
       the file works as-is across different agent tools' skill conventions
     - A short overview of the framework/library
     - An index mapping topics/sections to their `references/*.md` paths,
       so an agent can decide which reference file(s) to open for a given
       question without loading everything upfront

## Error Handling

- Per-page fetch/convert failures are logged and skipped; they don't abort
  the whole run.
- If nav-tree parsing finds no recognizable structure, fall back silently to
  sitemap discovery; if that yields nothing under the path prefix, fall back
  silently to path-prefix link crawling.
- If robots.txt disallows the whole start path, abort immediately with a
  clear error.
- A summary is printed at the end: pages found, converted, skipped/failed,
  discovery strategy used.
- If `--skip-scrape` is given but no cache exists yet for `<name>`, fall back
  to a normal crawl (with a warning) rather than failing.

## Dependencies

- `requests` — HTTP fetching
- `beautifulsoup4` — HTML parsing (nav-tree parsing, boilerplate stripping)
- `markdownify` — HTML → Markdown conversion
- `playwright` — headless-browser fallback for JS-rendered pages (lazy
  import, optional extra)
- `anthropic` — only imported/required when `--enhance` is passed (lazy
  import, optional extra)

## Testing Approach

This tool's core value is scraping real, uncontrolled third-party websites,
so end-to-end testing is manual: run against a couple of real doc sites
(including a DocFX site, e.g. Unity Entities manual) and inspect the
generated skill folder for correctness.

Pure logic is unit-testable against fixture HTML/XML saved from real pages:
- path-prefix filtering
- slugification
- sitemap XML parsing
- DocFX `toc.html` parsing
- JS-shell detection heuristic
