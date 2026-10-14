# Development and Deployment

This guide covers development, testing, and deployment for FileSqueeze maintainers.

## Development

### Dev Mode Isolation

FileSqueeze automatically detects when running in development/testing mode and **isolates itself from production installations**. This allows you to develop and test FileSqueeze on the same machine where it runs in production.

**Dev Mode Detection:**
- Running inside `pytest` (automatic)
- Environment variable `FILEQUEEZE_DEV_MODE=1` (manual)

**Dev Mode Invariants:**
- ✅ **Different mutex**: Uses `Global\\FileSqueeze_DevInstance_Mutex` instead of production mutex
- ✅ **No user config**: Skips loading `~/.config/filesqueeze/config.toml`
- ✅ **Safe directories**: Uses `./dev_test_data/` instead of user directories
- ✅ **Isolated logs**: Logs to `./dev_test_data/filesqueeze_dev.log`
- ✅ **Gitignored**: All dev data is excluded from version control

**Directory Layout:**
```
filesqueeze/
├── dev_test_data/          # Created automatically, gitignored
│   ├── input/              # Test input files
│   ├── output/             # Test compressed files
│   ├── archive/            # Test archived originals
│   └── filesqueeze_dev.log # Dev mode logs
├── filesqueeze.dev.toml    # Optional dev config (gitignored)
└── filesqueeze.toml        # Production config (gitignored)
```

**Benefits:**
- 🚀 **Develop alongside production**: No need to stop production FileSqueeze
- 🧪 **Isolated testing**: Tests use separate data and state
- 🛡️ **Safe defaults**: Can't accidentally modify production data
- 🔄 **Easy workflow**: Just run `pytest` and everything is isolated

### Testing

Run all tests:

```bash
# Run all tests (automatically uses dev mode)
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/integration/test_handlers.py

# Run tests without GUI/Service tests (for CI environments)
poetry run pytest tests/integration/ -v --ignore=tests/integration/test_gui_behavior.py --ignore=tests/integration/test_service.py --ignore=tests/integration/test_single_instance.py
```

### Manual Dev Mode

For manual testing outside of pytest:

```bash
# Set dev mode environment variable
export FILEQUEEZE_DEV_MODE=1

# Run FileSqueeze (will use dev mode)
python -m filesqueeze service

# Or create custom dev config
cat > filesqueeze.dev.toml << 'EOF'
[directories]
input = "./dev_test_data/input"
output = "./dev_test_data/output"

[logging]
file = "./dev_test_data/filesqueeze_dev.log"
EOF
```

See [plans/filesqueeze-implementation-plan.md](../plans/filesqueeze-implementation-plan.md) for implementation details.

See [FILE-LAYOUT.md](FILE-LAYOUT.md) for detailed information about file locations during installation.

---

## Deployment (For Maintainers)

FileSqueeze is distributed from this repository only — there is no PyPI
package and no separately hosted installer. The canonical install is a
clone of the repo, a checkout of the release tag, and the installer script
(see the README's Installation section).

### Publishing a Release

Releases follow the hard rules in [RELEASING.md](RELEASING.md) — the
short version:

1. `main`'s `pyproject.toml` declares the version the release will carry
   (at least a patch above anything ever published).
2. Merge the change; then tag the **merge commit** (not the branch tip):
   `git tag vX.Y.Z <full-merge-sha>`.
3. Build the wheel from that exact commit (`poetry build`) — the tag and
   the wheel name/version must match, because the in-app updater verifies
   both before installing.
4. Publish a **full (non-prerelease)** GitHub release with
   `filesqueeze-X.Y.Z-py3-none-any.whl` attached (prereleases are
   invisible to the updater).
5. Verify live: `/releases/latest` serves the new tag, the wheel asset
   resolves, and a simulated older client's update check returns the new
   version with a wheel URL.

### Deployment Checklist

- [ ] Test installer on fresh Windows machine
- [ ] Test installer on fresh Linux machine
- [ ] Create GitHub release with the wheel attached (no PyPI — FileSqueeze is not published there)
- [ ] Test installation from the release wheel: `python -m pip install --force-reinstall "<wheel-url>"`
- [ ] Verify a v-1 client sees the update (see RELEASING.md step 5)
