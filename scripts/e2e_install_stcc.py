"""E2E: install the pinned stcc package into the default binaries dir."""

from pathlib import Path

from filesqueeze.deps_setup import run_setup

base = Path.home() / "FileSqueeze" / "bin"
base.mkdir(parents=True, exist_ok=True)
print("binaries dir:", base)
report = run_setup(base_dir=base, requested={"stcc"}, assume_yes=True)
print("EXIT-REACHED")
print("\n".join(report.summary_lines()))
print("config written:", report.config_written)
