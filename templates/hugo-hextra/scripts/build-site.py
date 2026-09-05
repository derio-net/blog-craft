#!/usr/bin/env python3
"""Build Hugo and the configured agent exports into public/ (stdlib only)."""
import subprocess
import sys
from pathlib import Path
site=Path(__file__).resolve().parents[1]
if any(a.split('=')[0] in {'--destination','-d'} for a in sys.argv[1:]):
    raise SystemExit('build-site.py owns public/; use --baseURL for preview origins')
subprocess.run(['hugo','--minify','--cleanDestinationDir',*sys.argv[1:]],cwd=site,check=True)
if (site/'public/content-index.json').exists():
    subprocess.run([sys.executable,str(site/'scripts/export-content.py'),str(site/'public')],check=True)
