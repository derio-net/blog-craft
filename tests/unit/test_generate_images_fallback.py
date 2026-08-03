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


# --- 2. primary succeeds -> the fallback is NEVER attempted ---

def test_primary_success_never_attempts_the_fallback(tmp_path, monkeypatch):
    calls = _install(monkeypatch, {"primary-m": _PNG, "fallback-m": _ALT})
    m = _mod()
    got = m._gen_bytes("P", None, "primary-m", {"fallback_model": "fallback-m"}, {}, tmp_path)
    assert got == _PNG
    assert [c.model for c in calls] == ["primary-m"]


# --- 3. both raise -> failure is reported, exit non-zero, no image written ---

def test_both_models_failing_reports_and_exits_non_zero(tmp_path, monkeypatch, capsys):
    calls = _install(monkeypatch, {"primary-m": RuntimeError("boom-1"),
                                   "fallback-m": RuntimeError("boom-2")})
    m = _mod()
    assert m._gen_bytes("P", None, "primary-m", {"fallback_model": "fallback-m"}, {},
                        tmp_path) is None
    assert [c.model for c in calls] == ["primary-m", "fallback-m"]

    cfg = _blog(tmp_path)
    rc = m.main(["--config", str(cfg)])
    assert rc == 1
    out = capsys.readouterr()
    assert "boom-1" in out.err and "boom-2" in out.err
    # no silent empty PNG: the entry's output must not exist at all
    assert not (tmp_path / "static" / "images" / "k-01.png").exists()


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


def test_no_fallback_configured_failure_propagates_nothing_extra(tmp_path, monkeypatch, capsys):
    calls = _install(monkeypatch, {"primary-m": RuntimeError("only-boom")})
    m = _mod()
    assert m._gen_bytes("P", None, "primary-m", {}, {}, tmp_path) is None
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
