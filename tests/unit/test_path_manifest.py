"""P1.T2 — path-ownership manifest + classifier.

Every path the templates materialize must be classified exactly once as
framework | content | merged (spec §3, §11 "no unclassified materialized path").
"""
import os

from path_ownership import classify, classify_all, load_manifest  # tools/ on sys.path

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST = os.path.join(ROOT, "templates", "manifest.yaml")
TPL = os.path.join(ROOT, "templates", "hugo-hextra")


def _materialized_paths():
    out = []
    for dp, _, fs in os.walk(TPL):
        for f in fs:
            rel = os.path.relpath(os.path.join(dp, f), TPL)
            if rel.endswith(".tmpl"):
                rel = rel[:-len(".tmpl")]
            out.append(rel)
    return out


def test_manifest_loads_known_classes():
    m = load_manifest(MANIFEST)
    assert set(m) <= {"framework", "content", "merged"}


def test_every_materialized_path_classified_exactly_once():
    m = load_manifest(MANIFEST)
    for p in _materialized_paths():
        classes = set(classify_all(p, m))
        assert len(classes) == 1, f"{p} classified as {classes} (want exactly one)"


def test_no_unclassified_materialized_path():
    m = load_manifest(MANIFEST)
    for p in _materialized_paths():
        assert classify(p, m) is not None, f"{p} is unclassified"


def test_per_series_outputs_are_content():
    m = load_manifest(MANIFEST)
    for p in ("content/docs/tutorials/_index.md",
              "content/docs/tutorials/00-overview/index.md"):
        assert classify(p, m) == "content"
