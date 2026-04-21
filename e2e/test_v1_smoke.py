"""Smoke tests for v1 UI (frontend/) — nav, Serves tab, detail panel, API."""

import requests


def test_home_loads(base_url):
    r = requests.get(f"{base_url}/", timeout=5)
    assert r.status_code == 200
    assert "RoboPong" in r.text


def test_api_serves_tree(base_url):
    r = requests.get(f"{base_url}/api/serves/tree", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert len(d["groups"]) == 6
    names = [g["name"] for g in d["groups"]]
    assert "Pendulum" in names
    assert "Tomahawk" in names
    assert "Squat" in names
    # Each factory group has serves with placement + responses
    for g in d["groups"]:
        assert g["readonly"] is True
        for sv in g["serves"]:
            assert "placement" in sv and "x" in sv["placement"] and "y" in sv["placement"]
            assert sv["technique"] in {"pendulum", "reverse_pendulum", "tomahawk", "backhand", "shovel", "squat"}
            assert sv["length"] in {"short", "half_long", "long"}


def test_duration_override_roundtrip(base_url):
    # Set
    r = requests.put(f"{base_url}/api/serves/1001/duration", json={"duration_sec": 450}, timeout=5)
    assert r.status_code == 200
    sv = requests.get(f"{base_url}/api/serves/1001", timeout=5).json()
    assert sv["duration_sec"] == 450
    assert sv["modified"] is True
    # Reset
    requests.put(f"{base_url}/api/serves/1001/reset", timeout=5)
    sv = requests.get(f"{base_url}/api/serves/1001", timeout=5).json()
    assert sv["modified"] is False


def test_v1_nav_has_serves_tab(page, base_url):
    page.goto(base_url + "/")
    page.wait_for_load_state("networkidle")
    nav_buttons = page.locator("nav.nav button").all_text_contents()
    assert any("Serwy" in t or "Serves" in t for t in nav_buttons), f"Nav: {nav_buttons}"


def test_v1_serves_tab_shows_groups(page, base_url):
    page.goto(base_url + "/")
    page.wait_for_load_state("networkidle")
    page.locator("nav.nav button", has_text="Serwy").click()
    page.wait_for_timeout(300)
    # Find only the visible (Serves) page
    groups = page.locator("div.page", has_text="🎾 Serwy").locator(".drill-folder-name").all_text_contents()
    assert len(groups) == 6
    assert any("Pendulum" in g for g in groups)


def test_v1_serve_detail_panel_renders(page, base_url):
    page.goto(base_url + "/")
    page.wait_for_load_state("networkidle")
    page.locator("nav.nav button", has_text="Serwy").click()
    page.wait_for_timeout(300)
    serves_view = page.locator("div.page", has_text="🎾 Serwy")
    # Expand Pendulum (first group)
    serves_view.locator(".drill-folder-header").filter(has_text="Pendulum").first.click()
    page.wait_for_timeout(200)
    # Click first serve
    serves_view.locator(".drill-row").first.click()
    page.wait_for_timeout(200)
    # Placement SVG present
    svg = serves_view.locator('svg[viewBox="0 0 120 68"]')
    assert svg.count() == 1
    # Spin bars (5 total, some active)
    total_bars = serves_view.locator(".serve-spin-bar").count()
    assert total_bars == 5
    # Two action buttons
    assert serves_view.get_by_text("🧘", exact=False).count() >= 1
    assert serves_view.get_by_text("🤖", exact=False).count() >= 1


def test_v1_language_switch_translates_serve(page, base_url):
    page.goto(base_url + "/")
    page.wait_for_load_state("networkidle")
    # Force English via localStorage + reload
    page.evaluate("localStorage.setItem('lang', 'en')")
    page.reload()
    page.wait_for_load_state("networkidle")
    page.locator("nav.nav button", has_text="Serves").click()
    page.wait_for_timeout(300)
    serves_view = page.locator("div.page", has_text="🎾 Serves")
    groups = serves_view.locator(".drill-folder-name").all_text_contents()
    # EN names
    assert any("Pendulum" in g for g in groups)
    assert any("Tomahawk" in g for g in groups)
