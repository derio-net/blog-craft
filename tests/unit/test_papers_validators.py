"""P3.T2 — papers validators (config-driven)."""
import yaml

from dossier_parser import parse_dossier, section
from sync_dossier_to_data import sync
from validate_dossier import validate_dossier
from validate_papers import validate_paper

GATE = {"min_vendors": 3, "min_sources": 5, "min_source_types": 3,
        "min_artefacts": 3, "min_artefact_kinds": 2, "min_gaps": 1, "min_counterargs": 1}
SOURCE_TYPES = ["vendor-docs", "paper", "postmortem", "talk", "benchmark"]
ARTEFACT_KINDS = ["grafana-screenshot", "asciinema", "yaml", "commit", "incident"]


def good_dossier():
    return {
        "vendors": [{"name": f"v{i}"} for i in range(3)],
        "primary_sources": [{"title": f"s{i}", "type": t, "url": f"http://e/{i}"}
                            for i, t in enumerate(SOURCE_TYPES)],
        "artefacts": [{"kind": k} for k in ("yaml", "commit", "incident")],
        "gaps": ["g1"],
        "counter_arguments": ["c1"],
    }


# ---- dossier gate ----

def test_passing_dossier():
    assert validate_dossier(good_dossier(), GATE) == []


def test_too_few_vendors():
    d = good_dossier(); d["vendors"] = d["vendors"][:2]
    assert any("vendors" in f for f in validate_dossier(d, GATE))


def test_too_few_source_types():
    d = good_dossier()
    for s in d["primary_sources"]:
        s["type"] = "paper"
    assert any("distinct types" in f for f in validate_dossier(d, GATE))


def test_unknown_source_type_flagged():
    d = good_dossier(); d["primary_sources"][0]["type"] = "bogus"
    fails = validate_dossier(d, GATE, source_types=SOURCE_TYPES)
    assert any("unknown type" in f for f in fails)


def test_too_few_artefact_kinds():
    d = good_dossier(); d["artefacts"] = [{"kind": "yaml"}] * 3
    assert any("distinct kinds" in f for f in validate_dossier(d, GATE))


def test_missing_gaps_and_counters():
    d = good_dossier(); d["gaps"] = []; d["counter_arguments"] = []
    fails = validate_dossier(d, GATE)
    assert any("gaps" in f for f in fails) and any("counter_arguments" in f for f in fails)


def test_parse_dossier_h2_sections():
    # H2-section format; section() locates by token even with parenthetical annotations
    s = parse_dossier("# Dossier\n\n## Vendors in scope (>=3)\n- {name: a}\n")
    assert section(s, "vendors")[0]["name"] == "a"
    # frank's per-blog prefixes resolve too
    s2 = parse_dossier("## Frank artefacts (>=3)\n- {kind: yaml}\n")
    assert section(s2, "artefacts")[0]["kind"] == "yaml"


# ---- paper frontmatter + weight invariant ----

def _fm(**over):
    fm = {"title": "T", "date": "2026-01-01", "draft": False, "weight": 2,
          "series": ["papers"], "layer": "x", "paper_number": 1, "publish_order": 1,
          "status": "published", "tldr": "t"}
    fm.update(over)
    return fm


def test_paper_passes():
    assert validate_paper(_fm(), weight_offset=1) == []


def test_paper_weight_invariant_violation():
    assert any("weight invariant" in f for f in validate_paper(_fm(weight=1), weight_offset=1))


def test_paper_weight_offset_is_config_driven():
    # offset 0: weight must equal paper_number
    assert validate_paper(_fm(weight=1, paper_number=1), weight_offset=0) == []
    assert any("weight invariant" in f for f in validate_paper(_fm(weight=1, paper_number=1), weight_offset=1))


def test_paper_missing_field():
    fm = _fm(); del fm["tldr"]
    assert any("tldr" in f for f in validate_paper(fm))


# ---- sync dossier -> data ----

def test_sync_writes_and_checks(tmp_path):
    d = tmp_path / "docs" / "papers-dossiers" / "01-x"
    d.mkdir(parents=True)
    (d / "dossier.md").write_text(
        "# D\n\n## Vendors in scope\n- {name: v}\n\n## Primary sources\n- {title: a, type: paper, url: 'http://e'}\n")
    assert sync(tmp_path, "docs/papers-dossiers", "blog/data/papers") == []
    out = tmp_path / "blog" / "data" / "papers" / "01-x.yaml"
    assert out.exists()
    data = yaml.safe_load(out.read_text())
    assert data["primary_sources"][0]["type"] == "paper"
    assert set(data) == {"primary_sources"}   # data file mirrors ONLY primary_sources (frank-compatible)
    assert sync(tmp_path, "docs/papers-dossiers", "blog/data/papers", check=True) == []
