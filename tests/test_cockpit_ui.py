from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_campaign_home_prioritizes_map_and_referee():
    template = (ROOT / "app" / "templates" / "dashboard.html").read_text(
        encoding="utf-8"
    )
    assert 'class="cockpit-workspace"' in template
    assert 'class="cockpit-map"' in template
    assert 'class="cockpit-referee"' in template
    assert 'role="separator"' in template
    assert 'data-layout="referee"' in template
    assert 'data-layout="split"' in template
    assert 'data-layout="map"' in template


def test_mechanics_launch_in_focused_workspaces():
    template = (ROOT / "app" / "templates" / "dashboard.html").read_text(
        encoding="utf-8"
    )
    for name in ("Characters & Crew", "Ships", "Trade", "Encounters", "Psionics"):
        assert f'data-workspace="{name}"' in template
    assert "data-mechanics-workspace" in template
    assert "data-workspace-frame" in template


def test_cockpit_preferences_are_retained_per_user():
    template = (ROOT / "app" / "templates" / "dashboard.html").read_text(
        encoding="utf-8"
    )
    behavior = (ROOT / "app" / "static" / "js" / "cockpit.js").read_text(
        encoding="utf-8"
    )
    assert "current_user.public_id" in template
    assert "localStorage.setItem" in behavior
    assert "localStorage.getItem" in behavior
