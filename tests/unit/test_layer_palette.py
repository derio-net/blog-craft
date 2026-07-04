"""tools/gen-layer-palette.py — registry-driven OKLCH palette generator.

Reads a blog's `.blog-craft.yaml` `series_index.layers` (list of {code, name}) and emits
`data/layer_palette.yaml` mapping each code -> {name, light, dark, lt, dt}.
"""
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEN = os.path.join(ROOT, "tools", "gen-layer-palette.py")


def _gen(layers, tmp_path):
    cfg = {"series_index": {"layers": layers}}
    p = tmp_path / "cfg.yaml"; p.write_text(yaml.safe_dump(cfg))
    r = subprocess.run([sys.executable, GEN, "--config", str(p)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def _registry(n):
    return [{"code": f"l{i}", "name": f"Layer {i}"} for i in range(n)]


def test_entry_per_layer_with_name_and_colours(tmp_path):
    layers = [{"code": "hw", "name": "Hardware & Nodes"}, {"code": "net", "name": "Networking"}]
    data = yaml.safe_load(_gen(layers, tmp_path))["layers"]
    for ly in layers:
        e = data[ly["code"]]
        assert e["name"] == ly["name"]
        for k in ("light", "dark"):
            assert e[k].startswith("#") and len(e[k]) == 7
        assert e["lt"] in ("#ffffff", "#1a1a2e")
        assert e["dt"] in ("#ffffff", "#1a1a2e")


def test_deterministic(tmp_path):
    layers = _registry(21)
    assert _gen(layers, tmp_path) == _gen(layers, tmp_path)


def test_unique_light_colours(tmp_path):
    data = yaml.safe_load(_gen(_registry(21), tmp_path))["layers"]
    lights = [e["light"] for e in data.values()]
    assert len(set(lights)) == len(lights), "layer colours must be unique"


def test_empty_registry_emits_no_layers(tmp_path):
    data = yaml.safe_load(_gen([], tmp_path))
    assert not (data.get("layers") or {})


# --- bootstrap materialises the palette only when the blog declares layers ---

RENDER = os.path.join(ROOT, "tools", "bootstrap-render.sh")
FIX = os.path.join(ROOT, "tests", "fixtures")


def _bootstrap(tmp_path, series_index):
    import subprocess
    cfg = yaml.safe_load(open(os.path.join(FIX, "valid-v2.blog-craft.yaml")))
    if series_index is not None:
        cfg["series_index"] = series_index
    ans = tmp_path / "ans.yaml"; ans.write_text(yaml.safe_dump(cfg))
    blog = tmp_path / "blog"
    env = {**os.environ, "PYTHON": sys.executable}   # a PyYAML-capable python for the palette step
    subprocess.run(["bash", RENDER, str(ans), str(blog)], check=True, capture_output=True, text=True, env=env)
    return blog


def test_bootstrap_generates_palette_when_layers_declared(tmp_path):
    blog = _bootstrap(tmp_path, {"style": "cards",
                                 "layers": [{"code": "api", "name": "API"},
                                            {"code": "db", "name": "Database"}]})
    pal = blog / "data" / "layer_palette.yaml"
    assert pal.exists(), "bootstrap should generate data/layer_palette.yaml"
    data = yaml.safe_load(pal.read_text())["layers"]
    assert data["api"]["name"] == "API" and data["db"]["name"] == "Database"


def test_bootstrap_no_palette_without_layers(tmp_path):
    blog = _bootstrap(tmp_path, {"style": "cards"})   # style but no layers
    assert not (blog / "data" / "layer_palette.yaml").exists()
