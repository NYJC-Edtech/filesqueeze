# FileSqueeze Testing Guidelines

## Golden Rule

**NEVER modify production state during tests.**

This includes:
- User config files (`~/.config/filesqueeze/config.toml`)
- User data directories
- System-wide settings
- Any files outside the test temp directory

## Test Safety Mechanisms

### Automatic Protection

The `tests/conftest.py` file includes automatic protection that patches `Path.write_text()` and `Path.write_bytes()` to prevent tests from writing to protected paths:

**Protected Paths**:
- `~/.config/filesqueeze/config.toml`
- `./filesqueeze.toml` (in project root)

**If a test tries to write to these paths**, it will fail immediately with:
```
TEST SAFETY VIOLATION: Attempted to write to protected config file!
```

## Using tmp_path Fixture

**Always use the `tmp_path` fixture for test-specific files:**

```python
def test_something(tmp_path):
    # Create test config in temp directory
    config_file = tmp_path / 'test_config.toml'
    config_file.write_text('[test]\nkey = "value"')

    # Use the test config
    config = Config(config_path=config_file)

    # Test logic here
    assert config.get('test.key') == 'value'
```

## Test Structure

### Unit Tests

Test individual functions and classes in isolation:

```python
class TestVideoCompression:
    def test_compress_without_ffmpeg(self, tmp_path):
        """Test that compress raises error without FFmpeg."""
        from filesqueeze.ops.video import compress

        input_file = tmp_path / "input.mp4"
        input_file.write_bytes(b"fake video")

        output_file = tmp_path / "output.mp4"

        with pytest.raises(RuntimeError):
            compress(str(input_file), str(output_file))
```

### Integration Tests

Test multiple components working together:

```python
class TestRealFileCompression:
    def test_compress_video(self, sample_video, tmp_path):
        """Test actual video compression."""
        from filesqueeze.ops.video import compress

        output_path = tmp_path / "compressed.mp4"

        # Compress
        compress(sample_video, str(output_path))

        # Verify output exists and is valid
        assert output_path.exists()
        assert output_path.stat().st_size > 0
```

### Regression Tests

Establish baseline behavior before refactoring, verify no regressions after:

```python
class TestBehavioralRegression:
    def test_video_compression_regression(self, baseline_data):
        """Verify video compression matches baseline."""
        # Load baseline
        baseline = load_baseline('video_compression')

        # Run compression
        result = compress_video(...)

        # Compare with baseline
        assert result['compression_ratio'] >= baseline['min_ratio']
```

## Configuration in Tests

### Safe Config Patterns

**✅ DO: Use tmp_path for config files**
```python
def test_with_custom_config(tmp_path):
    config_file = tmp_path / 'config.toml'
    config_file.write_text('[ffmpeg]\ncrf = 25\n')
    config = Config(config_path=config_file)
```

**✅ DO: Use dict for inline config**
```python
def test_with_dict_config():
    config = Config({'ffmpeg': {'crf': 25}})
    assert config.get('ffmpeg.crf') == 25
```

**✅ DO: Use default config (no args)**
```python
def test_with_defaults():
    config = Config()  # Loads from default.toml
    assert config.get('ffmpeg.crf') is not None
```

**❌ DON'T: Write to actual user config**
```python
def test_bad_example():
    # This will FAIL with safety violation!
    user_config = Path.home() / '.config' / 'filesqueeze' / 'config.toml'
    user_config.write_text('[test]\n')  # ❌ TEST SAFETY VIOLATION!
```

## Test Fixtures

### Sample Files

Use fixtures for sample test files:

```python
@pytest.fixture
def sample_video():
    """Path to sample video file for testing."""
    video_path = FIXTURES_DIR / "testvideo61.mp4"
    if video_path.exists():
        return str(video_path)
    pytest.skip("Sample video not found")
```

### Mock Config

Create mock config for testing:

