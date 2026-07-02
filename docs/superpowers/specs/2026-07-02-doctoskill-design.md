# DocToSkill — Design

## Purpose

A Python CLI script that crawls a live framework/library documentation website
and converts it into a Claude Agent Skill: a `SKILL.md` router plus a
`references/` folder of markdown files, following the standard
progressive-disclosure skill pattern.

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
doctoskill.py <start-url> --output <dir> --name <skill-name> [--max-pages N] [--delay SECONDS]
```

- `start-url` (required, positional) — first page of the docs to crawl.
- `--output` — directory to write the skill folder into. Default: `./skills`.
- `--name` — skill folder / `SKILL.md` name. Default: derived from the
  start URL's domain + path (slugified).
- `--max-pages` — safety cap on number of pages crawled. Default: 500.
- `--delay` — seconds to wait between requests. Default: 0.5.

## Pipeline

1. **Politeness check** — fetch `robots.txt` for the start URL's domain.
   If it disallows the entire path prefix of the start URL, abort with a
   clear error before crawling anything. Otherwise respect per-path
   disallow rules during discovery/crawl.

2. **Discovery** — determine the full set of pages to crawl and, where
   possible, their hierarchy. Strategies are tried in order, first success
   wins:
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

3. **Fetch** — for each discovered page: plain HTTP GET + parse. If the
   resulting content looks like a JS-rendering shell (body text below a
   minimum length threshold, or missing an expected main-content selector),
   retry that single page with a headless browser (Playwright) render.
   Playwright is imported lazily, only the first time it's actually needed.

4. **Convert** — strip nav/header/footer/sidebar/ad/boilerplate elements,
   convert the remaining main-content HTML to clean markdown, one page per
   file.

5. **Assemble skill**:
   - Reference files are placed at `references/<hierarchy-path>/<page>.md`,
     where the hierarchy comes from the nav tree when available, otherwise
     from URL path segments, otherwise flat.
   - Folder and file names are slugified from the nav item / page title
     (not raw URL slugs, which are often inconsistent with the displayed
     title).
   - `SKILL.md` is generated with:
     - YAML frontmatter (`name`, `description` — what the framework is and
       when this skill is relevant)
     - A short overview of the framework/library
     - An index mapping topics/sections to their `references/*.md` paths,
       so Claude can decide which reference file(s) to open for a given
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

## Dependencies

- `requests` — HTTP fetching
- `beautifulsoup4` — HTML parsing (nav-tree parsing, boilerplate stripping)
- `markdownify` — HTML → Markdown conversion
- `playwright` — headless-browser fallback for JS-rendered pages (lazy
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
