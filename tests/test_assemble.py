from doctoskill.assemble import assemble_skill
from doctoskill.types import ConvertedPage


def test_assemble_writes_router_references_and_handles_collisions(tmp_path):
    skill_dir = assemble_skill(
        tmp_path,
        "example-skill",
        "Example documentation",
        "Use these docs.",
        [
            ConvertedPage("Intro", "# Intro", []),
            ConvertedPage("Intro", "# Second intro", []),
            ConvertedPage("Install", "# Install", ["Getting Started"]),
        ],
    )
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "references" / "intro.md").exists()
    assert (skill_dir / "references" / "intro-2.md").exists()
    assert (skill_dir / "references" / "getting-started" / "install.md").exists()
    router = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "name: example-skill" in router
    assert "references/getting-started/install.md" in router


def test_assemble_removes_stale_references(tmp_path):
    skill = assemble_skill(tmp_path, "skill", "D", "O", [ConvertedPage("Old", "old", [])])
    assert (skill / "references" / "old.md").exists()
    assemble_skill(tmp_path, "skill", "D", "O", [ConvertedPage("New", "new", [])])
    assert not (skill / "references" / "old.md").exists()


def test_assemble_removes_legacy_cache_and_macos_junk(tmp_path):
    skill = tmp_path / "skill"
    (skill / ".cache").mkdir(parents=True)
    (skill / ".cache" / "raw.html").write_text("raw", encoding="utf-8")
    (skill / "__MACOSX").mkdir()
    (skill / "__MACOSX" / "._SKILL.md").write_text("junk", encoding="utf-8")
    (skill / ".DS_Store").write_text("junk", encoding="utf-8")
    assemble_skill(tmp_path, "skill", "D", "O", [ConvertedPage("New", "new", [])])
    assert not (skill / ".cache").exists()
    assert not (skill / "__MACOSX").exists()
    assert not (skill / ".DS_Store").exists()
