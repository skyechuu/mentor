# Mentor

**Mentor teaches agents how to do stuff by turning documentation websites into Agent Skills.**

Give Mentor the root URL of a framework, library, engine, or product manual. It
discovers the relevant pages, converts them to clean Markdown, and produces a
portable skill that an agent can navigate without loading the entire manual into
context.

Mentor is deterministic by default, vendor-neutral, and does not require an API
key. An optional Anthropic-powered pass can polish the generated `SKILL.md`.

## What Mentor creates

```text
skills/
└── product-version/
    ├── SKILL.md
    └── references/
        ├── introduction.md
        ├── concepts/
        │   └── components.md
        └── workflows/
            └── setup.md
```

- `SKILL.md` contains vendor-neutral YAML frontmatter, a short overview, and a
  reference index.
- `references/` contains one cleaned Markdown file per documentation page.
- Names and descriptions are derived from the product, version, API identifiers,
  `##`/`###` headings, and navigation tree so an agent can recognize when the
  skill is relevant.
- Crawl caches and macOS metadata are never included in the skill or its ZIP.

## Features

- Four discovery strategies with automatic fallback: `llms-full.txt`/`llms.txt`,
  navigation trees, `sitemap.xml`, and path-prefix link crawling.
- First-class DocFX TOC support plus generic sidebar/navigation detection.
- Same-domain and same-path crawl boundaries with `robots.txt` checks.
- Plain HTTP fetching with optional Playwright fallback for JavaScript-rendered
  pages.
- HTML boilerplate and DocFX navigation cruft removal.
- Hierarchy-aware Markdown references and trigger-oriented skill metadata.
- External raw-HTML cache for fast offline regeneration.
- Clean, deterministic ZIP archives without `.cache`, `.DS_Store`, `._*`, or
  `__MACOSX` entries. Archives are published atomically only after all requested
  generation and enhancement steps succeed.
- Live progress messages during long operations, with a quiet mode for scripts.
- Optional Anthropic enhancement of `SKILL.md`; reference files remain
  deterministic.
- Python 3.9+ support.

## Installation

Clone the repository and create an isolated environment:

```bash
git clone https://github.com/skyechuu/mentor.git
cd mentor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

On Windows PowerShell, activate with:

```powershell
.venv\Scripts\Activate.ps1
```

Verify the installation:

```bash
mentor --help
# Equivalent: python -m mentor --help
```

The former `doctoskill` command and `python -m doctoskill` remain available as
backward-compatible aliases.

### Optional dependencies

For JavaScript-rendered documentation:

```bash
python -m pip install -e ".[playwright]"
python -m playwright install chromium
```

For `--enhance`:

```bash
python -m pip install -e ".[enhance]"
export ANTHROPIC_API_KEY="your-key"
```

Install everything needed for development and optional features:

```bash
python -m pip install -e ".[playwright,enhance,dev]"
python -m playwright install chromium
```

## Quick start

```bash
mentor https://docs.example.com/manual/index.html \
  --output ./skills \
  --zip
```

Mentor prints progress to stderr while keeping the final summary on stdout:

```text
[mentor] Checking robots.txt permissions.
[mentor] Checking for llms-full.txt or llms.txt.
[mentor] Checking sitemap.xml.
[mentor] Fetching and converting page 3/42: https://...
[mentor] Assembling 42 pages into skill: example-2.0
[mentor] Finished successfully.
Strategy: sitemap
Pages found: 42
Pages converted: 42
Pages skipped/failed: 0
Skill written to: skills/example-2.0
```

## Complete CLI reference

```text
mentor START_URL [--output DIR] [--name NAME] [--max-pages N]
                 [--delay SECONDS] [--config FILE] [--skip-scrape]
                 [--zip] [--enhance] [--quiet]
```

| Argument | Default | Description |
| --- | --- | --- |
| `START_URL` | Required | First documentation page and crawl root. Must be an absolute `http://` or `https://` URL. |
| `--output DIR` | `./skills` | Parent directory in which the generated skill folder is written. |
| `--name NAME` | Auto-detected | Overrides the generated skill name. Names are normalized to lowercase and may contain letters, numbers, hyphens, and version dots. |
| `--max-pages N` | `500` | Safety cap on discovered and converted pages. Must be at least `1`. |
| `--delay SECONDS` | `0.5` | Delay between requests made by fallback link crawling. Must be zero or greater. |
| `--config FILE` | None | JSON override file for include/exclude rules and CSS selectors. |
| `--skip-scrape` | Off | Reuse cached raw pages without downloading them again. If no cache exists, Mentor warns and performs a normal crawl. |
| `--zip` | Off | After all requested steps succeed, atomically creates `<output>/<name>.zip` with skill contents at the archive root. |
| `--enhance` | Off | Uses Anthropic to improve only `SKILL.md`. Requires the `enhance` extra and `ANTHROPIC_API_KEY`. |
| `--quiet` | Off | Suppresses progress messages. Warnings, errors, and the final summary remain visible. |
| `-h`, `--help` | — | Displays command help and exits. |

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Skill generated successfully. |
| `1` | No pages could be converted, or optional enhancement failed. |
| `2` | Invalid arguments/configuration, or `robots.txt` disallowed the start URL. |

## How discovery works

Mentor tries strategies in priority order and uses the first useful result:

