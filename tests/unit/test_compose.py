"""Generic layer concatenator (Approach A, spec §4.1 — v4 `_select` walk).

compose(composition_order, layers, entry) joins non-empty resolved sections with
"\\n\\n" (matching frank's generate-all-images.py). Resolution:
  scalar -> verbatim; list -> "- " bullets; scene -> entry.prompt;
  dict -> selector walk: `_select` declares the steps (default: the layer's own
  name); each step is an entry field or a list of fields (first present wins);
  dict-key / int-index descent; free-form passthrough at the LAST step only;
  an intermediate miss or a missing field skips the layer. `_`-prefixed table
  keys are directives, never prose.

The torso tables here carry the explicit `_select` that migration 003_to_004
writes — the engine itself no longer knows the words "torso" or "mood".
"""
from compose import compose  # tools/ on sys.path

LAYERS = {
    "base_style": "STYLE",
    "persona": "PERSONA",
    "visual_constants": ["c1", "c2"],
    "reference_guidance": "GUIDE",
    "torso": {
        "_select": [["torso", "series"], "torso_variant"],
        "building": ["torsoB0", "torsoB1"],
        "papers": ["torsoP0"],
    },
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


def test_torso_alternatives_first_present_wins():
    # entry.torso beats entry.series when both are present
    out = compose(["torso"], LAYERS,
                  {"torso": "papers", "series": "building", "torso_variant": 0})
    assert out == "torsoP0"


def test_mood_named_then_freeform():
    assert compose(["mood"], LAYERS, {"mood": "focused"}) == "MOODF"
    assert compose(["mood"], LAYERS, {"mood": "a bespoke mood"}) == "a bespoke mood"


def test_generic_dict_layer_default_selector():
    layers = {"palette": {"warm": "WARM PROSE"}}
    assert compose(["palette"], layers, {"palette": "warm"}) == "WARM PROSE"


def test_generic_dict_layer_freeform_passthrough():
    # v4: passthrough at the last step is universal, not mood-specific
    layers = {"palette": {"warm": "WARM PROSE"}}
    assert compose(["palette"], layers, {"palette": "novel prose"}) == "novel prose"


def test_freeform_torso_variant_passthrough_at_last_step():
    out = compose(["torso"], LAYERS,
                  {"series": "building", "torso_variant": "hand-written torso"})
    assert out == "hand-written torso"


def test_intermediate_miss_skips_layer():
    # unknown group must NOT pass through as prose (it isn't the last step)
    out = compose(["torso", "scene"], LAYERS,
                  {"series": "unknown", "torso_variant": 0, "prompt": "S"})
    assert out == "S"


def test_missing_selector_skips_layer():
    # torso in order but no torso/series field on the entry -> skipped
    assert compose(["torso", "scene"], LAYERS, {"prompt": "ONLY"}) == "ONLY"


def test_missing_second_step_field_skips_layer():
    out = compose(["torso", "scene"], LAYERS,
                  {"series": "building", "prompt": "S"})
    assert out == "S"


def test_index_out_of_range_skips_layer():
    out = compose(["torso", "scene"], LAYERS,
                  {"series": "papers", "torso_variant": 5, "prompt": "S"})
    assert out == "S"


def test_underscore_keys_are_never_prose():
    layers = {"style": {"_note": "SECRET", "warm": "WARM"}}
    # selecting the directive key must not surface it; it falls to passthrough
    assert compose(["style"], layers, {"style": "_note"}) == "_note"


def test_walk_dead_end_on_non_scalar_skips_layer():
    # steps exhausted while the value is still a container -> "" (validator flags it)
    layers = {"torso": {"_select": [["torso", "series"]],
                        "building": ["torsoB0", "torsoB1"]}}
    assert compose(["torso", "scene"], layers,
                   {"series": "building", "prompt": "S"}) == "S"


def test_empty_sections_dropped():
    assert compose(["base_style", "scene"], {"base_style": ""}, {"prompt": "X"}) == "X"
