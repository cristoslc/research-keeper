from __future__ import annotations

from unittest.mock import MagicMock, patch

from research_keeper.component_installer import (
    ComponentInstaller,
    _registry,
    install_all_components,
    register_component,
)


class TestComponentInstallation:
    def test_registry_empty_by_default(self):
        old = _registry.copy()
        _registry.clear()
        try:
            assert _registry == []
            results = install_all_components()
            assert results == {}
        finally:
            _registry[:] = old

    def test_register_adds_to_registry(self):
        old = _registry.copy()
        try:
            fake = ComponentInstaller(
                name="fake",
                is_installed=lambda: False,
                install=lambda: None,
            )
            _registry.clear()
            register_component(fake)
            assert len(_registry) == 1
            assert _registry[0].name == "fake"
        finally:
            _registry[:] = old

    def test_install_all_components_skips_installed(self):
        old = _registry.copy()
        try:
            install_called = []
            fake = ComponentInstaller(
                name="fake",
                is_installed=lambda: True,
                install=lambda: install_called.append(1),
            )
            _registry.clear()
            register_component(fake)
            results = install_all_components()
            assert results == {"fake": "already_installed"}
            assert install_called == []
        finally:
            _registry[:] = old

    def test_install_all_components_runs_missing(self):
        old = _registry.copy()
        try:
            install_called = []
            fake = ComponentInstaller(
                name="fake",
                is_installed=lambda: False,
                install=lambda: install_called.append(1),
            )
            _registry.clear()
            register_component(fake)
            results = install_all_components()
            assert results == {"fake": "installed"}
            assert install_called == [1]
        finally:
            _registry[:] = old

    def test_install_all_components_captures_failure(self):
        old = _registry.copy()
        try:
            def fail():
                raise RuntimeError("boom")

            fake = ComponentInstaller(
                name="fake",
                is_installed=lambda: False,
                install=fail,
            )
            _registry.clear()
            register_component(fake)
            results = install_all_components()
            assert results == {"fake": "failed"}
        finally:
            _registry[:] = old

    def test_register_component_dedup(self):
        old = _registry.copy()
        try:
            fake1 = ComponentInstaller(
                name="dup", is_installed=lambda: True, install=lambda: None
            )
            fake2 = ComponentInstaller(
                name="dup", is_installed=lambda: False, install=lambda: None
            )
            _registry.clear()
            register_component(fake1)
            register_component(fake2)
            assert len(_registry) == 1
        finally:
            _registry[:] = old
