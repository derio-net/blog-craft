#!/usr/bin/env python3
"""Insert a block of text immediately before a marker line in a file.

Used by blog-post and media skill helpers to splice into auto-managed sections
(e.g. "<!-- /blog-post auto-appends entries here -->") without parsing Markdown.

Usage:
    insert-before-marker.py <file> <marker> <new-content>

Reads <new-content> from argv[3] (so it can contain newlines via $'...'),
finds the first occurrence of <marker>, inserts <new-content> + newline before it.
Idempotent: if <new-content> is already present immediately above <marker>, no-op.
"""
import sys

if len(sys.argv) != 4:
    print(f"usage: {sys.argv[0]} <file> <marker> <new-content>", file=sys.stderr)
    sys.exit(2)

path, marker, new_content = sys.argv[1], sys.argv[2], sys.argv[3]

with open(path) as f:
    content = f.read()

if marker not in content:
    print(f"marker not found in {path}: {marker!r}", file=sys.stderr)
    sys.exit(1)

# Idempotency check
already = new_content.rstrip() + "\n" + marker
if already in content:
    print(f"already present, no-op")
    sys.exit(0)

content = content.replace(marker, new_content.rstrip() + "\n" + marker, 1)

with open(path, "w") as f:
    f.write(content)
print(f"inserted into {path}")
