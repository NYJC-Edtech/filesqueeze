"""Smoke tests for FileSqueeze.

These tests verify critical system functionality that MUST work for the application
to function at all. These check for show-stopper issues that users cannot fix themselves.

All smoke tests must:
- Run in under 30 seconds total
- Test only critical, unfixable-by-user issues
- Require no external binaries or configuration
- Give clear pass/fail indication

What these tests check for:
- Import failures and circular dependencies
- Critical module loading issues
- Core data structure instantiation
- Basic application structure integrity
- Broken installation or corrupted codebase

What these tests do NOT check for (user-fixable issues):
- Missing external binaries (ffmpeg, gs, etc.)
- Configuration file problems
- Permission issues
- Network connectivity
- Disk space issues
"""
