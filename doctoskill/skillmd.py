import re


def _yaml_scalar(value: str) -> str:
    if value and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._/@()+-]*", value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def render_skill_md(
    name: str,
    description: str,
    overview: str,
    index_entries: list[tuple[str, str]],
) -> str:
    frontmatter = (
        "---\n"
        f"name: {_yaml_scalar(name)}\n"
        f"description: {_yaml_scalar(description)}\n"
        "---\n\n"
    )
    body = f"# {name}\n\n{overview.strip()}\n\n## Reference Index\n\n"
    for title, relative_path in index_entries:
        body += f"- [{title}]({relative_path})\n"
    return frontmatter + body
