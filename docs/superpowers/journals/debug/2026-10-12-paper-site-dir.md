# Journal: 2026-10-12-paper-site-dir

<!-- fr:journal kind=repro scope=debug id=6c7e591973f7 created=2026-10-11T22:58:57+00:00 -->
### 6c7e591973f7 · repro · scaffold-paper.sh writes the bundle beside a site_dir Hugo site

With `site_dir: blog` and .blog-craft.yaml at the repo root, `scaffold-paper.sh --config .blog-craft.yaml 21 x` writes `content/docs/papers/21-x/index.md` at the repo root instead of `blog/content/docs/papers/21-x/index.md`. The dossier lands correctly at `docs/papers-dossiers/21-x/` (repo-relative dossier_dir). blog-craft#79.
