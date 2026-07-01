"""P2.T1 — generic layer concatenator (Approach A, spec §4.1).

compose(composition_order, layers, entry) joins non-empty resolved sections with
"\\n\\n" (matching frank's generate-all-images.py). Resolution:
  scalar -> verbatim; list -> "- " bullets; scene -> entry.prompt;
  indexed-table torso -> layers.torso[entry.torso|entry.series][entry.torso_variant];
  indexed-table mood  -> layers.mood[entry.mood] or entry.mood (free-form).
"""
from compose import compose  # tools/ on sys.path

LAYERS = {
    "base_style": "STYLE",
    "persona": "PERSONA",
    "visual_constants": ["c1", "c2"],
    "reference_guidance": "GUIDE",
    "torso": {"building": ["torsoB0", "torsoB1"], "papers": ["torsoP0"]},
    "mood": {"focused": "MOODF", "weighing": "MOODW"},
}
STOA_ORDER = ["base_style", "persona", "visual_constants", "scene", "reference_guidance"]


def test_scalar_list_scene_join():
    out = compose(STOA_ORDER, LAYERS, {"prompt": "SCENE"})
    assert out == "STYLE\n\nPERSONA\n\n- c1\n- c2\n\nSCENE\n\nGUIDE"


def test_torso_indexed_by_group_and_variant():
    out = compose(["torso", "scene"], LAYERS,
                  {"torso": "building", "torso_variant": 1, "prompt": "S"})
    assert out == "torsoB1\n\nS"


def test_torso_defaults_group_to_series():
    out = compose(["torso", "scene"], LAYERS,
                  {"series": "papers", "torso_variant": 0, "prompt": "S"})
    assert out == "torsoP0\n\nS"


def test_mood_named_then_freeform():
    assert compose(["mood"], LAYERS, {"mood": "focused"}) == "MOODF"
    assert compose(["mood"], LAYERS, {"mood": "a bespoke mood"}) == "a bespoke mood"


def test_missing_selector_skips_layer():
    # torso in order but no torso/series/variant on the entry -> skipped
    assert compose(["torso", "scene"], LAYERS, {"prompt": "ONLY"}) == "ONLY"


def test_empty_sections_dropped():
    assert compose(["base_style", "scene"], {"base_style": ""}, {"prompt": "X"}) == "X"
