# Journal: 2026-10-12-paper-site-dir

<!-- fr:journal kind=repro scope=debug id=6c7e591973f7 created=2026-10-11T22:58:57+00:00 -->
### 6c7e591973f7 · repro · scaffold-paper.sh writes the bundle beside a site_dir Hugo site

With `site_dir: blog` and .blog-craft.yaml at the repo root, `scaffold-paper.sh --config .blog-craft.yaml 21 x` writes `content/docs/papers/21-x/index.md` at the repo root instead of `blog/content/docs/papers/21-x/index.md`. The dossier lands correctly at `docs/papers-dossiers/21-x/` (repo-relative dossier_dir). blog-craft#79.

<!-- fr:journal kind=root-cause scope=debug id=ba7fe51b567a created=2026-10-11T22:59:01+00:00 -->
### ba7fe51b567a · root-cause · BUNDLE is rooted at the config's directory; site_dir is never read

scaffold-paper.sh:35 sets ROOT to dirname(--config) and :39 builds BUNDLE=$ROOT/content/docs/<key>/<dir>. The python config read (:26-33) extracts weight_offset, dossier_dir and the papers key but not site_dir. Per templates/manifest.yaml, content/** is a site-placed path (lands under site_dir) while dossier_dir is a config-root-relative path, so only the bundle needs the site_dir prefix. glossary_scan.py:323 shows the convention: (site_dir or '.').rstrip('/').

<!-- fr:journal kind=finding scope=debug id=13cf22f97eee created=2026-10-11T23:11:58+00:00 state=fixed -->
### 13cf22f97eee · finding [fixed] · Bundle prefixed with site_dir; dossier unchanged

scaffold-paper.sh (template + tools/ mirror) reads site_dir ((site_dir or '.').rstrip('/'), the glossary_scan.py convention) and builds BUNDLE_REL=<site_dir>/content/docs/<key>/<dir>; the printed path is BUNDLE_REL. Pinned by tests/unit/test_scaffold_paper.py::test_scaffold_honours_site_dir (committed failing first). papers SKILL.md (both mirrors) documents the site prefix; matrix row UPD-R7; 0.22.6.

<!-- fr:journal kind=review scope=debug id=05e70895cae5 created=2026-10-11T23:14:25+00:00 -->
### 05e70895cae5 · review · Self-review: no findings; full suite deferred to CI

Reviewed the diff: site_dir './' and '/' fall back to '.', missing/empty keeps the old path (existing tests cover it), template and tools/ mirror byte-identical (test_mirrors), papers SKILL.md mirrors updated. Known limit shared with dossier_dir: a site_dir containing spaces would mis-split the read (not a regression). Local verification was targeted only (test_scaffold_paper, test_mirrors, test_papers_scripts: pass); the full suite runs in CI per the operator's overnight rule (evidence: tests=ci).
