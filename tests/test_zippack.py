import zipfile

from doctoskill.zippack import zip_skill_folder


def test_zip_excludes_cache_and_is_deterministic(tmp_path):
    skill = tmp_path / "skill"
    (skill / "references").mkdir(parents=True)
    (skill / ".cache").mkdir()
    (skill / "SKILL.md").write_text("skill", encoding="utf-8")
    (skill / "references" / "page.md").write_text("page", encoding="utf-8")
    (skill / ".cache" / "page.html").write_text("raw", encoding="utf-8")
    (skill / "__MACOSX").mkdir()
    (skill / "__MACOSX" / "._SKILL.md").write_text("metadata", encoding="utf-8")
    (skill / "._SKILL.md").write_text("metadata", encoding="utf-8")
    (skill / ".DS_Store").write_text("metadata", encoding="utf-8")
    archive_path = zip_skill_folder(skill)
    first = archive_path.read_bytes()
    zip_skill_folder(skill)
    assert archive_path.read_bytes() == first
    with zipfile.ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == {"SKILL.md", "references/page.md"}
