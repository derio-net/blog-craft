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

from path_ownership import load_manifest, root_of  # tools/ on sys.path

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST = os.path.join(ROOT, "templates", "manifest.yaml")

# The --src roots bootstrap-render.sh renders. Wider than the class guard in
# test_path_manifest.py (hugo-hextra only), because the opt-in content types and
# feature bundles materialize paths too.
SRC_ROOTS = (
    "templates/hugo-hextra",
    "templates/content-type-papers/shared",
    "templates/content-type-explainers/shared",
    "templates/features/read-tracker",
    "templates/features/analytics",
    "templates/features/glossary",
)

M = load_manifest(MANIFEST)


def _materialized_paths():
    out = []
    for src in SRC_ROOTS:
        base = os.path.join(ROOT, src)
        for dp, _, fs in os.walk(base):
            for f in fs:
                rel = os.path.relpath(os.path.join(dp, f), base)
                out.append(rel[:-len(".tmpl")] if rel.endswith(".tmpl") else rel)
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
    assert any(p.startswith("scripts/") for p in paths)
    assert any(p.startswith("layouts/") for p in paths)
