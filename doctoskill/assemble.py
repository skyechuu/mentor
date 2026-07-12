import shutil
from pathlib import Path

from doctoskill.skillmd import render_skill_md
from doctoskill.slugify import slugify
from doctoskill.types import ConvertedPage

JUNK_DIRECTORY_NAMES = {".cache", "__MACOSX"}


def _remove_packaging_junk(skill_dir: Path) -> None:
    for directory_name in JUNK_DIRECTORY_NAMES:
        for directory in skill_dir.rglob(directory_name):
            if directory.is_dir():
                shutil.rmtree(directory)
    for file_path in skill_dir.rglob("*"):
        if file_path.is_file() and (file_path.name == ".DS_Store" or file_path.name.startswith("._")):
            file_path.unlink()


def _unique_relative_path(
    page: ConvertedPage,
    used: set[str],
) -> str:
    directory = [slugify(segment) for segment in page.path_segments]
    stem = slugify(page.title)
    candidate = "/".join(["references", *directory, f"{stem}.md"])
    counter = 2
    while candidate in used:
        candidate = "/".join(["references", *directory, f"{stem}-{counter}.md"])
        counter += 1
    used.add(candidate)
    return candidate


def assemble_skill(
    output_dir,
    skill_name: str,
    description: str,
    overview: str,
    pages: list[ConvertedPage],
) -> Path:
    skill_dir = Path(output_dir) / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    _remove_packaging_junk(skill_dir)
    references_dir = skill_dir / "references"
    if references_dir.exists():
        shutil.rmtree(references_dir)
    references_dir.mkdir(parents=True, exist_ok=True)

    used: set[str] = set()
    index_entries: list[tuple[str, str]] = []
    for page in pages:
        relative_path = _unique_relative_path(page, used)
        file_path = skill_dir / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(page.markdown.rstrip() + "\n", encoding="utf-8")
        index_entries.append((page.title, relative_path))

    skill_md = render_skill_md(skill_name, description, overview, index_entries)
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
    return skill_dir
