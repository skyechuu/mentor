import zipfile

import pytest

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
    (skill / "references" / "__MACOSX").mkdir()
    (skill / "references" / "__MACOSX" / "._page.md").write_text(
        "metadata", encoding="utf-8"
    )
    (skill / ".mentor-cache").mkdir()
    (skill / ".mentor-cache" / "raw.html").write_text("raw", encoding="utf-8")
    archive_path = zip_skill_folder(skill)
    first = archive_path.read_bytes()
    zip_skill_folder(skill)
    assert archive_path.read_bytes() == first
    with zipfile.ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == {"SKILL.md", "references/page.md"}
    assert not archive_path.with_name(f".{archive_path.name}.tmp").exists()


def test_zip_is_published_only_after_success(tmp_path, monkeypatch):
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("skill", encoding="utf-8")
    archive_path = skill.with_suffix(".zip")
    archive_path.write_bytes(b"previous-valid-archive")

    def fail_write(_self, *_args, **_kwargs):
        raise RuntimeError("compression failed")

    monkeypatch.setattr(zipfile.ZipFile, "writestr", fail_write)
    with pytest.raises(RuntimeError, match="compression failed"):
        zip_skill_folder(skill)

    assert archive_path.read_bytes() == b"previous-valid-archive"
    assert not archive_path.with_name(f".{archive_path.name}.tmp").exists()
