"""`image.fallback_model` + `image.timeout_ms` in `_gen_bytes` (stickers P2.T1).

WHY: the default primary is a *preview* model (`gemini-3-pro-image-preview`) and
frank's private sticker generator carried a fallback to `gemini-2.5-flash-image`
for exactly that reason, plus a 120 s HTTP cap
(`frank/blog/_private/frank-stickers/generate-stickers.py:37-39,91-95,123-136`).
blog-craft's `_gen_bytes` had neither, so porting the stickers onto the shared
engine would silently change behavior on the failure path — the one path the
fallback exists for.

Test mechanics:
- `_gen_bytes` does `from google import genai` INSIDE the function, so a fake
  module injected into `sys.modules` is picked up and google-genai need not be
  installed (it is not, in the unit venv).
- `BLOG_CRAFT_TEST_MODE=1` short-circuits before the client, and the module
  reads it at IMPORT time — so these tests must not set it, and must import the
  module after clearing it.
"""

import importlib.util
import os
import sys
from types import ModuleType, SimpleNamespace

import pytest
import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEN = os.path.join(_ROOT, "templates/hugo-hextra/scripts/generate-images.py")

_PNG = b"\x89PNG\r\n\x1a\nFAKE-IMAGE-BYTES"
_ALT = b"\x89PNG\r\n\x1a\nFALLBACK-IMAGE-BYTES"


def _mod():
    """Import the hyphenated script by path (not importable as a module name)."""
    spec = importlib.util.spec_from_file_location("generate_images", GEN)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _fake_genai(behaviour: dict, calls: list) -> ModuleType:
    """A stand-in `google.genai`. `behaviour`: model -> bytes | None | Exception."""

    class _Kwargs:  # HttpOptions / GenerateContentConfig / ImageConfig
        def __init__(self, **kw):
            self.kw = kw

    class _Part:
        def __init__(self, data):
            self.inline_data = None if data is None else SimpleNamespace(data=data)

    class _Models:
        def generate_content(self, *, model, contents, config=None):
            calls.append(SimpleNamespace(model=model, contents=contents, config=config))
            out = behaviour.get(model)
            if isinstance(out, BaseException):
                raise out
            # a leading text part is normal; the image part is the one that counts
            parts = [_Part(None)] + ([_Part(out)] if out is not None else [])
            return SimpleNamespace(parts=parts)

    class Client:
        def __init__(self, api_key=None):
            self.api_key = api_key
            self.models = _Models()

    genai = ModuleType("google.genai")
    genai.Client = Client
    genai.types = SimpleNamespace(HttpOptions=_Kwargs, GenerateContentConfig=_Kwargs,
                                  ImageConfig=_Kwargs)
    return genai


def _install(monkeypatch, behaviour):
    calls = []
    genai = _fake_genai(behaviour, calls)
    pkg = ModuleType("google")
    pkg.genai = genai
    monkeypatch.setitem(sys.modules, "google", pkg)
    monkeypatch.setitem(sys.modules, "google.genai", genai)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("BLOG_CRAFT_TEST_MODE", raising=False)
    return calls


CFG = {
    "version": 5, "project": {"name": "x"}, "series": [], "voice": "v",
    "image": {"prompts_file": "prompt_for_images.yaml", "model": "primary-m",
              "fallback_model": "fallback-m",
              "composition_orders": {"hero": ["scene"]}, "layers": {}},
}
ENTRY = {"key": "k-01", "output": "static/images/k-01.png",
         "composition": {"modifiers": {}, "scene": "SCENE", "reference_images": {}}}


def _blog(tmp_path):
    (tmp_path / ".blog-craft.yaml").write_text(yaml.safe_dump(CFG))
    (tmp_path / "prompt_for_images.yaml").write_text(yaml.safe_dump({"images": [ENTRY]}))
    return tmp_path / ".blog-craft.yaml"


# --- 1. primary raises -> the fallback is attempted and its bytes come back ---

def test_primary_failure_falls_back_to_the_fallback_model(tmp_path, monkeypatch, capsys):
    calls = _install(monkeypatch, {"primary-m": RuntimeError("503 model overloaded"),
                                   "fallback-m": _ALT})
    m = _mod()
    got = m._gen_bytes("P", None, "primary-m", {"fallback_model": "fallback-m"}, {}, tmp_path)
    assert got == _ALT
    assert [c.model for c in calls] == ["primary-m", "fallback-m"]
    err = capsys.readouterr().err
    assert "primary-m" in err and "overloaded" in err   # the failure is not silent
    # the exception TYPE is named too: on the default path the operator used to
    # get a full traceback, so a truncated str() alone loses the diagnosis.
    assert "RuntimeError" in err


# --- 2. primary succeeds -> the fallback is NEVER attempted ---

def test_primary_success_never_attempts_the_fallback(tmp_path, monkeypatch):
    calls = _install(monkeypatch, {"primary-m": _PNG, "fallback-m": _ALT})
    m = _mod()
    got = m._gen_bytes("P", None, "primary-m", {"fallback_model": "fallback-m"}, {}, tmp_path)
    assert got == _PNG
    assert [c.model for c in calls] == ["primary-m"]


# --- 3. both raise -> the LAST exception propagates; nothing is written ---

