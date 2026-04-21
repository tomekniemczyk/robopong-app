"""Smoke tests for v2 UI (frontend-v2/) — parity check with v1."""


def test_v2_home_loads(page, base_url):
    page.goto(base_url + "/v2/")
    page.wait_for_load_state("networkidle")
    assert "RoboPong" in page.title()


def test_v2_nav_has_serves_tab(page, base_url):
    page.goto(base_url + "/v2/")
    page.wait_for_load_state("networkidle")
    nav_buttons = page.locator("nav.nav button").all_text_contents()
    assert any("Serwy" in t or "Serves" in t for t in nav_buttons)


def test_v2_serves_tab_shows_groups(page, base_url):
    page.goto(base_url + "/v2/")
    page.wait_for_load_state("networkidle")
    page.locator("nav.nav button", has_text="Serwy").click()
    page.wait_for_timeout(300)
    groups = page.locator("div.page", has_text="🎾 Serwy").locator(".drill-folder-name").all_text_contents()
    assert len(groups) == 6


def test_v2_serve_detail_panel_renders(page, base_url):
    page.goto(base_url + "/v2/")
    page.wait_for_load_state("networkidle")
    page.locator("nav.nav button", has_text="Serwy").click()
    page.wait_for_timeout(300)
    serves_view = page.locator("div.page", has_text="🎾 Serwy")
    serves_view.locator(".drill-folder-header").filter(has_text="Pendulum").first.click()
    page.wait_for_timeout(200)
    serves_view.locator(".drill-row").first.click()
    page.wait_for_timeout(200)
    assert serves_view.locator('svg[viewBox="0 0 120 68"]').count() == 1
    assert serves_view.locator(".serve-spin-bar").count() == 5
