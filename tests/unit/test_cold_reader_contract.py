"""P4 — cold-reader agent contract + drafting-skill wiring.

Grep-style contract tests, same style as test_reader_arc_contract.py: they pin
the load-bearing strings of the agent definition (read-only tools, the five
critique sections, the blindness sentence) without judging the prose itself.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COLD_READER = os.path.join(ROOT, "agents", "cold-reader.md")

BLINDNESS_SENTENCE = (
    "You receive only the draft and the methodology — never the session "
    "context, the evidence brief, or the source repo."
)

CRITIQUE_SECTIONS = [
    "Takeaway mirror",
    "Lost points",
    "Session residue",
    "Arc assessment",
    "AI-tell instances",
]


def _read(path):
    assert os.path.exists(path), f"missing file: {path}"
    with open(path) as f:
        return f.read()


def _frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "no yaml frontmatter block"
    return m.group(1)


# ---- agents/cold-reader.md ----

def test_cold_reader_exists():
    assert os.path.exists(COLD_READER), f"missing file: {COLD_READER}"


def test_cold_reader_tools_are_read_only():
    """The frontmatter tools line lists ONLY Read, Grep, Glob — the blindness
    is enforced by capability, not just prose."""
    fm = _frontmatter(_read(COLD_READER))
    m = re.search(r"^tools:\s*(.+)$", fm, re.MULTILINE)
    assert m, "no tools line in frontmatter"
    tools = {t.strip() for t in m.group(1).split(",")}
    assert tools == {"Read", "Grep", "Glob"}, f"unexpected tools: {tools}"


def test_cold_reader_has_five_critique_sections():
    text = _read(COLD_READER)
    for section in CRITIQUE_SECTIONS:
        assert section in text, f"missing critique section: {section}"


def test_cold_reader_states_blindness_verbatim():
    assert BLINDNESS_SENTENCE in _read(COLD_READER)


# ---- /blog-post wiring ----

BLOG_POST = os.path.join(ROOT, "skills", "blog-post", "SKILL.md")
POST_REWRITE = os.path.join(ROOT, "skills", "post-rewrite", "SKILL.md")


def _step_block(text, step):
    """The block of a '### Step N' heading, up to the next '### ' heading."""
    parts = text.split(f"### Step {step}")
    assert len(parts) > 1, f"no '### Step {step}' heading"
    return parts[1].split("\n### ")[0]


def test_blog_post_step4_loads_arc_and_tells_references():
    step4 = _step_block(_read(BLOG_POST), 4)
    assert "reader-arc.md" in step4
    assert "ai-tells.md" in step4


def test_blog_post_step4_dispatches_cold_reader_before_approval():
    """The cold-reader critique sub-step sits between composing the body and
    the approve question."""
    step4 = _step_block(_read(BLOG_POST), 4)
    assert "cold-reader" in step4
    assert "critique" in step4
    body_at = step4.index("**Body.**")
    dispatch_at = step4.index("cold-reader")
    approve_at = step4.index("Approve body")
    assert body_at < dispatch_at < approve_at, (
        "cold-reader dispatch must come after body composition and before "
        "the approval question"
    )


def test_blog_post_step0_seeds_quality_lint_enabled():
    step0 = _step_block(_read(BLOG_POST), 0)
    assert "quality.lint.enabled" in step0


# ---- /post-rewrite wiring ----

def test_post_rewrite_loads_arc_and_tells_references():
    text = _read(POST_REWRITE)
    assert "reader-arc.md" in text
    assert "ai-tells.md" in text


def test_post_rewrite_step0_seeds_quality_lint_enabled():
    """rev-imp-4: /post-rewrite runs the same lint gate as /blog-post, so its
    Step 0 must seed quality.lint.enabled the same way."""
    step0 = _step_block(_read(POST_REWRITE), 0)
    assert "quality.lint.enabled" in step0


def test_post_rewrite_dispatches_cold_reader_before_approval():
    text = _read(POST_REWRITE)
    assert "cold-reader" in text
    assert "critique" in text
    dispatch_at = text.index("cold-reader")
    approve_at = text.index("Approve rewrite?")
    assert dispatch_at < approve_at, (
        "cold-reader dispatch must come before the approval question"
    )
