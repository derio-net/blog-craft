"""tools/blog_config.py — the dotted-path config reader the scaffolder uses (spec D4).

blog-post-create.sh must READ the config it already requires (#39 item 1); a
tiny python reader is the testable seam. `get <dotted.key>` prints the value;
`--default` supplies a fallback; a missing key without a default exits 1.
"""
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(ROOT, "tools", "blog_config.py")


def _cfg(tmp_path, data):
    p = tmp_path / ".blog-craft.yaml"
    p.write_text(yaml.safe_dump(data))
    return str(p)


def _run(cfg, *args):
    return subprocess.run([sys.executable, TOOL, "--config", cfg, *args],
                          capture_output=True, text=True)


def test_get_nested_key(tmp_path):
    cfg = _cfg(tmp_path, {"image": {"prompts_file": "blog/prompt_for_images.yaml"}})
    r = _run(cfg, "get", "image.prompts_file")
    assert r.returncode == 0
    assert r.stdout.strip() == "blog/prompt_for_images.yaml"


def test_get_missing_with_default(tmp_path):
    cfg = _cfg(tmp_path, {"image": {}})
    r = _run(cfg, "get", "site_dir", "--default", ".")
    assert r.returncode == 0
    assert r.stdout.strip() == "."


def test_get_present_beats_default(tmp_path):
    cfg = _cfg(tmp_path, {"site_dir": "blog"})
    r = _run(cfg, "get", "site_dir", "--default", ".")
    assert r.returncode == 0
    assert r.stdout.strip() == "blog"


def test_get_missing_without_default_fails(tmp_path):
    cfg = _cfg(tmp_path, {"image": {}})
    r = _run(cfg, "get", "image.nope")
    assert r.returncode == 1


def test_mirror_is_byte_identical():
    mirror = os.path.join(ROOT, "templates", "hugo-hextra", "scripts", "blog_config.py")
    with open(TOOL, "rb") as a, open(mirror, "rb") as b:
        assert a.read() == b.read(), "tools/blog_config.py and its scripts/ mirror drifted"
