"""P1 — the sync snapshot (blog-craft#60).

`.blog-craft.sync.yaml` records the config as of the last successful sync so
`update.py` can render an honest 3-way base — `render(config_at_last_sync,
templates_at_recorded_version)` — instead of feeding the old templates whatever
the operator edited five minutes ago.

Two properties carry the whole design and are asserted hard here:
  * the payload is the config VERBATIM (a byte copy, not a YAML round-trip), so
    the old templates get exactly what they got at sync time; and
  * the write is DETERMINISTIC — no timestamp — because
    tests/reproduction/test_golden_configs.py renders a config twice and demands
    zero structural drift between the two trees.
"""
import subprocess
import sys

import yaml

import sync_state

CONFIG = """\
# stoa's blog — hand-annotated, key order is meaningful to its author
site_dir: blog
features:
  glossary:
    enabled: false      # trailing comment
  read_tracker: true
blog_craft_version: "v0.13.0"
"""


def _write_config(tmp_path, text=CONFIG, name=".blog-craft.yaml"):
    p = tmp_path / name
    p.write_text(text)
    return p


def test_snapshot_path_sits_beside_the_config(tmp_path):
    assert sync_state.snapshot_path(tmp_path) == tmp_path / ".blog-craft.sync.yaml"
    assert sync_state.SNAPSHOT_NAME == ".blog-craft.sync.yaml"


def test_write_snapshot_copies_the_config_verbatim(tmp_path):
    cfg = _write_config(tmp_path)
    blog = tmp_path / "blog"
    blog.mkdir()
    dest = sync_state.write_snapshot(cfg, blog)

    body = dest.read_bytes()
    # the config's own bytes survive intact — comments, key order, spacing
    assert cfg.read_bytes() in body
    assert b"# trailing comment" in body
    assert body.index(b"site_dir") < body.index(b"features")


def test_header_is_comment_only_so_the_payload_still_parses(tmp_path):
    cfg = _write_config(tmp_path)
    dest = sync_state.write_snapshot(cfg, tmp_path)

    header = dest.read_text()[: dest.read_text().index("site_dir")]
    assert header.strip(), "a snapshot with no provenance header is a mystery file"
    for line in header.splitlines():
        assert not line.strip() or line.lstrip().startswith("#"), \
            f"header line is not a YAML comment: {line!r}"

    # what the renderer will see is the original mapping, unchanged
    assert yaml.safe_load(dest.read_text()) == yaml.safe_load(cfg.read_text())


def test_header_explains_itself_and_cites_the_issue(tmp_path):
    dest = sync_state.write_snapshot(_write_config(tmp_path), tmp_path)
    text = dest.read_text()
    assert "GENERATED" in text and "DO NOT EDIT" in text
    assert "#60" in text, "the header should point at the issue that explains why it exists"


def test_write_is_deterministic_no_timestamp(tmp_path):
    # test_golden_configs.py renders the same config twice and asserts zero
    # structural drift; a clock in the header would make every render differ.
    cfg = _write_config(tmp_path)
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    assert sync_state.write_snapshot(cfg, a).read_bytes() == \
        sync_state.write_snapshot(cfg, b).read_bytes()


def test_write_snapshot_overwrites_a_previous_snapshot(tmp_path):
    blog = tmp_path / "blog"
    blog.mkdir()
    sync_state.write_snapshot(_write_config(tmp_path, "old: 1\n"), blog)
    sync_state.write_snapshot(_write_config(tmp_path, "new: 2\n"), blog)
    body = sync_state.snapshot_path(blog).read_text()
    assert "new: 2" in body and "old: 1" not in body


def test_write_snapshot_creates_a_missing_blog_root(tmp_path):
    cfg = _write_config(tmp_path)
    dest = sync_state.write_snapshot(cfg, tmp_path / "does" / "not" / "exist")
    assert dest.is_file()


def test_read_snapshot_returns_the_path_when_present(tmp_path):
    sync_state.write_snapshot(_write_config(tmp_path), tmp_path)
    assert sync_state.read_snapshot(tmp_path) == sync_state.snapshot_path(tmp_path)


def test_read_snapshot_is_none_when_absent(tmp_path):
    assert sync_state.read_snapshot(tmp_path) is None


def test_read_snapshot_is_none_when_empty_or_blank(tmp_path):
    for content in ("", "   \n\n\t\n"):
        sync_state.snapshot_path(tmp_path).write_text(content)
        assert sync_state.read_snapshot(tmp_path) is None, repr(content)


def test_read_snapshot_is_none_when_header_only(tmp_path):
    # a truncated write leaves the comment header with no config behind it —
    # rendering that would fail, so the caller must see "no snapshot" instead.
    sync_state.snapshot_path(tmp_path).write_text("# only a header\n#\n\n")
    assert sync_state.read_snapshot(tmp_path) is None


def test_read_snapshot_is_none_when_it_is_a_directory(tmp_path):
    sync_state.snapshot_path(tmp_path).mkdir()
    assert sync_state.read_snapshot(tmp_path) is None


def test_module_imports_nothing_outside_the_stdlib(tmp_path):
    # bootstrap-render.sh calls this with a bare `python3` that may have no
    # PyYAML — the same machine the layer-palette step warns about.
    r = subprocess.run([sys.executable, "-S", "-c",
                        f"import sys; sys.path.insert(0, {str(sync_state.__file__)!r}"
                        f".rsplit('/', 1)[0]); import sync_state"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_cli_writes_the_snapshot(tmp_path):
    cfg = _write_config(tmp_path)
    blog = tmp_path / "blog"
    blog.mkdir()
    r = subprocess.run([sys.executable, sync_state.__file__,
                        "--config", str(cfg), "--blog", str(blog)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert str(sync_state.snapshot_path(blog)) in r.stdout
    assert "site_dir: blog" in sync_state.snapshot_path(blog).read_text()


def test_cli_fails_loudly_on_a_missing_config(tmp_path):
    r = subprocess.run([sys.executable, sync_state.__file__,
                        "--config", str(tmp_path / "nope.yaml"), "--blog", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert "nope.yaml" in r.stderr
