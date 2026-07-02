"""P5.T2/T3 — frank + stoa golden configs (drift-capture harness).

Per the agreed sequencing: the ZERO-DRIFT assertion against each blog's *real*
tree runs in that blog's migration PR (frank P7 / a stoa migration), where the
tree is the working copy — not here (blog-craft's CI has no access to those
trees). What we prove here:
  1. both configs are schema-valid;
  2. each config renders a STABLE, fully-classified blog (self-reproduction is
     zero-drift + no unclassified path) — i.e. the harness works with them and
     the templates cover everything they need.
The golden runner (golden-reproduce.sh) is what the migration PRs invoke.
"""
import os

import yaml

from reproduce import apply, default_manifest, materialized_paths, structural_diff
from path_ownership import classify
from validate_config import validate_config

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIX = os.path.join(ROOT, "tests", "fixtures")
FRANK = os.path.join(FIX, "frank.blog-craft.yaml")
STOA = os.path.join(FIX, "stoa-v2.expected.yaml")


def test_configs_are_schema_valid():
    assert validate_config(yaml.safe_load(open(FRANK))) == []
    assert validate_config(yaml.safe_load(open(STOA))) == []


def test_golden_runner_present():
    assert os.access(os.path.join(ROOT, "tests", "reproduction", "golden-reproduce.sh"), os.X_OK) \
        or os.path.exists(os.path.join(ROOT, "tests", "reproduction", "golden-reproduce.sh"))


def _stable(cfg_path, tmp_path):
    a = apply(cfg_path, str(tmp_path / "a"))
    b = apply(cfg_path, str(tmp_path / "b"))
    m = default_manifest()
    drift = structural_diff(a, b, m)
    unclassified = [p for p in materialized_paths(a) if classify(p, m) is None]
    return drift, unclassified


def test_frank_config_renders_stable_blog(tmp_path):
    # papers on + read_tracker + analytics + roadmap -> exercises the full surface
    drift, unclassified = _stable(FRANK, tmp_path)
    assert drift == [], drift
    assert unclassified == [], unclassified


def test_stoa_config_renders_stable_blog(tmp_path):
    drift, unclassified = _stable(STOA, tmp_path)
    assert drift == [], drift
    assert unclassified == [], unclassified
