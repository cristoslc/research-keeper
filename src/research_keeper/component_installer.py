from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ComponentInstaller:
    name: str
    is_installed: Callable[[], bool]
    install: Callable[[], None]


_registry: list[ComponentInstaller] = []


def register_component(component: ComponentInstaller) -> None:
    for existing in _registry:
        if existing.name == component.name:
            return
    _registry.append(component)


def install_all_components() -> dict[str, str]:
    results: dict[str, str] = {}
    for component in _registry:
        try:
            if component.is_installed():
                results[component.name] = "already_installed"
                logger.info(
                    "Component %s already installed, skipping", component.name
                )
            else:
                logger.info("Installing component: %s", component.name)
                component.install()
                results[component.name] = "installed"
        except Exception as exc:
            logger.warning(
                "Component %s install failed: %s", component.name, exc
            )
            results[component.name] = "failed"
    return results


def _register_embedding_model() -> None:
    def _is_installed() -> bool:
        try:
            from sentence_transformers import SentenceTransformer

            SentenceTransformer(
                "nomic-ai/nomic-embed-text-v1.5", local_files_only=True
            )
            return True
        except Exception:
            return False

    def _install() -> None:
        from sentence_transformers import SentenceTransformer

        SentenceTransformer(
            "nomic-ai/nomic-embed-text-v1.5", local_files_only=False
        )

    register_component(
        ComponentInstaller(
            name="embedding-model",
            is_installed=_is_installed,
            install=_install,
        )
    )


def _register_playwright_chromium() -> None:
    def _is_installed() -> bool:
        try:
            result = sys._xoptions.get("playwright_installed")
            if result is not None:
                return result
        except AttributeError:
            pass
        try:
            import subprocess

            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
                capture_output=True,
                text=True,
            )
            return (
                result.returncode == 0
                and "downloading" not in result.stdout.lower()
            )
        except Exception:
            return False

    def _install() -> None:
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "playwright",
                "install",
                "chromium",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"playwright install chromium failed: {result.stderr}"
            )

    register_component(
        ComponentInstaller(
            name="playwright-chromium",
            is_installed=_is_installed,
            install=_install,
        )
    )


_register_embedding_model()
_register_playwright_chromium()
