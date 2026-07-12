import subprocess
import sys
from pathlib import Path

from doctoskill.types import ConvertedPage

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_mentor_and_legacy_module_help_run():
    for module_name in ("mentor", "doctoskill"):
        result = subprocess.run(
            [sys.executable, "-m", module_name, "--help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage: mentor" in result.stdout
        assert "Teach agents how to do stuff" in result.stdout
        assert "start_url" in result.stdout


def test_mentor_public_version_matches_compatibility_package():
    import mentor
    import doctoskill

    assert mentor.__version__ == doctoskill.__version__ == "0.3.4"


def test_converted_page_defaults():
    page = ConvertedPage("Intro", "# Intro", ["guide"])
    assert page.url is None
