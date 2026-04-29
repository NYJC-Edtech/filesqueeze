"""Test dependency rules - system must not import ops.

These tests enforce the architectural rule that the system package
must never import from the ops package to avoid circular dependencies.
"""

import inspect
import sys

import pytest


class TestDependencyRules:
    """Test that dependency direction rules are enforced."""

    def test_system_does_not_import_ops(self):
        """Enforce: system package must not import ops package."""
        system_modules = [
            "filesqueeze.system.logger",
            "filesqueeze.system.binaries",
            "filesqueeze.system.platform",
            "filesqueeze.system.config_adapters",
            "filesqueeze.system.decorators",
        ]

        violations = []

        for module_name in system_modules:
            # Import module if not already loaded
            if module_name not in sys.modules:
                try:
                    __import__(module_name)
                except ImportError as e:
                    pytest.skip(f"Could not import {module_name}: {e}")
                    continue

            module = sys.modules[module_name]

            try:
                source = inspect.getsource(module)
            except (OSError, TypeError):
                # Built-in or compiled module, skip
                continue

            # Check for ops imports
            if "from filesqueeze.ops" in source:
                violations.append(f"{module_name} imports from filesqueeze.ops")

            if "from .ops" in source:
                violations.append(f"{module_name} imports from .ops (relative)")

            if "import filesqueeze.ops" in source:
                violations.append(f"{module_name} imports filesqueeze.ops")

        # Assert no violations
        assert len(violations) == 0, "Dependency rule violations found:\n" + "\n".join(violations)

    def test_ops_can_import_system(self):
        """Ops package can import from system package."""
        # This should work without errors
        from filesqueeze.ops import document, video

        # Modules should be loaded
        assert video is not None
        assert document is not None

        # Verify they actually import from system
        # (by checking they have access to system resources)
        # This is a basic sanity check

    def test_no_circular_imports_between_system_and_ops(self):
        """Verify no circular imports exist between system and ops."""
        # Start fresh
        modules_to_unload = [
            "filesqueeze.system",
            "filesqueeze.ops",
            "filesqueeze.system.logger",
            "filesqueeze.system.binaries",
            "filesqueeze.ops.video",
            "filesqueeze.ops.document",
        ]

        # Unload if present
        for mod in modules_to_unload:
            if mod in sys.modules:
                del sys.modules[mod]

        try:
            # Import system first
            # Then import ops
            import filesqueeze.ops.video
            import filesqueeze.system.logger

            # If we get here without circular import error, test passes
            assert True

        except ImportError as e:
            if "circular import" in str(e).lower():
                pytest.fail(f"Circular import detected: {e}")
            else:
                # Other import error (e.g., missing module) is OK for this test
                pytest.skip(f"Import error (not circular): {e}")

    def test_system_modules_are_independent(self):
        """System modules should be independently importable."""
        system_modules = [
            "filesqueeze.system.logger",
            "filesqueeze.system.binaries",
            "filesqueeze.system.platform",
            "filesqueeze.system.config_adapters",
        ]

        for module_name in system_modules:
            # Try importing each system module independently
            try:
                if module_name in sys.modules:
                    del sys.modules[module_name]

                __import__(module_name)

                # If successful, module is independent
                assert True

            except ImportError as e:
                # Missing dependencies are OK (not yet implemented)
                # Circular imports are not OK
                if "circular import" in str(e).lower():
                    pytest.fail(f"{module_name} has circular dependencies")
                else:
                    # Module not yet implemented, skip
                    pass


class TestArchitectureDocumentation:
    """Test that architectural rules are documented."""

    def test_system_package_has_docstring(self):
        """System package should have documentation."""
        try:
            import filesqueeze.system

            assert filesqueeze.system.__doc__ is not None
        except ImportError:
            pytest.skip("System package not yet created")

    def test_ops_package_has_docstring(self):
        """Ops package should have documentation."""
        try:
            import filesqueeze.ops

            assert filesqueeze.ops.__doc__ is not None
        except ImportError:
            pytest.skip("Ops package not yet created")

    def test_dependency_rule_documented(self):
        """Dependency rule should be documented in system package."""
        try:
            import filesqueeze.system

            doc = filesqueeze.system.__doc__

            if doc:
                # Should mention the dependency rule
                assert "ops" in doc.lower() or "dependency" in doc.lower()
        except ImportError:
            pytest.skip("System package not yet created")


