"""P5.T1 — reproduction harness core (apply-to-scratch + structural diff)."""
import os
from pathlib import Path

import yaml

from path_ownership import classify
from reproduce import apply, default_manifest, materialized_paths, structural_diff

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIX = os.path.join(ROOT, "tests", "fixtures")


def _cfg(tmp_path):
    # papers-enabled config → exercises the content-type-papers materialization too.
    cfg = yaml.safe_load(open(os.path.join(FIX, "answers-papers-v2.yaml")))
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(cfg))
    return str(p)


def test_self_reproduction_is_zero_drift(tmp_path):
    cfg = _cfg(tmp_path)
    a = apply(cfg, str(tmp_path / "a"))
    b = apply(cfg, str(tmp_path / "b"))
    drift = structural_diff(a, b, default_manifest())
    assert drift == [], drift


def test_no_unclassified_materialized_path(tmp_path):
    a = apply(_cfg(tmp_path), str(tmp_path / "a"))
    m = default_manifest()
    unclassified = [p for p in materialized_paths(a) if classify(p, m) is None]
    assert unclassified == [], unclassified


def test_structural_diff_detects_framework_drift(tmp_path):
    cfg = _cfg(tmp_path)
    a = apply(cfg, str(tmp_path / "a"))
    b = apply(cfg, str(tmp_path / "b"))
    tampered = Path(b) / "layouts" / "shortcodes" / "screenshot.html"
    assert tampered.exists()
    tampered.write_text("TAMPERED")
    drift = structural_diff(a, b, default_manifest())
    assert any("screenshot.html" in d for d in drift)


def test_structural_diff_ignores_content(tmp_path):
    cfg = _cfg(tmp_path)
    a = apply(cfg, str(tmp_path / "a"))
    b = apply(cfg, str(tmp_path / "b"))
    # editing a content file must NOT count as drift
    (Path(b) / "content" / "_index.md").write_text("---\ntitle: changed\n---\n")
    assert structural_diff(a, b, default_manifest()) == []
