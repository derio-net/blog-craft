"""gen-character-sheet.py draws its character prose from config (spec D8).

`image.character_sheet.layers` names the character-defining layers (default
[persona, visual_constants] — so existing blogs need no config edit; frank's
migration sets [base_character]). The sheet prompt keeps its fixed frame
(SHEET_STYLE ... SHEET_LAYOUT): the first configured layer renders under the
"CHARACTER — draw THIS character:" label, list-shaped layers under
"HOLD ALL OF THESE CONSTANT"; resolution reuses compose.resolve_layer.

The default-config case is BYTE-PARITY: today's persona+visual_constants
output, reproduced exactly.
"""
import importlib.util
import os

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHEET = os.path.join(_ROOT, "templates/hugo-hextra/scripts/gen-character-sheet.py")


def _load():
    spec = importlib.util.spec_from_file_location("gen_character_sheet", SHEET)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DEFAULT_CFG = {
    "layers": {"persona": "A chibi persona.", "visual_constants": ["green skin", "neck bolts"]},
}


def test_default_config_byte_parity():
    m = _load()
    got = m.build_prompt(DEFAULT_CFG)
    expected = "\n\n".join([
        m.SHEET_STYLE,
        "CHARACTER — draw THIS character:\nA chibi persona.",
        "HOLD ALL OF THESE CONSTANT (they define the character):\n- green skin\n- neck bolts",
        m.SHEET_LAYOUT,
    ])
    assert got == expected


def test_frank_shaped_character_sheet_layers():
    m = _load()
    cfg = {
        "layers": {"base_character": "Frank, stitched of server parts.",
                   "persona": "IGNORED", "visual_constants": ["IGNORED"]},
        "character_sheet": {"layers": ["base_character"]},
    }
    got = m.build_prompt(cfg)
    assert "CHARACTER — draw THIS character:\nFrank, stitched of server parts." in got
    assert "IGNORED" not in got


def test_unknown_character_layer_is_a_clear_error():
    m = _load()
    cfg = {"layers": {"persona": "P"},
           "character_sheet": {"layers": ["nope_layer"]}}
    with pytest.raises(SystemExit, match="nope_layer"):
        m.build_prompt(cfg)


def test_missing_default_layers_tolerated():
    # a blog with only persona (no visual_constants) still builds a sheet
    m = _load()
    got = m.build_prompt({"layers": {"persona": "Solo persona."}})
    assert "Solo persona." in got
    assert "HOLD ALL OF THESE CONSTANT" not in got
