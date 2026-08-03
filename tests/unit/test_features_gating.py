"""P4.T2 — read-tracker + analytics materialize iff their feature flag is set.

Extended by stickers P4.T3: `features.stickers` gates the two sticker scripts
(stk-4). Opt-in is a promise to every existing blog — gondor and stoa must carry
none of it — and after `migrations/006_to_007.py` the shape that promise is kept
for is `{enabled: false}`, written explicitly into every UPDATED config. So
`disabled` is the case that actually occurs in the field and `absent` is the
legacy one; both are asserted here.
"""
import os
import subprocess

import yaml

from path_ownership import _matches, classify, load_manifest, root_of

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDER = os.path.join(ROOT, "tools", "bootstrap-render.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")
MANIFEST = os.path.join(ROOT, "templates", "manifest.yaml")

RT = "assets/js/read-tracker.js"
GC = "layouts/partials/custom/goatcounter.html"

STICKER_SCRIPTS = ("scripts/build-sheets.py", "scripts/generate-stickers.py")


def _base():
    # complete v2 config (stoa-style, no papers) to override features on.
    return yaml.safe_load(open(os.path.join(FIX, "stoa-v2.expected.yaml")))


def _bootstrap(cfg, tmp_path, name):
    ans = tmp_path / f"{name}.yaml"
    ans.write_text(yaml.safe_dump(cfg))
    target = tmp_path / name
    r = subprocess.run(["bash", RENDER, str(ans), str(target)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return target


def test_features_on_materialize(tmp_path):
    cfg = _base()
    cfg["features"] = {"read_tracker": True,
                       "analytics": {"provider": "goatcounter", "url": "https://counter.example/x"}}
    b = _bootstrap(cfg, tmp_path, "on")
    assert (b / RT).exists()
    gc = b / GC
    assert gc.exists()
    text = gc.read_text()
    # literal beacon URL baked from features.analytics.url (not a Hugo getenv)
    assert "https://counter.example/x/count" in text
    assert "https://counter.example/x/count.js" in text
    assert "getenv" not in text   # getenv is Hugo-security-blocked; must be a literal


def test_features_off_absent(tmp_path):
    cfg = _base()
    cfg["features"] = {"read_tracker": False}   # no analytics block
    b = _bootstrap(cfg, tmp_path, "off")
    assert not (b / RT).exists()
    assert not (b / GC).exists()


# --- stickers (P4.T3, stk-4): default OFF, and no Hugo surface at all ---------

def _stickers(enabled):
    return {"enabled": enabled,
            "prompts_file": "blog/_private/stickers/stickers.yaml",
            "images_dir": "blog/_private/stickers/images",
            "sheets_dir": "blog/_private/stickers/sheets"}


def test_stickers_absent_materializes_neither_script(tmp_path):
    """The legacy shape: any blog whose config predates the v7 rung."""
    cfg = _base()
    cfg.setdefault("features", {}).pop("stickers", None)
    b = _bootstrap(cfg, tmp_path, "stk-absent")
    for rel in STICKER_SCRIPTS:
        assert not (b / rel).exists(), f"{rel} present with no features.stickers at all"


def test_stickers_disabled_materializes_neither_script(tmp_path):
    """The COMMON shape after 006_to_007, which seeds `{enabled: false}`."""
    cfg = _base()
    cfg.setdefault("features", {})["stickers"] = _stickers(False)
    b = _bootstrap(cfg, tmp_path, "stk-off")
    for rel in STICKER_SCRIPTS:
        assert not (b / rel).exists(), f"{rel} present when the feature is disabled"


def test_stickers_enabled_materializes_both_scripts(tmp_path):
    cfg = _base()
    cfg.setdefault("features", {})["stickers"] = _stickers(True)
    b = _bootstrap(cfg, tmp_path, "stk-on")
    for rel in STICKER_SCRIPTS:
        assert (b / rel).is_file(), f"{rel} missing when the feature is enabled"
    # they ship as SIBLINGS of the engine they delegate to / live beside
    assert (b / "scripts/generate-images.py").is_file()
    assert (b / "scripts/compose.py").is_file()


def test_stickers_ship_no_hugo_surface(tmp_path):
    """Operator decision 3: the sticker set is a private PRINT asset. Enabling it
    must add no layout, no shortcode, no CSS, no gallery — the feature module is
    scripts and nothing else, unlike every other templates/features/ bundle."""
    cfg = _base()
    cfg.setdefault("features", {})["stickers"] = _stickers(True)
    on = _bootstrap(cfg, tmp_path, "surface-on")
    cfg2 = _base()
    cfg2.setdefault("features", {})["stickers"] = _stickers(False)
    off = _bootstrap(cfg2, tmp_path, "surface-off")

    def _tree(base):
        return {os.path.relpath(os.path.join(dp, f), base)
                for dp, _, fs in os.walk(base) for f in fs}

    added = _tree(on) - _tree(off)
    # .blog-craft.sync.yaml records the answers, so it differs by content, not name
    assert added == set(STICKER_SCRIPTS), added


def test_the_two_sticker_scripts_classify_via_the_existing_manifest_rows(tmp_path):
    """No manifest change: `scripts/**` already says framework + site-rooted."""
    m = load_manifest(MANIFEST)
    for rel in STICKER_SCRIPTS:
        assert classify(rel, m) == "framework", rel
        assert root_of(rel, m) == "site", rel
        # test_path_roots.py's completeness guard: exactly ONE root may match
        hits = [r for r, globs in (m.get("roots") or {}).items()
                if any(_matches(g, rel) for g in globs)]
        assert hits == ["site"], f"{rel} matches roots {hits} (want exactly one)"
