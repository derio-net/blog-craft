#!/usr/bin/env python3
"""Replace <!-- MEDIA: ... --> placeholder pairs in a blog-craft post with
rendered Hugo shortcodes — but only for placeholders whose referenced asset
file is already present in the post's bundle directory.

Placeholder pattern (two adjacent HTML-comment lines):

    <!-- MEDIA: screenshot | A grafana dashboard | Visit https://example.com -->
    <!-- {{</* screenshot src="grafana.png" caption="Grafana" */>}} -->

After filling (asset grafana.png present):

    {{< screenshot src="grafana.png" caption="Grafana" >}}

Usage:
    media-fill.py <post-bundle-dir>

Exit codes:
    0  — at least one placeholder filled (or none present, nothing to do)
    1  — index.md missing
    2  — bad arguments
"""
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print(f"usage: {sys.argv[0]} <post-bundle-dir>", file=sys.stderr)
    sys.exit(2)

bundle = Path(sys.argv[1])
index = bundle / "index.md"
if not index.is_file():
    print(f"ERROR: {index} not found", file=sys.stderr)
    sys.exit(1)

# Match the second line of the placeholder pair: a commented Hugo shortcode of
# the form <!-- {{</* <name> <args...> */>}} -->. We capture name+args.
# The shortcode body is matched non-greedily up to the */>}} terminator.
SHORTCODE_RE = re.compile(
    r'^\s*<!--\s*\{\{</\*\s*(\S+)\s+(.+?)\s*\*/>\}\}\s*-->\s*$'
)

# Matches the instruction comment: <!-- MEDIA: <type> | ... -->
# The body may legitimately contain ">" (URLs like http://<svc>:8429, UI paths
# like "Dashboards > Node Exporter") — only the full "-->" ends the comment.
MEDIA_INSTRUCTION_RE = re.compile(r'^\s*<!--\s*MEDIA:\s*.*?-->\s*$')

# Pull a src="..." (or src='...') value out of shortcode args
SRC_RE = re.compile(r'''src\s*=\s*["']([^"']+)["']''')

lines = index.read_text().splitlines(keepends=True)
out = []
filled = 0
skipped_missing = []
i = 0
while i < len(lines):
    line = lines[i]
    if MEDIA_INSTRUCTION_RE.match(line) and i + 1 < len(lines):
        next_line = lines[i + 1]
        m = SHORTCODE_RE.match(next_line)
        if m:
            sc_name, sc_args = m.group(1), m.group(2)
            src = None
            src_m = SRC_RE.search(sc_args)
            if src_m:
                src = src_m.group(1)

            asset_present = src is not None and (bundle / src).is_file()
            if asset_present:
                # Replace both lines with the uncommented shortcode
                # Preserve the indentation of the shortcode line.
                indent = re.match(r'^(\s*)', next_line).group(1)
                out.append(f"{indent}{{{{< {sc_name} {sc_args} >}}}}\n")
                filled += 1
                i += 2
                continue
            else:
                # Asset missing — skip this placeholder entirely
                skipped_missing.append(src or "(no src)")
        # If next line isn't a recognized shortcode comment, fall through
    out.append(line)
    i += 1

if filled == 0 and not skipped_missing:
    print(f"no <!-- MEDIA: --> placeholders found in {index}")
    sys.exit(0)

if filled > 0:
    index.write_text("".join(out))
    print(f"filled {filled} placeholder(s) in {index}")

if skipped_missing:
    print(f"skipped {len(skipped_missing)} placeholder(s) — asset(s) missing in bundle:", file=sys.stderr)
    for s in skipped_missing:
        print(f"  - {s}", file=sys.stderr)
