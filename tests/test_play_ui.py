from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_play_screen_preserves_original_bridge_structure():
    template = (ROOT / "app" / "templates" / "play.html").read_text(
        encoding="utf-8"
    )
    assert 'class="mapwrap"' in template
    assert 'class="bridge-panel"' in template
    assert 'class="feed"' in template
    assert "data-feed-grip" in template
    assert 'class="modal"' in template
    assert 'data-tab="crew"' in template
    assert 'data-tab="ships"' in template
    assert 'data-tab="worlds"' in template
    assert 'data-tab="lore"' in template


def test_play_map_is_svg_backed_by_relational_systems():
    template = (ROOT / "app" / "templates" / "play.html").read_text(
        encoding="utf-8"
    )
    assert "<svg" in template
    assert "{% for system in campaign.systems" in template
    assert "system.hex_column" in template
    assert "system.hex_row" in template


def test_play_screen_does_not_extend_current_emporos_shell():
    template = (ROOT / "app" / "templates" / "play.html").read_text(
        encoding="utf-8"
    )
    assert '{% extends "base.html" %}' not in template
    assert 'class="rail"' not in template
    assert 'class="dashboard-grid"' not in template
