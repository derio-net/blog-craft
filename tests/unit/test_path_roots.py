"""P2 — every materialized path declares its ROOT (blog-craft#61).

`map_dest` used to carry a three-entry allowlist and site-prefix everything
else. `.github/**` fell into "everything else", so for a `site_dir` blog the CI
workflow was materialized to `<site_dir>/.github/workflows/`, where GitHub
Actions never looks. Nothing surfaced it: no error, no skipped run, no empty
check — just an inert YAML document that looks exactly like a workflow.

The distinction the allowlist was groping for is not "dotfile" and not "special
case". It is:

    Who defines this path's location — the Hugo site, or a tool that reads it
    from the REPOSITORY root?

`templates/manifest.yaml` answers it explicitly, in a `roots:` section shaped
like the class model it sits beside, and this module is the completeness guard:
a new template file cannot merge without a reviewer answering the question.
"""
import os
import re

from path_ownership import load_manifest, root_of  # tools/ on sys.path

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST = os.path.join(ROOT, "templates", "manifest.yaml")

RENDER_SH = os.path.join(ROOT, "tools", "bootstrap-render.sh")

# Wider than the class guard in test_path_manifest.py (hugo-hextra only): the
# opt-in content types and feature bundles materialize paths too. Each render
# pass is a (source tree, destination under $TARGET) pair — most land at the
# blog root, the per-series passes at content/docs/.
_RENDER_RE = re.compile(
    r'--src\s+"\$PLUGIN_ROOT/(templates/[^"]+)"\s+--dst\s+"\$TARGET(?:/([^"]*))?"')


def _render_passes():
    """Every (src, dst-prefix) pass bootstrap-render.sh runs, read from the script.

    Derived rather than listed: a new bundle is added by giving
    bootstrap-render.sh another `--src`, and a hand-maintained list here would
    silently stop covering it — which is exactly the class of drift this module
    exists to catch.
    """
    passes = sorted(set(_RENDER_RE.findall(open(RENDER_SH).read())))
    assert passes, "no render passes found in bootstrap-render.sh — has the call shape changed?"
    return [(src, dst or "") for src, dst in passes]


def _src_roots():
    return sorted({src for src, _ in _render_passes()})


M = load_manifest(MANIFEST)


def _materialized_paths():
    out = []
    for src, dst in _render_passes():
        base = os.path.join(ROOT, src)
        for dp, _, fs in os.walk(base):
            for f in fs:
                rel = os.path.relpath(os.path.join(dp, f), base)
                if rel.endswith(".tmpl"):
                    rel = rel[:-len(".tmpl")]
                # A --per-series pass adds a <series.key>/ level under dst; any
                # deeper path still sits under the same declared root, so the
                # prefix alone is enough to place it.
                out.append(f"{dst}/{rel}" if dst else rel)
    return sorted(set(out))


# --- the two roots ------------------------------------------------------------

def test_github_workflows_are_repo_rooted():
    """GitHub Actions loads workflows from <repo>/.github/workflows/ only."""
    assert root_of(".github/workflows/blog-ci.yml", M) == "repo"


def test_claude_dir_is_repo_rooted():
    """hookify globs .claude/hookify.*.local.md from the project root."""
    assert root_of(".claude/hookify.warn-hextra-weight-zero.local.md", M) == "repo"


def test_the_config_and_its_declared_relocations_are_repo_rooted():
    for p in (".blog-craft.yaml", "prompt_for_images.yaml", ".reference-pool/README.md"):
        assert root_of(p, M) == "repo", p


def test_hugo_owned_paths_are_site_rooted():
    for p in ("layouts/baseof.html", "assets/css/custom.css", "content/_index.md",
              "static/images/.gitkeep", "hugo.toml", "go.mod", "scripts/compose.py",
              "README.md", "MEDIA-GUIDE.md", ".gitignore"):
        assert root_of(p, M) == "site", p


def test_an_undeclared_path_defaults_to_site():
    """Fail-safe: byte-identical to the pre-root-model behaviour.

    A template file someone forgets to declare must never break a blog at
    runtime. The enforcement is the guard below — a test, not a crash.
    """
    assert root_of("some/brand/new/path.html", M) == "site"


# --- the completeness guard ---------------------------------------------------

def test_every_materialized_path_matches_exactly_one_root():
    roots = M.get("roots") or {}
    from path_ownership import _matches
    for p in _materialized_paths():
        hits = [r for r, globs in roots.items() if any(_matches(g, p) for g in globs)]
        assert len(hits) == 1, (
            f"{p} matches roots {hits} (want exactly one).\n"
            "Answer the question in templates/manifest.yaml: who defines this "
            "path's location — the Hugo site, or a tool that reads it from the "
            "repository root?")


def test_the_guard_actually_covers_the_paths_that_regressed():
    """A guard that walks the wrong tree proves nothing."""
    paths = _materialized_paths()
    assert ".github/workflows/blog-ci.yml" in paths
    assert ".claude/hookify.warn-hextra-weight-zero.local.md" in paths
    assert any(p.startswith("scripts/") for p in paths)
    assert any(p.startswith("layouts/") for p in paths)


def test_the_src_roots_track_bootstrap_render():
    """Every opt-in bundle is covered, not just the always-on template."""
    roots = _src_roots()
    assert "templates/hugo-hextra" in roots
    # the opt-in bundles — the ones a hand-maintained list would have missed
    assert any("content-type-papers" in r for r in roots)
    assert any("content-type-explainers" in r for r in roots)
    assert sum(1 for r in roots if r.startswith("templates/features/")) >= 3
