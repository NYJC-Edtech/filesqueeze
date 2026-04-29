# Development and Deployment

This guide covers development, testing, and deployment for FileSqueeze maintainers.

## Development

### Testing

Run all tests:

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/integration/test_handlers.py

# Run tests without GUI/Service tests (for CI environments)
poetry run pytest tests/integration/ -v --ignore=tests/integration/test_gui_behavior.py --ignore=tests/integration/test_service.py --ignore=tests/integration/test_single_instance.py
```

See [plans/filesqueeze-implementation-plan.md](../plans/filesqueeze-implementation-plan.md) for implementation details.

See [FILE-LAYOUT.md](FILE-LAYOUT.md) for detailed information about file locations during installation.

---

## Deployment (For Maintainers)

If you're maintaining FileSqueeze and need to deploy the installation system:

### 1. Update Repository URLs

Replace placeholder URLs in install scripts:

**In `install.ps1` (line 11):**
```powershell
[string]$RepoUrl = "https://github.com/YOUR_USERNAME/filesqueeze.git"
```

**In `install.sh` (line 10):**
```bash
REPO_URL="https://github.com/YOUR_USERNAME/filesqueeze.git"
```

### 2. Host Install Scripts

**Option A: Host on website**
```bash
# Upload install.ps1 and install.sh to:
# https://yourdomain.com/filesqueeze/install
```

**Option B: Use GitHub Raw**
```powershell
# Windows
irm https://raw.githubusercontent.com/USERNAME/filesqueeze/main/install.ps1 | iex

# Linux
curl -sSL https://raw.githubusercontent.com/USERNAME/filesqueeze/main/install.sh | bash
```

**Option C: Use GitHub Gist**
- Create a Gist with install.ps1 and install.sh
- Use Gist raw URL for distribution

### 3. Publish to PyPI

```bash
# Build package
poetry build

# Test on TestPyPI first
poetry publish -r test-pypi

# Publish to PyPI (requires API token)
poetry publish
```

### 4. Create GitHub Release

```bash
# Tag the release
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0

# Create release on GitHub with:
# - Installation instructions
# - Release notes
```

### Deployment Checklist

- [ ] Update repository URLs in install scripts
- [ ] Upload install scripts to web server/GitHub
- [ ] Test installer on fresh Windows machine
- [ ] Test installer on fresh Linux machine
- [ ] Publish to PyPI (or TestPyPI for testing)
- [ ] Create GitHub release
- [ ] Update documentation with actual URLs
- [ ] Test PyPI installation: `pip install filesqueeze`
