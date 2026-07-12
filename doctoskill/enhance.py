from pathlib import Path

MODEL = "claude-sonnet-4-20250514"
MAX_REFERENCE_FILES = 10
MAX_SNIPPET_CHARS = 2_000


def enhance_skill(skill_dir, client=None) -> None:
    """Optionally rewrite only SKILL.md using representative references."""
    skill_dir = Path(skill_dir)
    skill_md_path = skill_dir / "SKILL.md"
    current_skill_md = skill_md_path.read_text(encoding="utf-8")
    reference_files = sorted((skill_dir / "references").rglob("*.md"))
    if len(reference_files) > MAX_REFERENCE_FILES:
        step = max(1, len(reference_files) // MAX_REFERENCE_FILES)
        reference_files = reference_files[::step][:MAX_REFERENCE_FILES]
    excerpts = [
        f"## {path.relative_to(skill_dir)}\n{path.read_text(encoding='utf-8')[:MAX_SNIPPET_CHARS]}"
        for path in reference_files
    ]

    if client is None:
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "--enhance requires the optional dependency: pip install 'mentor[enhance]'"
            ) from exc
        client = anthropic.Anthropic()

    joined_excerpts = "\n\n---\n\n".join(excerpts)
    prompt = (
        "Rewrite the following SKILL.md to sharpen its overview and description. "
        "Keep only the existing YAML keys (name and description), preserve the exact "
        "Reference Index links, and return only the complete replacement SKILL.md.\n\n"
        f"Current SKILL.md:\n{current_skill_md}\n\n"
        f"Representative reference excerpts:\n{joined_excerpts}"
    )
    message = client.messages.create(
        model=MODEL,
        max_tokens=2_000,
        messages=[{"role": "user", "content": prompt}],
    )
    replacement = message.content[0].text
    if not replacement.startswith("---\n"):
        raise ValueError("Enhancement response was not a valid complete SKILL.md")
    skill_md_path.write_text(replacement, encoding="utf-8")
