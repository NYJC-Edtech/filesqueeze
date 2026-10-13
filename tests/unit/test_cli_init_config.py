"""Unit tests for init-config output-path resolution and safeguards.

init-config picks its default output by install context: a dev checkout
writes ./filesqueeze.toml (project config), an installed copy writes the
user config (~/.config/filesqueeze/config.toml), the only location the
app reads regardless of working directory. Explicitly pointing --output
at the user config still requires --user-config.
"""

import argparse
from pathlib import Path


def _fake_home(monkeypatch, tmp_path):
    """Point Path.home() at tmp_path so 'user config' is a safe fake."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path / ".config" / "filesqueeze" / "config.toml"


def test_installed_copy_defaults_to_user_config(monkeypatch, tmp_path):
    """Outside a dev checkout, the default output is the user config."""
    import filesqueeze.update_check as update_check
    from filesqueeze.cli import default_config_output

    fake_user_config = _fake_home(monkeypatch, tmp_path)
    monkeypatch.setattr(update_check, "is_dev_checkout", lambda: False)

    assert default_config_output() == fake_user_config


def test_dev_checkout_defaults_to_project_config(monkeypatch, tmp_path):
    """In a dev checkout, the default output is ./filesqueeze.toml."""
    import filesqueeze.update_check as update_check
    from filesqueeze.cli import default_config_output

    _fake_home(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(update_check, "is_dev_checkout", lambda: True)

    assert default_config_output() == tmp_path / "filesqueeze.toml"


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


def test_installed_default_targets_user_config_with_flag_semantics(monkeypatch, tmp_path):
    """Installed-copy default (no --output) may write the user config.

    The --user-config safeguard only guards explicit --output paths; the
    installed default targets the user config deliberately, while an
    existing file there still requires --force.
    """
    import filesqueeze.update_check as update_check
    from filesqueeze.cli import cmd_init_config

    fake_user_config = _fake_home(monkeypatch, tmp_path)
    # Simulate an installed copy: under pytest we are in a dev checkout,
    # whose default would be ./filesqueeze.toml (a protected path).
    monkeypatch.setattr(update_check, "is_dev_checkout", lambda: False)

    args = argparse.Namespace(output=None, force=False, user_config=False)

    cmd_init_config(args)  # no SystemExit from the guard, file is created
    assert fake_user_config.exists()

    # Existing user config is protected: without --force, init-config refuses
    import pytest

    args = argparse.Namespace(output=None, force=False, user_config=False)
    with pytest.raises(SystemExit) as excinfo:
        cmd_init_config(args)
    assert excinfo.value.code == 1
