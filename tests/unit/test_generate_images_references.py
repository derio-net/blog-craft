"""An image entry's `references:` anchors must reach the model (#39).

`reference_guidance` prose promises the model that additional reference images
are "clothing/pose anchors", and the entry schema carries a `references:` list —
but `_gen_bytes` only ever appended the single master reference, so those anchors
were inert. Covers then drift off the declared clothing/torso variant, because
only the text layer carries it.

Provenance: frank's pre-cutover `scripts/generate-all-images.py` did pass them
(`contents = [full_prompt, reference_image]; contents.extend(explicit_images)`).
The blog-craft cutover proved "image-compose parity" on the composed PROMPT TEXT
— the one thing that had not regressed — and nothing asserted which IMAGES were
sent, so the payload silently shrank. These guards assert the payload, because a
text-only parity check structurally cannot catch this.

ORDER is load-bearing: the master sheet stays FIRST (it is canonical for the
face); entry anchors are appended after it.
"""

import importlib.util
import inspect
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEN = os.path.join(_ROOT, "templates/hugo-hextra/scripts/generate-images.py")


def _mod():
    """Import the hyphenated script by path (not importable as a module name)."""
    spec = importlib.util.spec_from_file_location("generate_images", GEN)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_entry_references_resolve_against_blog_root(tmp_path):
    m = _mod()
    d = tmp_path / ".reference-pool/building/subjects"
    d.mkdir(parents=True)
    a = d / "a.png"
    a.write_bytes(b"x")
    entry = {"references": [".reference-pool/building/subjects/a.png"]}
    assert m.entry_reference_paths(entry, tmp_path) == [a]


def test_missing_reference_is_skipped_not_fatal(tmp_path):
    """A stale path in one entry must not block generating its cover."""
    m = _mod()
    (tmp_path / "refs").mkdir()
    good = tmp_path / "refs/good.png"
    good.write_bytes(b"x")
    entry = {"references": ["refs/missing.png", "refs/good.png"]}
    assert m.entry_reference_paths(entry, tmp_path) == [good]


def test_declared_order_is_preserved(tmp_path):
    m = _mod()
    (tmp_path / "refs").mkdir()
    for n in ("one", "two", "three"):
        (tmp_path / f"refs/{n}.png").write_bytes(b"x")
    entry = {"references": ["refs/two.png", "refs/one.png", "refs/three.png"]}
    got = [p.name for p in m.entry_reference_paths(entry, tmp_path)]
    assert got == ["two.png", "one.png", "three.png"]


def test_absent_or_empty_references_yields_nothing(tmp_path):
    m = _mod()
    assert m.entry_reference_paths({}, tmp_path) == []
    assert m.entry_reference_paths({"references": []}, tmp_path) == []
    assert m.entry_reference_paths({"references": None}, tmp_path) == []


def test_gen_bytes_takes_root_so_entry_refs_can_resolve():
    """The regression was structural: `_gen_bytes` had no way to resolve the
    entry's blog-root-relative reference paths, so it could not pass them."""
    m = _mod()
    params = list(inspect.signature(m._gen_bytes).parameters)
    assert "entry" in params and "root" in params, params


def test_master_reference_stays_first_in_the_payload():
    """`reference_guidance` declares the FIRST image canonical for the face, so
    entry anchors must be appended AFTER the master sheet, never before."""
    m = _mod()
    src = inspect.getsource(m._gen_bytes)
    master_at = src.index("contents.append(Image.open(ref))")
    entry_at = src.index("entry_reference_paths(entry, root)")
    assert master_at < entry_at, "entry references must be appended after the master sheet"