```python
@pytest.fixture
def mock_config(tmp_path):
    """Create a mock config for testing."""
    config_file = tmp_path / 'test_config.toml'
    config_file.write_text('''
        [ffmpeg]
        crf = 25
        preset = "medium"

        [document]
        image_quality = 85
    ''')
    return Config(config_path=config_file)
```

## Test Isolation

Each test should be independent:

```python
@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state before each test."""
    # Reset logger
    from filesqueeze.system import logger as logger_module
    logger_module._logger = None

    # Reset binary finder
    from filesqueeze.system import binaries as binaries_module
    binaries_module._binary_finder = None

    yield

    # Cleanup after test
    logger_module._logger = None
    binaries_module._binary_finder = None
```

## Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_video_config_validation():
    """Unit test for video config validation."""

@pytest.mark.integration
def test_real_video_compression():
    """Integration test with actual FFmpeg."""

@pytest.mark.regression
def test_behavioral_baseline():
    """Regression test for behavior verification."""
```

Run specific categories:
```bash
pytest -m unit           # Run only unit tests
pytest -m integration    # Run only integration tests
pytest -m "not regression"  # Skip regression tests
```

## Common Test Patterns

### Testing Error Conditions

```python
def test_invalid_crf_raises_error():
    """Test that invalid CRF value raises error."""
    from filesqueeze.system.config_adapters import VideoConfig

    with pytest.raises(ValueError, match="CRF must be 0-51"):
        VideoConfig({'crf': -1})
```

### Testing with Missing Binaries

```python
def test_compress_without_ffmpeg(tmp_path):
    """Test compress raises error when FFmpeg missing."""
    from filesqueeze.ops.video import compress

    # Skip if FFmpeg is installed
    if shutil.which('ffmpeg'):
        pytest.skip("FFmpeg installed, cannot test missing binary")

    # Test error handling
    input_file = tmp_path / "input.mp4"
    input_file.write_bytes(b"fake video")

    with pytest.raises(RuntimeError):
        compress(str(input_file), str(tmp_path / "output.mp4"))
```

### Testing Config Loading

```python
def test_config_cascade(tmp_path):
    """Test that project config overrides user config."""
    # Create user config
    user_config = tmp_path / 'user.toml'
    user_config.write_text('[ffmpeg]\ncrf = 25\n')

    # Create project config
    project_config = tmp_path / 'project.toml'
    project_config.write_text('[ffmpeg]\ncrf = 23\n')

    # Load project config (should override user)
    config = Config(config_path=project_config)
    assert config.get('ffmpeg.crf') == 23  # Project wins
