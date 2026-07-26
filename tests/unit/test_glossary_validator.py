"""P4 — validate_glossary.py: the CI gate for the abbreviation glossary.

Errors are things that break the promise to the reader (a marker with no
definition, a definition with no text). Warnings are hygiene (an unused entry, an
unsorted registry) and never fail a build.
"""
import os
import subprocess
import sys

import yaml

from validate_glossary import validate_glossary  # tools/ on sys.path via conftest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VALIDATE = os.path.join(ROOT, "tools", "validate_glossary.py")

GOOD = {
    "NUT": {"name": "Network UPS Tools", "description": "Monitors a UPS."},
    "SLO": {"name": "Service Level Objective", "description": "A target."},
}


def _marked(*terms):
    """A [(term, file, line)] list as the marker extractor would produce."""
    return [(t, "content/docs/x/01-y/index.md", 10 + i)
            for i, t in enumerate(terms)]


# --- errors -----------------------------------------------------------------

def test_clean_registry_and_posts_pass():
    errors, warnings = validate_glossary(GOOD, _marked("NUT", "SLO"))
    assert errors == []


def test_marker_without_a_registry_entry_is_an_error():
    errors, _ = validate_glossary(GOOD, _marked("XYZ"))
    assert len(errors) == 1
    assert "XYZ" in errors[0]
    assert "index.md" in errors[0]
    assert ":10" in errors[0]


def test_missing_name_is_an_error():
    reg = {"NUT": {"description": "d"}}
    errors, _ = validate_glossary(reg, _marked("NUT"))
    assert any("NUT" in e and "name" in e for e in errors)


def test_blank_name_is_an_error():
    reg = {"NUT": {"name": "   ", "description": "d"}}
    errors, _ = validate_glossary(reg, _marked("NUT"))
    assert any("name" in e for e in errors)


def test_missing_description_is_an_error():
    reg = {"NUT": {"name": "Network UPS Tools"}}
    errors, _ = validate_glossary(reg, _marked("NUT"))
    assert any("description" in e for e in errors)


def test_blank_description_is_an_error():
    reg = {"NUT": {"name": "N", "description": ""}}
    errors, _ = validate_glossary(reg, _marked("NUT"))
    assert any("description" in e for e in errors)


def test_relative_url_is_an_error():
    reg = {"NUT": {"name": "N", "description": "d", "url": "/local/page"}}
    errors, _ = validate_glossary(reg, _marked("NUT"))
    assert any("url" in e for e in errors)


def test_absolute_url_is_fine():
    reg = {"NUT": {"name": "N", "description": "d",
                   "url": "https://networkupstools.org"}}
    errors, _ = validate_glossary(reg, _marked("NUT"))
    assert errors == []


def test_case_colliding_keys_are_an_error():
    reg = {"NUT": {"name": "N", "description": "d"},
           "Nut": {"name": "N", "description": "d"}}
    errors, _ = validate_glossary(reg, _marked("NUT"))
    assert any("case" in e.lower() for e in errors)


def test_a_non_mapping_entry_is_an_error():
    reg = {"NUT": "Network UPS Tools"}
    errors, _ = validate_glossary(reg, _marked("NUT"))
    assert any("NUT" in e for e in errors)


# --- warnings ---------------------------------------------------------------

def test_unreferenced_entry_is_a_warning_not_an_error():
    errors, warnings = validate_glossary(GOOD, _marked("NUT"))
    assert errors == []
    assert any("SLO" in w for w in warnings)


def test_unsorted_registry_is_a_warning_not_an_error():
    reg = {"SLO": GOOD["SLO"], "NUT": GOOD["NUT"]}
    errors, warnings = validate_glossary(reg, _marked("NUT", "SLO"))
    assert errors == []
    assert any("sorted" in w.lower() for w in warnings)


def test_sorted_registry_warns_nothing_about_order():
    _, warnings = validate_glossary(GOOD, _marked("NUT", "SLO"))
    assert not any("sorted" in w.lower() for w in warnings)


# --- CLI --------------------------------------------------------------------

def _blog(tmp_path, registry, body):
    blog = tmp_path / "blog"
    post_dir = blog / "content" / "docs" / "series" / "01-post"
    post_dir.mkdir(parents=True)
    (blog / "data").mkdir(parents=True, exist_ok=True)
    (blog / ".blog-craft.yaml").write_text(yaml.safe_dump({"version": 5}))
    (blog / "data" / "glossary.yaml").write_text(yaml.safe_dump(registry))
    post = post_dir / "index.md"
    post.write_text(body)
    return blog, post


def _run(blog, post):
    return subprocess.run(
        [sys.executable, VALIDATE, "--config", str(blog / ".blog-craft.yaml"), str(post)],
        capture_output=True, text=True)


def test_cli_passes_on_a_clean_blog(tmp_path):
    blog, post = _blog(tmp_path, GOOD, 'we ran {{< abbr "NUT" >}} and {{< abbr "SLO" >}}\n')
    r = _run(blog, post)
    assert r.returncode == 0, r.stderr
    assert "OK" in r.stdout


def test_cli_fails_on_a_dangling_marker(tmp_path):
    blog, post = _blog(tmp_path, GOOD, 'we ran {{< abbr "XYZ" >}}\n')
    r = _run(blog, post)
    assert r.returncode == 1
    assert "XYZ" in r.stderr


def test_cli_exits_zero_with_only_warnings(tmp_path):
    blog, post = _blog(tmp_path, GOOD, 'we ran {{< abbr "NUT" >}}\n')
    r = _run(blog, post)
    assert r.returncode == 0, r.stderr
    assert "SLO" in r.stderr          # the unused-entry warning
    assert "OK" in r.stdout


def test_cli_exits_one_when_errors_and_warnings_coexist(tmp_path):
    blog, post = _blog(tmp_path, GOOD, 'we ran {{< abbr "XYZ" >}}\n')
    r = _run(blog, post)
    assert r.returncode == 1


def test_cli_ignores_markers_inside_code_fences(tmp_path):
    # A post DOCUMENTING the shortcode must not be gated on it.
    body = 'Use it like this:\n\n```\n{{< abbr "XYZ" >}}\n```\n'
    blog, post = _blog(tmp_path, GOOD, body)
    r = _run(blog, post)
    assert r.returncode == 0, r.stderr + r.stdout


def test_a_key_containing_a_quote_is_an_error():
    # The marker is {{< abbr "KEY" >}} — a quote in the key would terminate the
    # argument early and emit a shortcode Hugo cannot parse. Unreachable for
    # scanner-proposed terms; reachable for a hand-added entry.
    reg = {'A"B': {"name": "N", "description": "d"}}
    errors, _ = validate_glossary(reg, [])
    assert any("quote" in e.lower() for e in errors)
