import subprocess
import sys
from pathlib import Path

from doctoskill.types import ConvertedPage

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_module_help_runs():
    result = subprocess.run(
        [sys.executable, "-m", "doctoskill", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "start_url" in result.stdout


def test_converted_page_defaults():
    page = ConvertedPage("Intro", "# Intro", ["guide"])
    assert page.url is None
