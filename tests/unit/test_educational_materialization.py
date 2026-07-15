"""The blog-side validator copy must stay byte-identical to the plugin's.

`tools/validate_educational.py` is what the skills call; the copy at
`templates/hugo-hextra/scripts/validate_educational.py` is what ships into every
blog and runs in the blog's CI. They must not drift (same convention as the
papers validators).
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLUGIN = os.path.join(ROOT, "tools", "validate_educational.py")
BLOG = os.path.join(ROOT, "templates", "hugo-hextra", "scripts", "validate_educational.py")


def test_both_copies_exist():
    assert os.path.isfile(PLUGIN)
    assert os.path.isfile(BLOG)


def test_validator_copies_are_identical():
    assert open(PLUGIN, "rb").read() == open(BLOG, "rb").read(), (
        "tools/validate_educational.py and templates/hugo-hextra/scripts/"
        "validate_educational.py have drifted — re-sync them (they must be "
        "byte-identical)."
    )