1. **`llms-full.txt` / `llms.txt`** — checks the domain root for pre-curated
   Markdown and splits it into reference sections.
2. **Navigation tree** — checks a sibling DocFX `toc.html`, then looks for a
   generic sidebar or navigation tree on the start page. This preserves the
   documentation's real hierarchy even when URLs are flat.
3. **`sitemap.xml`** — loads sitemap URLs and keeps only entries under the start
   URL's path prefix.
4. **Path-prefix crawl** — breadth-first follows links on the same domain and
   under the same path prefix, up to `--max-pages`.

One run intentionally creates one skill for one crawl root. Use separate runs for
independent documentation sections such as a user manual and API reference.

## Override configuration

Use `--config` when automatic discovery or content selection needs help:

```json
{
  "include": ["/docs/", "/guide/"],
  "exclude": ["/docs/changelog/", "/docs/archive/"],
  "content_selector": "main.article-content",
  "nav_selector": "nav.sidebar"
}
```

All fields are optional:

| Field | Type | Effect |
| --- | --- | --- |
| `include` | Array of strings | Keeps discovered URLs containing at least one listed fragment. An empty array includes all in-scope URLs. |
| `exclude` | Array of strings | Removes URLs containing any listed fragment. |
| `content_selector` | CSS selector or `null` | Selects the page element converted to Markdown instead of automatic `main`/`article` detection. |
| `nav_selector` | CSS selector or `null` | Selects the navigation container used by generic tree parsing. |

Example:

```bash
mentor https://example.com/docs/index.html \
  --config ./mentor-config.json \
  --output ./skills
```

## Cache and offline regeneration

Raw HTML is working data, not part of the generated skill. Mentor stores it in a
sibling cache outside `--output`:

```text
project/
├── .mentor-cache/       # local scraper cache; never packaged
└── skills/              # generated skills safe to share
```

Cache entries are separated by output directory, host, and start URL. Rebuild
from cached pages with:

```bash
mentor https://example.com/docs/index.html \
  --output ./skills \
  --skip-scrape \
  --zip
```

Mentor automatically migrates caches created by older DocToSkill versions.

## Naming and descriptions

Without `--name`, Mentor derives a concise product/version name. For example:

```text
https://docs.unity3d.com/Packages/com.unity.entities@6.5/manual/index.html
→ unity-entities-6.5
```

Descriptions identify the product and prioritize API/concept terms extracted from
`##`/`###` headings, inline code, and code samples. Page titles are used only as a
fallback. They also instruct the consuming agent to open only relevant reference
files. This makes generated skills discoverable without using a raw URL slug as
their identity.

## JavaScript-rendered pages

Mentor first performs a normal HTTP request. If a page looks like an empty app
shell, it retries with Playwright. Install the `playwright` extra and Chromium as
shown above. Server-rendered sites do not require Playwright.

## Optional Anthropic enhancement

`--enhance` sends the current `SKILL.md` and selected reference excerpts to the
Anthropic API, then replaces only `SKILL.md`. The converted reference documents
are never rewritten by the model.

```bash
export ANTHROPIC_API_KEY="your-key"
mentor https://example.com/docs/ \
  --output ./skills \
  --enhance \
  --zip
```

Review your source documentation's privacy requirements before enabling this
option because representative excerpts are sent to an external API.

## Common recipes

Create a versioned Unity Entities skill:

```bash
mentor \
  https://docs.unity3d.com/Packages/com.unity.entities@6.5/manual/index.html \
  --output ./skills \
  --zip
```

Set an explicit name and smaller crawl cap:

```bash
mentor https://example.com/guide/ \
  --name example-guide-3.2 \
  --max-pages 100 \
  --delay 1.0 \
  --output ./skills
```

Run quietly in automation:

```bash
mentor https://example.com/docs/ --quiet --zip
```

## Error handling and troubleshooting

- Individual page failures are reported and skipped; they do not abort the
  entire crawl when other pages can be converted.
- If `robots.txt` blocks the start URL, Mentor exits before crawling.
- If `--skip-scrape` finds no cache, Mentor falls back to a normal crawl with a
  warning.
- If a JavaScript shell is detected without Playwright, install the optional
  browser dependencies.
- If automatic content extraction includes navigation or misses the article,
  set `content_selector` in a config file.
- If discovery selects the wrong sidebar, set `nav_selector`, `include`, or
  `exclude`.
- Use the default progress output to identify which URL or discovery phase is
  slow. Add `--quiet` only when logs are not wanted.

## Security and privacy

- Mentor does not require or store credentials for normal deterministic crawls.
- API keys must be supplied through environment variables; do not put them in
  configuration files or commit them to Git.
- Raw HTML caches remain outside generated skills and ZIP archives.
- Generated ZIPs explicitly exclude cache directories and macOS metadata.
- Crawled documentation may still contain proprietary or sensitive content.
  Inspect generated references before publishing or uploading them.
- Only crawl sites you are authorized to access, and respect their terms and
  `robots.txt` policies.

## Development

Install development dependencies and run the test suite:

```bash
python -m pip install -e ".[dev]"
pytest -q
```

The suite covers discovery, URL scope, robots rules, caching, conversion,
navigation hierarchy, metadata generation, assembly, ZIP hygiene, progress
reporting, Python 3.9 compatibility, and CLI end-to-end flows.
