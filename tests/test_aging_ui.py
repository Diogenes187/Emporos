from app.database import aging_allocation_options
from pathlib import Path


def test_aging_options_are_always_distinct_and_legal():
    legal = {
        "characteristic.strength",
        "characteristic.dexterity",
        "characteristic.endurance",
    }
    expected_counts = {
        "two_two_two": 1,
        "two_two_one": 3,
        "two_one_one": 3,
        "one_one_one": 1,
        "one_one": 3,
        "one": 3,
    }
    for pattern, count in expected_counts.items():
        options = aging_allocation_options(pattern)
        assert len(options) == count
        for option in options:
            codes = option["physical_codes"]
            assert len(codes) == len(set(codes))
            assert set(codes) <= legal


def test_unknown_aging_pattern_has_no_fabricated_choice():
    assert aging_allocation_options("unknown") == []


def test_aging_form_only_submits_generated_physical_targets():
    template = (
        Path(__file__).parents[1] / "app" / "templates" / "crew.html"
    ).read_text(encoding="utf-8")
    assert 'type="hidden" name="physical_characteristic_codes"' in template
    assert '<select name="physical_characteristic_codes"' not in template
