"""gen-character-sheet.py must call _gen_bytes signature-compatibly (#39 / PR #40).

PR #40 added a required `root` parameter to `_gen_bytes` in generate-images.py
so entry `references:` anchors can resolve against the blog root. The
character-sheet tool is the SECOND caller of `_gen_bytes` and was missed there,
failing the bootstrap smoke with:

    TypeError: _gen_bytes() missing 1 required positional argument: 'root'

This guard binds the call site's positional arity against the real signature,
so the two files cannot silently drift again — any future signature change
must update both callers or this test goes red.
"""

import ast
import importlib.util
import inspect
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEN = os.path.join(_ROOT, "templates/hugo-hextra/scripts/generate-images.py")
SHEET = os.path.join(_ROOT, "templates/hugo-hextra/scripts/gen-character-sheet.py")


def _load_gen():
    spec = importlib.util.spec_from_file_location("genimg_for_sheet_guard", GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sheet_gen_bytes_calls():
    with open(SHEET) as f:
        tree = ast.parse(f.read())
    calls = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_gen_bytes"
        ):
            calls.append(node)
    return calls


def test_sheet_calls_gen_bytes():
    assert _sheet_gen_bytes_calls(), "gen-character-sheet.py no longer calls _gen_bytes"


def test_sheet_call_binds_gen_bytes_signature():
    sig = inspect.signature(_load_gen()._gen_bytes)
    for call in _sheet_gen_bytes_calls():
        kwargs = {k.arg: None for k in call.keywords}
        # raises TypeError when the call site's arity can't bind the signature
        sig.bind(*range(len(call.args)), **kwargs)
