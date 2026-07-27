"""P3 — the hookify guard ships where hookify actually looks (blog-craft#61).

#61 flagged `.hookify.warn-hextra-weight-zero.md` as *probably* having the same
shape as `.github/**` and asked for verification rather than assertion. Verified
against hookify's own loader (`plugins/hookify/core/config_loader.py`):

    pattern = os.path.join('.claude', 'hookify.*.local.md')
    files = glob.glob(pattern)

— relative to the process CWD, i.e. the Claude Code project root. The shipped
file matched **neither the directory nor the filename**, so it had never loaded
for ANY blog, `site_dir` or not. That is worse than #61 suspected: not another
`site_dir` casualty, a file that was inert everywhere.

Corroborating evidence in the wild: the blog the issues were filed from carries
a hand-written `.claude/hookify.warn-hextra-weight-zero.local.md` beside the
inert shipped copy — the operator had to write their own.

The rule's own `file_path` pattern has the same bug one level down: hookify
matches paths from the project root, so on a `site_dir` blog the pattern has to
be `<site_dir>/content/…`. That is why the file is a template.
"""
import os
import shutil
import subprocess

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENDERER = os.path.join(ROOT, "tools", "render-template")
TPL_DIR = os.path.join(ROOT, "templates", "hugo-hextra", ".claude")
TPL = os.path.join(TPL_DIR, "hookify.warn-hextra-weight-zero.local.md.tmpl")

#: The one shape hookify's glob will find. Both halves matter — the directory
#: AND the `.local.md` suffix.
DISCOVERABLE = ".claude/hookify.warn-hextra-weight-zero.local.md"

pytestmark = pytest.mark.skipif(shutil.which("go") is None, reason="needs the Go renderer")


def _render(cfg, tmp_path):
    src = tmp_path / "src" / ".claude"
    src.mkdir(parents=True)
    shutil.copy(TPL, src / "hookify.warn-hextra-weight-zero.local.md.tmpl")
    dst = tmp_path / "dst"; dst.mkdir()
    ans = tmp_path / "a.yaml"; ans.write_text(yaml.safe_dump(cfg))
    subprocess.run(["go", "run", ".", "--src", str(tmp_path / "src"), "--dst", str(dst),
                    "--answers", str(ans)],
                   cwd=RENDERER, check=True, capture_output=True, text=True)
    return dst / ".claude" / "hookify.warn-hextra-weight-zero.local.md"


def _frontmatter(text):
    assert text.startswith("---"), "hookify requires YAML frontmatter as the first thing"
    return yaml.safe_load(text.split("---", 2)[1])


def test_the_template_lives_at_the_only_path_hookify_globs():
    assert os.path.exists(TPL), (
        "hookify globs .claude/hookify.*.local.md from the project root; a rule "
        "anywhere else — or without the .local.md suffix — is never loaded")


def test_the_old_inert_path_is_gone():
    assert not os.path.exists(
        os.path.join(ROOT, "templates", "hugo-hextra", ".hookify.warn-hextra-weight-zero.md")), \
        "the pre-#61 path was never discoverable; it must not ship alongside the fix"


def test_renders_to_the_discoverable_filename(tmp_path):
    out = _render({"project": {"name": "x"}}, tmp_path)
    assert out.exists()
    assert str(out).endswith(DISCOVERABLE)


def test_pattern_is_repo_relative_without_site_dir(tmp_path):
    fm = _frontmatter(_render({"project": {"name": "x"}}, tmp_path).read_text())
    path_cond = [c for c in fm["conditions"] if c["field"] == "file_path"][0]
    assert path_cond["pattern"] == r"content/.*\.md$"


def test_pattern_carries_the_site_prefix_for_a_site_dir_blog(tmp_path):
    """hookify reports file_path from the project root — so must the pattern."""
    fm = _frontmatter(_render({"site_dir": "blog"}, tmp_path).read_text())
    path_cond = [c for c in fm["conditions"] if c["field"] == "file_path"][0]
    assert path_cond["pattern"] == r"blog/content/.*\.md$"


def test_explicit_dot_site_dir_is_not_prefixed(tmp_path):
    fm = _frontmatter(_render({"site_dir": "."}, tmp_path).read_text())
    path_cond = [c for c in fm["conditions"] if c["field"] == "file_path"][0]
    assert path_cond["pattern"] == r"content/.*\.md$"


def test_rendered_rule_has_the_shape_hookify_parses(tmp_path):
    fm = _frontmatter(_render({"site_dir": "blog"}, tmp_path).read_text())
    assert fm["name"] == "warn-hextra-weight-zero"
    assert fm["enabled"] is True
    assert fm["event"] == "file"
    assert fm["action"] == "warn"
    assert len(fm["conditions"]) == 2
    assert {c["field"] for c in fm["conditions"]} == {"file_path", "content"}


def test_the_message_body_survives_templating(tmp_path):
    body = _render({"site_dir": "blog"}, tmp_path).read_text().split("---", 2)[2]
    assert "weight: 0" in body and "Hextra sidebar" in body


def test_blog_craft_claims_only_the_file_it_ships(tmp_path):
    """The framework glob must not swallow an operator's own .claude/ files.

    `.claude/**` would classify `.claude/settings.json`, `.claude/commands/…`
    and anything else a blog keeps there — which reproduce.py then reports as
    `missing in generated` drift, and /update treats as blog-craft's to
    overwrite. blog-craft ships exactly one file under .claude/ and owns only
    that one.
    """
    from path_ownership import classify, load_manifest

    m = load_manifest(os.path.join(ROOT, "templates", "manifest.yaml"))
    assert classify(DISCOVERABLE, m) == "framework"
    for operator_owned in (".claude/settings.json", ".claude/commands/x.md",
                           ".claude/agents/reviewer.md", ".claude/launch.json"):
        assert classify(operator_owned, m) is None, (
            f"{operator_owned} is the operator's, not blog-craft's")
