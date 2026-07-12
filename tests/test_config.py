import json

import pytest

from doctoskill.config import OverrideConfig, load_config


def test_config_defaults_and_partial_file(tmp_path):
    assert load_config(None) == OverrideConfig()
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"content_selector": "main"}), encoding="utf-8")
    assert load_config(str(path)) == OverrideConfig(content_selector="main")


def test_config_validates_types(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"include": "/docs/"}), encoding="utf-8")
    with pytest.raises(ValueError, match="list of strings"):
        load_config(str(path))