```

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test File
```bash
pytest tests/test_video.py
```

### Run with Verbose Output
```bash
pytest tests/ -v
```

### Run and Stop on First Failure
```bash
pytest tests/ -x
```

### Run with Coverage
```bash
pytest tests/ --cov=filesqueeze --cov-report=html
```

## Static Checking with Ruff

Static checking complements runtime testing by catching issues before code execution. Our project uses Ruff for both linting and type checking.

### Enhanced Static Type Checking

We've enhanced our Ruff configuration to catch more issues:

```toml
[tool.ruff.lint.select = [
    "E",   # pycodestyle errors (syntax errors)
    "F",   # pyflakes (undefined names, unused imports)
    "W",   # pycodestyle warnings (dangerous patterns)
    "I",   # isort (import sorting)
    "B",   # flake8-bugbear (common bugs)
    "C4",  # flake8-comprehensions (unnecessary comprehensions)
    "UP",  # pyupgrade (modernize Python syntax)
    "ANN", # flake8-annotations (type annotations)
    "RUF", # Ruff-specific rules
]
```

### Running Static Checks

```bash
# Check for all issues
ruff check .

# Check for type annotation issues only
ruff check . --select ANN

# Auto-fix issues where possible
ruff check . --fix

# Check specific files
ruff check filesqueeze/handlers.py
```

### Code Formatting with Ruff

Our project uses Ruff for both linting and formatting (replacing Black):

```bash
# Format all Python files
ruff format .

# Check formatting without making changes
ruff format --check .

# Format specific files
ruff format filesqueeze/handlers.py

# Format and check in one command
ruff format . && ruff check .
```

**Why Ruff format?**
- **10-100x faster** than Black
- **Compatible configuration** - matches Black's default style
- **All-in-one tool** - single dependency for linting and formatting
- **Active development** - rapid improvements and new features

### Git Hooks

Our project includes automated git hooks for code quality:

#### Pre-commit Hook
Runs automatically before each commit:
1. **Ruff formatting** (`ruff format .`) - Auto-formats all code
2. **Ruff type checking** (`ruff check . --select ANN`)
3. **Smoke tests** (`pytest tests/smoke/ -q`)

If any check fails, the commit is rejected with helpful error messages.

#### Post-edit Hook
Automatically formats Python files after editing:
- **Auto-formats** with `ruff format` when you save a `.py` file
- **Zero friction** - no manual formatting commands needed

#### Pre-push Hook
Runs automatically before each push:
- **Poetry lockfile sync check** (`poetry lock --check`)
- Prevents pushing desynchronized lockfiles that cause dependency issues

If the lockfile is out of sync, the push is rejected with instructions to fix it.

**Installing Git Hooks:**
```bash
# Linux/macOS
bash .githooks/install.sh

# Windows PowerShell
powershell -ExecutionPolicy Bypass -File .githooks\install.ps1
```

**Manual Hook Testing:**
```bash
# Test pre-commit checks
ruff check . --select ANN
pytest tests/smoke/ -v

# Test formatting
ruff format . --check  # Check if formatting needed
ruff format .          # Apply formatting

# Test poetry lockfile sync
poetry lock --check    # Should pass if lockfile is current
poetry lock           # Update lockfile if needed
```

### Case Study: State Class Error Prevention

A recent bug occurred when code tried to directly assign to `state.status`:
```python
state.status = "Error during file analysis"  # WRONG - causes AttributeError
```

The `State` class uses `__slots__` and doesn't support direct attribute assignment. We fixed this through:

1. **Better Error Messages**: The State class now has a custom `__setattr__` that provides clear guidance
2. **Type Annotations**: All methods now have proper type hints
3. **API Documentation**: Clear warnings in docstrings about correct usage

### Best Practices for Static Checking

#### 1. Always Use State Methods
```python
# ❌ WRONG
state.status = "Error"
state.metadata["key"] = "value"

# ✅ CORRECT
state.error("Error message")
# metadata is accessed via property, not modified directly
```

#### 2. Add Type Annotations
```python
# ❌ WRONG
def process(state):
    state.status_analyze()

# ✅ CORRECT
def process(state: State) -> None:
    state.status_analyze()
```

#### 3. Run Static Checks Before Committing
```bash
# Make it part of your development workflow
ruff format . && ruff check .
```

### Benefits of Static Checking

- **Early Error Detection**: Catches issues at code-writing time, not runtime
- **Better IDE Support**: Type annotations enable autocomplete and inline documentation
- **Code Quality**: Enforces consistent style and catches common bugs
- **API Clarity**: Type hints serve as documentation for function signatures

## Debugging Tests

### Print Debug Info
```python
def test_with_debug(tmp_path):
    config_file = tmp_path / 'config.toml'
    config_file.write_text('[test]\nkey = "value"')

    # Debug: print what was written
    print(f"Config file: {config_file}")
    print(f"Content: {config_file.read_text()}")

    config = Config(config_path=config_file)
    assert config.get('test.key') == 'value'
```

### Use pdb Debugger
```python
def test_with_breakpoint():
    import pdb; pdb.set_trace()

    # Test will stop here for debugging
    result = some_function()
    assert result == expected
```

### Run with pdb on Failure
```bash
pytest tests/ --pdb
```

## Test Cleanup

### Cleanup After Tests

```python
def test_with_cleanup(tmp_path):
    """Test that cleans up resources."""
    log_file = tmp_path / 'test.log'
    logger = setup_logging(log_file=log_file)

    try:
        # Test code here
        logger.info("Test message")
    finally:
        # Always cleanup
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
```

## Best Practices

### 1. Use Descriptive Test Names
```python
# ✅ Good
def test_compress_video_raises_error_when_ffmpeg_missing():

# ❌ Bad
def test_video_1():
```

### 2. Test One Thing Per Test
```python
# ✅ Good - one assertion
def test_crf_validation_accepts_valid_range():
    config = VideoConfig({'crf': 23})
    assert config.crf == 23

# ❌ Bad - multiple unrelated assertions
def test_video_config():
    config = VideoConfig({'crf': 23})
    assert config.crf == 23
    assert config.preset == "medium"  # Different concern
    assert config.threads == 4  # Different concern
```

### 3. Use Fixtures for Setup
```python
# ✅ Good - reusable fixture
@pytest.fixture
def video_config():
    return VideoConfig({'crf': 23, 'preset': 'medium'})

def test_with_fixture(video_config):
    assert video_config.crf == 23

# ❌ Bad - duplicated setup
def test_without_fixture():
    config = VideoConfig({'crf': 23, 'preset': 'medium'})
    assert config.crf == 23
```

### 4. Make Tests Independent
```python
# ✅ Good - independent
def test_feature_a(tmp_path):
    file_a = tmp_path / 'a.txt'
    file_a.write_text('content a')

def test_feature_b(tmp_path):
    file_b = tmp_path / 'b.txt'
    file_b.write_text('content b')

# ❌ Bad - tests share state
shared_state = []

def test_feature_a():
    shared_state.append('a')

def test_feature_b():
    shared_state.append('b')  # Depends on test_a running first
```

## Safety Checklist

Before committing a test, verify:

- [ ] Test uses `tmp_path` for all file operations
- [ ] Test does NOT write to `~/.config/filesqueeze/`
- [ ] Test does NOT write to project root `filesqueeze.toml`
- [ ] Test cleans up its own resources (if needed)
- [ ] Test is independent (can run alone)
- [ ] Test has descriptive name explaining what it tests
- [ ] Test follows AAA pattern (Arrange, Act, Assert)
- [ ] Code passes static checks: `ruff check .`

## Troubleshooting

### Test Fails with "TEST SAFETY VIOLATION"

**Problem**: Test tried to write to protected config path.

**Solution**: Use `tmp_path` fixture instead:

```python
# ❌ Wrong
def test_bad():
    config_path = Path.home() / '.config' / 'filesqueeze' / 'config.toml'
    config_path.write_text('content')

# ✅ Correct
def test_good(tmp_path):
    config_path = tmp_path / 'config.toml'
    config_path.write_text('content')
```

### Tests Pass in Isolation but Fail in Suite

**Problem**: Tests are sharing state or not cleaning up properly.

**Solution**: Ensure each test cleans up after itself. Use fixtures for setup/teardown.

### Tests are Slow

**Problem**: Tests doing unnecessary I/O or setup.

**Solution**:
- Mock expensive operations
- Use fixtures to share setup
- Only test what's necessary

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [pytest markers](https://docs.pytest.org/en/stable/mark.html)
- [Ruff documentation](https://docs.astral.sh/ruff/)

## Future Improvements

1. **Pre-commit Hooks**: Add Ruff to git hooks to catch issues before commit
2. **CI Integration**: Run Ruff in CI to enforce code quality
3. **Strict Mode**: Consider enabling more strict Ruff rules over time
4. **Type Stub Files**: Add `.pyi` files for better type checking of complex modules
5. **Coverage Targets**: Set minimum coverage thresholds for CI/CD
