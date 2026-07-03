"""P4.T2 — read-tracker + analytics materialize iff their feature flag is set."""
import os
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDER = os.path.join(ROOT, "tools", "bootstrap-render.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")

RT = "assets/js/read-tracker.js"
GC = "layouts/partials/custom/goatcounter.html"


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