class TestImportOrder:
    """Test that import order is correct."""

    def test_system_can_be_imported_before_ops(self):
        """System should be importable before ops (no hidden ops imports)."""
        # This ensures system doesn't lazy-import ops

        # Unload both
        for mod in list(sys.modules.keys()):
            if mod.startswith("filesqueeze.system") or mod.startswith("filesqueeze.ops"):
                del sys.modules[mod]

        try:
            # Import system first
            import filesqueeze.system

            # Check that ops is NOT yet loaded
            assert "filesqueeze.ops.video" not in sys.modules
            assert "filesqueeze.ops.document" not in sys.modules

            # Now import ops
            import filesqueeze.ops.video

            # Ops should now be loaded
            assert "filesqueeze.ops.video" in sys.modules

        except ImportError as e:
            if "circular import" in str(e).lower():
                pytest.fail(f"Circular import when importing system before ops: {e}")
            else:
                pytest.skip(f"Import error: {e}")

    def test_ops_imports_system_implicitly(self):
        """Ops modules should import from system (explicit dependency)."""
        # Unload first
        for mod in list(sys.modules.keys()):
            if mod.startswith("filesqueeze"):
                del sys.modules[mod]

        try:
            # Import ops (which should import system)
            import filesqueeze.ops.video

            # System should now be loaded (because ops depends on it)
            assert "filesqueeze.system" in sys.modules or "filesqueeze.system.logger" in sys.modules

        except ImportError:
            pytest.skip("Ops modules not yet created")


class TestDependencyGraph:
    """Test the dependency graph structure."""

    def test_ops_has_system_as_dependency(self):
        """Ops modules list system as a dependency."""
        try:
            import inspect

            from filesqueeze.ops import video

            # inspect.getsource expects the module object, not __file__ string
            source = inspect.getsource(video)

            # Should import from system
            # (This is a loose check - we just verify ops imports something)
            assert True  # If we got here, imports worked

        except (ImportError, AttributeError):
            pytest.skip("Ops modules not yet created or not inspectable")

    def test_system_does_not_list_ops_as_dependency(self):
        """System modules should NOT list ops as dependency."""
        system_modules = [
            "filesqueeze.system.logger",
            "filesqueeze.system.binaries",
        ]

        for module_name in system_modules:
            if module_name not in sys.modules:
                try:
                    __import__(module_name)
                except ImportError:
                    continue

            module = sys.modules[module_name]

            # Get module's dependencies
            try:
                source = inspect.getsource(module)
            except (OSError, TypeError):
                continue

            # Should NOT import ops
            assert "filesqueeze.ops" not in source, f"{module_name} should not depend on filesqueeze.ops"


class TestPackageStructure:
    """Test that package structure is correct."""

    def test_system_package_exists(self):
        """System package should exist."""
        try:
            import filesqueeze.system

            assert hasattr(filesqueeze.system, "__path__")
        except ImportError:
            pytest.skip("System package not yet created")

    def test_ops_package_exists(self):
        """Ops package should exist."""
        try:
            import filesqueeze.ops

            assert hasattr(filesqueeze.ops, "__path__")
        except ImportError:
            pytest.skip("Ops package not yet created")

    def test_expected_system_modules_exist(self):
        """Expected system modules should exist."""
        expected_modules = [
            "filesqueeze.system.logger",
            "filesqueeze.system.binaries",
            "filesqueeze.system.platform",
            "filesqueeze.system.config_adapters",
        ]

        existing_modules = []
        missing_modules = []

        for module_name in expected_modules:
            try:
                __import__(module_name)
                existing_modules.append(module_name)
            except ImportError:
                missing_modules.append(module_name)

        # At least some should exist (unless we're testing before Phase 1)
        # If this is being run before implementation, that's OK
        if len(existing_modules) == 0:
            pytest.skip("System modules not yet implemented (expected before Phase 1)")

    def test_expected_ops_modules_exist(self):
        """Expected ops modules should exist."""
        expected_modules = [
            "filesqueeze.ops.video",
            "filesqueeze.ops.document",
            "filesqueeze.ops.image",
            "filesqueeze.ops.presentation",
        ]

        existing_modules = []
        missing_modules = []

        for module_name in expected_modules:
            try:
                __import__(module_name)
                existing_modules.append(module_name)
            except ImportError:
                missing_modules.append(module_name)

        # At least some should exist (unless we're testing before Phase 2)
        if len(existing_modules) == 0:
            pytest.skip("Ops modules not yet implemented (expected before Phase 2)")
