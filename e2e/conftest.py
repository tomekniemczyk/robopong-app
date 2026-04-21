"""Shared fixtures for e2e tests — browser + live backend URL."""

import os
import pytest
from playwright.sync_api import sync_playwright


BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8766")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


@pytest.fixture()
def page(browser):
    ctx = browser.new_context(viewport={"width": 412, "height": 915})  # mobile-like
    p = ctx.new_page()
    errors = []
    p.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

    def _on_console(msg):
        if msg.type != "error":
            return
        text = msg.text
        # Filter harmless noise: motion camera stream (not available in simulation),
        # ws reconnect logs, resource loading errors for external services.
        ignored = ["8081", "ERR_CONNECTION_REFUSED", "Failed to load resource"]
        if any(ig in text for ig in ignored):
            return
        errors.append(f"console.error: {text}")

    p.on("console", _on_console)
    yield p
    ctx.close()
    assert not errors, f"Unexpected JS errors: {errors}"
