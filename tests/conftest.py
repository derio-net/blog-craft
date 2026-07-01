import os
import sys

# Make `tools/` and `migrations/` importable from unit tests.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(_ROOT, "tools"), _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
