import os
import zipfile
from pathlib import Path

ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
JUNK_DIRECTORY_NAMES = {
    ".cache",
    ".doctoskill-cache",
    ".mentor-cache",
    "__MACOSX",
}


def _is_packaging_junk(relative_path: Path) -> bool:
    return (
        any(part in JUNK_DIRECTORY_NAMES for part in relative_path.parts)
        or relative_path.name == ".DS_Store"
        or relative_path.name.startswith("._")
    )


def zip_skill_folder(skill_dir, zip_path=None) -> Path:
    """Atomically publish a deterministic, macOS-junk-free skill archive."""
    skill_dir = Path(skill_dir)
    if not skill_dir.is_dir():
        raise FileNotFoundError(f"skill directory does not exist: {skill_dir}")
    zip_path = Path(zip_path) if zip_path else skill_dir.with_suffix(".zip")
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = zip_path.with_name(f".{zip_path.name}.tmp")

    try:
        with zipfile.ZipFile(temporary_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for root, directories, filenames in os.walk(skill_dir, followlinks=False):
                root_path = Path(root)
                directories[:] = sorted(
                    directory
                    for directory in directories
                    if directory not in JUNK_DIRECTORY_NAMES
                    and not (root_path / directory).is_symlink()
                )
                for filename in sorted(filenames):
                    file_path = root_path / filename
                    relative = file_path.relative_to(skill_dir)
                    if (
                        _is_packaging_junk(relative)
                        or file_path.is_symlink()
                        or file_path in {temporary_path, zip_path}
                    ):
                        continue
                    info = zipfile.ZipInfo(relative.as_posix(), ZIP_TIMESTAMP)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.create_system = 3
                    info.external_attr = 0o644 << 16
                    archive.writestr(info, file_path.read_bytes())
        temporary_path.replace(zip_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return zip_path