def test_both_models_failing_re_raises_the_last_exception(tmp_path, monkeypatch, capsys):
    """The fallback adds a RETRY; it must not convert a hard failure into a soft
    one. Once every configured model has raised, the exception propagates — the
    pre-fallback contract, where `generate_content` was called bare and any
    error aborted the run at the first failing entry rather than plodding on
    through the remaining 90."""
    calls = _install(monkeypatch, {"primary-m": RuntimeError("boom-1"),
                                   "fallback-m": RuntimeError("boom-2")})
    m = _mod()
    with pytest.raises(RuntimeError, match="boom-2"):
        m._gen_bytes("P", None, "primary-m", {"fallback_model": "fallback-m"}, {}, tmp_path)
    assert [c.model for c in calls] == ["primary-m", "fallback-m"]
    err = capsys.readouterr().err
    assert "boom-1" in err and "boom-2" in err   # both attempts logged before the raise

    cfg = _blog(tmp_path)
    with pytest.raises(RuntimeError, match="boom-2"):
        m.main(["--config", str(cfg)])
    # no silent empty PNG: the entry's output must not exist at all
    assert not (tmp_path / "static" / "images" / "k-01.png").exists()


def test_a_hard_primary_failure_is_not_softened_by_an_image_less_fallback(tmp_path, monkeypatch):
    """The mixed case. `primary` raises, `fallback` answers without an image
    part: no model produced an image and one of them errored, so the run gets
    the exception rather than a `None` that reads as 'the model just declined'.
    'The LAST exception' is the primary's — it is the only one."""
    calls = _install(monkeypatch, {"primary-m": RuntimeError("boom-1"), "fallback-m": None})
    m = _mod()
    with pytest.raises(RuntimeError, match="boom-1"):
        m._gen_bytes("P", None, "primary-m", {"fallback_model": "fallback-m"}, {}, tmp_path)
    assert [c.model for c in calls] == ["primary-m", "fallback-m"]


# --- 4. image.timeout_ms reaches genai.types.HttpOptions(timeout=...) ---

def test_timeout_ms_reaches_http_options(tmp_path, monkeypatch):
    calls = _install(monkeypatch, {"primary-m": _PNG})
    m = _mod()
    got = m._gen_bytes("P", None, "primary-m", {"timeout_ms": 120000}, {}, tmp_path)
    assert got == _PNG
    cfg = calls[0].config
    assert cfg is not None, "a timeout_ms must produce a GenerateContentConfig"
    assert cfg.kw["http_options"].kw == {"timeout": 120000}


def test_timeout_ms_coexists_with_entry_image_config(tmp_path, monkeypatch):
    """The pre-existing aspect_ratio/image_size path must keep working."""
    calls = _install(monkeypatch, {"primary-m": _PNG})
    m = _mod()
    m._gen_bytes("P", None, "primary-m", {"timeout_ms": 90000},
                 {"aspect_ratio": "1:1"}, tmp_path)
    kw = calls[0].config.kw
    assert kw["http_options"].kw == {"timeout": 90000}
    assert kw["image_config"].kw == {"aspect_ratio": "1:1"}


# --- 5. no fallback configured -> one attempt, config unchanged (None) ---

def test_no_fallback_configured_is_a_single_attempt(tmp_path, monkeypatch):
    calls = _install(monkeypatch, {"primary-m": _PNG})
    m = _mod()
    assert m._gen_bytes("P", None, "primary-m", {}, {}, tmp_path) == _PNG
    assert [c.model for c in calls] == ["primary-m"]
    # byte-for-byte current behavior: no knobs -> no config object at all
    assert calls[0].config is None


def test_no_fallback_configured_the_single_failure_propagates(tmp_path, monkeypatch, capsys):
    """THE default-path contract, unchanged from before the fallback existed:
    with no `fallback_model` there is nothing to retry, so the one attempt's
    exception propagates out of `_gen_bytes` untouched. Absorbing it here would
    silently turn every blog's first API error from 'abort' into 'warn and keep
    generating the other 90 entries' — an undeclared behavior change on the path
    every existing blog takes."""
    calls = _install(monkeypatch, {"primary-m": RuntimeError("only-boom")})
    m = _mod()
    with pytest.raises(RuntimeError, match="only-boom"):
        m._gen_bytes("P", None, "primary-m", {}, {}, tmp_path)
    assert [c.model for c in calls] == ["primary-m"]
    assert "only-boom" in capsys.readouterr().err


# --- frank parity: a response with no image part also falls through ---

def test_response_without_an_image_part_falls_back(tmp_path, monkeypatch):
    """frank's loop only breaks on a saved image (`if ok: break`,
    generate-stickers.py:133-134), so an image-less response is a failure that
    the fallback still gets a shot at."""
    calls = _install(monkeypatch, {"primary-m": None, "fallback-m": _ALT})
    m = _mod()
    assert m._gen_bytes("P", None, "primary-m", {"fallback_model": "fallback-m"}, {},
                        tmp_path) == _ALT
    assert [c.model for c in calls] == ["primary-m", "fallback-m"]


def test_image_less_responses_stay_a_SOFT_failure(tmp_path, monkeypatch, capsys):
    """The image-less path was ALWAYS soft (`return None` -> "no image returned"
    -> rc=1) and stays soft: no exception was raised, so there is none to
    propagate. Both with and without a fallback configured."""
    _install(monkeypatch, {"primary-m": None, "fallback-m": None})
    m = _mod()
    assert m._gen_bytes("P", None, "primary-m", {"fallback_model": "fallback-m"}, {},
                        tmp_path) is None
    assert m._gen_bytes("P", None, "primary-m", {}, {}, tmp_path) is None
    assert "no image part" in capsys.readouterr().err

    # ... and end to end it is still rc=1 with nothing written, not a traceback
    cfg = _blog(tmp_path)
    assert m.main(["--config", str(cfg)]) == 1
    assert not (tmp_path / "static" / "images" / "k-01.png").exists()
