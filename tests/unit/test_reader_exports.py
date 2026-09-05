"""Publication boundaries and semantic fidelity of reader exports."""
import hashlib
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / 'templates/hugo-hextra'
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


def test_unresolved_shortcode_fails(tmp_path):
    page, _ = fixture_catalog(tmp_path, '<p>{{&lt; broken &gt;}}</p>')
    with pytest.raises(ValueError, match='Unresolved shortcode'):
        exporter.export(tmp_path)
    assert not (page / 'index.md').exists()


def test_hugo_catalog_only_exports_published_content(tmp_path):
    hugo = shutil.which('hugo')
    if not hugo:
        pytest.skip('Hugo required for publication-boundary integration test')
    (tmp_path / 'layouts/docs').mkdir(parents=True)
    (tmp_path / 'layouts/docs/single.html').write_text('<main id="content"><div data-article-body>{{ .Content }}</div></main>')
    (tmp_path / 'layouts/index.html').write_text('<main>Home</main>')
    for name in ['home.catalog.json', 'home.llms.txt', 'home.rss.xml']:
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
    (tmp_path / 'private').mkdir()
    (tmp_path / 'private/secret.md').write_text('never publish this')
    subprocess.run([hugo, '--minify'], cwd=tmp_path, check=True, capture_output=True)
    public = tmp_path / 'public'
    exporter.export(public)
    catalog = json.loads((public / 'content-index.json').read_text())
    articles = {a['title']: a for a in catalog['articles']}
    assert set(articles) == {'published', 'unknown'}
    assert articles['published']['commands_change_state'] is False
    assert articles['unknown']['commands_change_state'] == 'unknown'
    assert articles['published']['updated'] == '2026-02-01'
    assert articles['published']['last_verified'] is False
    assert len(list(public.rglob('index.md'))) == 2
    assert '<item>' in (public / 'index.xml').read_text()
    assert 'content-index.json' in (public / 'llms.txt').read_text()
