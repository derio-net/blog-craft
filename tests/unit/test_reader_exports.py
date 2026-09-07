"""Publication boundaries and semantic fidelity of reader exports."""
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / 'templates/features/reader-experience'
spec = importlib.util.spec_from_file_location('reader_export', TEMPLATES / 'scripts/export-content.py')
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


def fixture_catalog(tmp_path, body):
    page = tmp_path / 'docs/example'
    page.mkdir(parents=True)
    (page / 'index.html').write_text('<main id="content"><nav>Do not export</nav><div data-article-body>' + body + '</div></main>')
    article = dict(title='Example', url='https://example.org/blog/docs/example/', published='2026-01-01', updated='2026-01-02')
    catalog = dict(site='https://example.org/blog/', articles=[article])
    (tmp_path / 'content-index.json').write_text(json.dumps(catalog))
    return page, catalog


def test_export_preserves_code_tables_glossary_references_and_links(tmp_path):
    source = 'first\n\n\n    indented\n{{&lt; literal-example &gt;}}\n```\n'
    page, _ = fixture_catalog(tmp_path, f'''<h2 id="install">Install</h2>
<pre><code class="language-bash">{source}</code></pre>
<pre class="mermaid">graph TD\n A --&gt; B\n</pre>
<table><tr><th>Tool<th>Version<tr><td>Hugo<td>0.157</table>
<p><abbr title="Kubernetes">K8s</abbr> <a href="../other/#check">related</a></p>
<ul><li>Parent<ul><li>Child</ul><li>Second</ul>
<h2 id="references">References</h2><ol><li><a href="https://example.org/paper">Paper</a></ol>
<button>Copy code</button>''')
    exporter.export(tmp_path)
    text = (page / 'index.md').read_text()
    assert 'first\n\n\n    indented\n{{< literal-example >}}\n```\n' in text
    assert '````bash\n' in text
    assert '```mermaid\ngraph TD\n A --> B\n```' in text
    assert '| Tool | Version |\n| --- | --- |\n| Hugo | 0.157 |' in text
    assert 'K8s (Kubernetes)' in text
    assert '[related](https://example.org/blog/docs/other/#check)' in text
    assert '[Install](https://example.org/blog/docs/example/#install)' in text
    assert '- Parent' in text and '  - Child' in text and '- Second' in text
    assert '1. [Paper](https://example.org/paper)' in text
    assert 'Copy code' not in text and 'Do not export' not in text
    catalog = json.loads((tmp_path / 'content-index.json').read_text())
    assert catalog['articles'][0]['content_sha256'] == hashlib.sha256(text.encode()).hexdigest()


@pytest.mark.parametrize('bad_url', ['https://example.org/blog/%2e%2e/escape/', 'https://example.org/other/'])
def test_path_escape_fails_before_writing_any_exports(tmp_path, bad_url):
    page, catalog = fixture_catalog(tmp_path, '<p>Safe</p>')
    catalog['articles'].append(dict(catalog['articles'][0], url=bad_url))
    (tmp_path / 'content-index.json').write_text(json.dumps(catalog))
    with pytest.raises(ValueError):
        exporter.export(tmp_path)
    assert not (page / 'index.md').exists()


def test_escaped_shortcode_in_prose_is_exported_verbatim(tmp_path):
    """Hugo renders the documented escape {{</* name */>}} as a literal — a
    teaching post that NAMES a shortcode in a sentence is ordinary content, not
    an unresolved shortcode (an unknown one fails the Hugo build long before
    export). A false positive here blocked every page's export."""
    page, _ = fixture_catalog(tmp_path, '<p>Use the {{&lt; screenshot &gt;}} shortcode in prose.</p>')
    exporter.export(tmp_path)
    assert 'Use the {{< screenshot >}} shortcode in prose.' in (page / 'index.md').read_text()


@pytest.mark.parametrize('argv', [['-DF'], ['-dpublic2'], ['--destination=elsewhere'], ['--buildDrafts']])
def test_build_site_refuses_every_argument(argv):
    """hugo's pflag accepts combined shorthands and attached values, so a flag
    allowlist cannot be made safe; the helper takes no arguments at all and
    exits before hugo runs."""
    r = subprocess.run([sys.executable, str(TEMPLATES / 'scripts/build-site.py'), *argv],
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert 'takes no arguments' in r.stderr


def test_hugo_catalog_only_exports_published_content(tmp_path):
    hugo = shutil.which('hugo')
    if not hugo:
        pytest.skip('Hugo required for publication-boundary integration test')
    (tmp_path / 'layouts/docs').mkdir(parents=True)
    (tmp_path / 'layouts/docs/single.html').write_text('<main id="content"><div data-article-body>{{ .Content }}</div></main>')
    (tmp_path / 'layouts/index.html').write_text('<main>Home</main>')
    for name in ['home.catalog.json', 'home.llms.txt']:
        shutil.copy(TEMPLATES / 'layouts' / name, tmp_path / 'layouts' / name)
    (tmp_path / 'hugo.toml').write_text('''baseURL = "https://example.org/blog/"
title = "Test"
[frontmatter]
lastmod = ["last_updated", "lastmod", "date"]
[outputs]
home = ["HTML", "RSS", "Catalog", "LLMS"]
[outputFormats.Catalog]
mediaType = "application/json"
baseName = "content-index"
isPlainText = true
[outputFormats.LLMS]
mediaType = "text/plain"
baseName = "llms"
isPlainText = true
''')
    for slug, extra in [('published', 'commands_change_state: false\nlast_updated: 2026-02-01'), ('unknown', ''), ('draft', 'draft: true'), ('future', 'publishDate: 2999-01-01'), ('expired', 'expiryDate: 2001-01-01')]:
        page = tmp_path / 'content/docs' / slug
        page.mkdir(parents=True)
        (page / 'index.md').write_text(f'---\ntitle: {slug}\ndate: 2026-01-01\n{extra}\n---\n## Evidence\n\nPublic text.\n')
    # a dateless page (the About/Topics pages the docs tell operators to create)
    (tmp_path / 'content/docs/undated').mkdir()
    (tmp_path / 'content/docs/undated/index.md').write_text('---\ntitle: undated\n---\nNo dates here.\n')
    (tmp_path / 'private').mkdir()
    (tmp_path / 'private/secret.md').write_text('never publish this')
    subprocess.run([hugo, '--minify'], cwd=tmp_path, check=True, capture_output=True)
    public = tmp_path / 'public'
    exporter.export(public)
    catalog = json.loads((public / 'content-index.json').read_text())
    articles = {a['title']: a for a in catalog['articles']}
    assert set(articles) == {'published', 'unknown', 'undated'}
    assert articles['undated']['published'] == '' and articles['undated']['updated'] == ''
    undated_md = (public / 'docs/undated/index.md').read_text()
    assert 'Published:' not in undated_md and '0001-01-01' not in undated_md
    assert articles['published']['commands_change_state'] is False
    assert articles['unknown']['commands_change_state'] == 'unknown'
    assert articles['published']['updated'] == '2026-02-01'
    assert articles['published']['last_verified'] is False
    assert len(list(public.rglob('index.md'))) == 3
    assert '<item>' in (public / 'index.xml').read_text()
    assert 'content-index.json' in (public / 'llms.txt').read_text()
