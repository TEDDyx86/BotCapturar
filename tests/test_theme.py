from botcapturar.theme import COLORS, FONTS, SPACING


def test_theme_uses_capturix_dark_purple_gold_and_semantic_states():
    assert COLORS["background"] == "#110C22"
    assert COLORS["panel"] == "#1D1032"
    assert COLORS["gold"] == "#F2BF4C"
    assert COLORS["success"] == "#72EC4A"
    assert COLORS["danger"] == "#951440"


def test_theme_spacing_has_consistent_small_and_panel_rhythm():
    assert SPACING["sm"] == 8
    assert SPACING["md"] == 16
    assert SPACING["lg"] == 24


def test_theme_defines_a_compact_console_panel_heading():
    assert FONTS["panel-title"] == ("Consolas", 18, "bold")
