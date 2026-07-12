# DocToSkill

DocToSkill crawls a documentation website and converts it into a portable Agent
Skill: one `SKILL.md` router plus progressively disclosed Markdown files under
`references/`. The default pipeline is deterministic and does not require an API
key.

## Install

DocToSkill requires Python 3.9 or newer.

```bash
python3 -m pip install -e .
```

Install optional browser rendering or LLM enhancement support with:

```bash
python3 -m pip install -e '.[playwright,enhance]'
playwright install chromium
```

## Use

```bash
python3 -m doctoskill https://docs.example.com/manual/index.html \
  --output ./skills \
  --name example-manual \
  --zip
```

Run `python3 -m doctoskill --help` for all options. Discovery tries `llms-full.txt`
or `llms.txt`, a DocFX or generic navigation tree, `sitemap.xml`, and finally a
same-path breadth-first crawl. Raw HTML is cached inside the generated skill's
cache outside the generated output under a sibling `.doctoskill-cache/` directory;
use `--skip-scrape` for an offline conversion rerun. Generated skill folders and
ZIP archives never contain crawl caches, `.DS_Store`, `._*`, or `__MACOSX` files.

Progress is printed to stderr throughout discovery, crawling, conversion, and
packaging so long runs remain visibly active. Pass `--quiet` to suppress these
messages in scripts while keeping warnings, errors, and the final summary.

For sites with unusual markup, pass a JSON config:

```json
{
  "include": ["/docs/"],
  "exclude": ["/docs/changelog/"],
  "content_selector": "main.article-content",
  "nav_selector": "nav.sidebar"
}
```
