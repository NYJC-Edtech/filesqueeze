"""Unit tests for init-config output-path resolution and safeguards.

init-config always defaults to the user config (~/.config/filesqueeze/
config.toml) — the only location the app reads regardless of working
directory, and the only one a source-zip "install" can rely on. Devs who
want a project config pass --output explicitly. Explicitly pointing
--output at the user config still requires --user-config.
"""

import argparse
from pathlib import Path


def _fake_home(monkeypatch, tmp_path):
    """Point Path.home() at tmp_path so 'user config' is a safe fake."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path / ".config" / "filesqueeze" / "config.toml"


def test_default_output_is_user_config(monkeypatch, tmp_path):
    """The default output is the user config, everywhere."""
    from filesqueeze.cli import default_config_output

    fake_user_config = _fake_home(monkeypatch, tmp_path)

    assert default_config_output() == fake_user_config


def test_explicit_user_config_output_requires_flag(monkeypatch, tmp_path):
    """Explicitly pointing --output at the user config without --user-config exits."""
    import pytest

    from filesqueeze.cli import cmd_init_config

    fake_user_config = _fake_home(monkeypatch, tmp_path)
    fake_user_config.parent.mkdir(parents=True)
    fake_user_config.write_text("# existing user settings\n")

    args = argparse.Namespace(output=str(fake_user_config), force=True, user_config=False)

    with pytest.raises(SystemExit) as excinfo:
        cmd_init_config(args)
    assert excinfo.value.code == 1
    # Guard must fire before anything is written or backed up
    assert fake_user_config.read_text() == "# existing user settings\n"


def test_default_targets_user_config_and_requires_force_when_existing(monkeypatch, tmp_path):
    """The default (no --output) may write the user config.

    The --user-config safeguard only guards explicit --output paths; the
    default targets the user config deliberately, while an existing file
    there still requires --force.
    """
    import pytest

    from filesqueeze.cli import cmd_init_config

    fake_user_config = _fake_home(monkeypatch, tmp_path)

    args = argparse.Namespace(output=None, force=False, user_config=False)

    cmd_init_config(args)  # no SystemExit from the guard, file is created
    assert fake_user_config.exists()

    # Existing user config is protected: without --force, init-config refuses
    args = argparse.Namespace(output=None, force=False, user_config=False)
    with pytest.raises(SystemExit) as excinfo:
        cmd_init_config(args)
    assert excinfo.value.code == 1
