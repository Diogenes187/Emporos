from tools.verify_database import NARRATIVE_TEXT_MARKERS


def test_character_appearance_is_narrative_not_mechanical_prose():
    column_name = "appearance"
    assert any(marker in column_name for marker in NARRATIVE_TEXT_MARKERS)
