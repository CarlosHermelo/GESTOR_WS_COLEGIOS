"""
Configuración de pytest para tests async.
"""
import pytest


def pytest_configure(config):
    """Configuración global de pytest."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


@pytest.fixture(scope="session")
def event_loop_policy():
    """Usar policy por defecto para el event loop."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()

