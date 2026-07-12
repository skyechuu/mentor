import zipfile
from pathlib import Path

ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
JUNK_DIRECTORY_NAMES = {".cache", "__MACOSX"}


def _is_packaging_junk(relative_path: Path) -> bool:
    return (
        any(part in JUNK_DIRECTORY_NAMES for part in relative_path.parts)
        or relative_path.name == ".DS_Store"
        or relative_path.name.startswith("._")
    )


def zip_skill_folder(skill_dir, zip_path=None) -> Path:
    """Create a deterministic zip with skill contents at the archive root."""
    skill_dir = Path(skill_dir)
    zip_path = Path(zip_path) if zip_path else skill_dir.with_suffix(".zip")
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(skill_dir.rglob("*")):
            relative = file_path.relative_to(skill_dir)
            if _is_packaging_junk(relative) or not file_path.is_file():
                continue
            info = zipfile.ZipInfo(relative.as_posix(), ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, file_path.read_bytes())
    return zip_path
