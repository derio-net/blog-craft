# Journal: 2026-07-26-abbreviation-glossary

<!-- fr:journal kind=discovery scope=plan id=p2-percent-shortcode created=2026-07-26T00:33:10 phase=2 -->
### p2-percent-shortcode · discovery · {{% %}} shortcode BODIES are prose — only the tags are excluded (phase 2)

A red test asserted that '{{% note %}}NUT{{% /note %}}' proposes nothing. That was wrong about the domain: Hugo's percent form renders its body AS MARKDOWN (that is the whole difference from '{{< >}}'), so a marker placed in the body works fine. Only the tags themselves must be excluded. Test corrected to pin the real contract — tags excluded, inner prose still scanned. The angle-bracket form stays fully excluded, body included, because its body is not markdown.

<!-- fr:journal kind=finding scope=plan id=p3-idempotence created=2026-07-26T00:36:14 phase=3 state=fixed -->
### p3-idempotence · finding [fixed] · Idempotence needed an explicit marked-terms seed, not just span exclusion (phase 3)

First implementation assumed idempotence 'fell out' of excluded_spans: a token inside an existing {{< abbr >}} is in an excluded span, so it is never re-proposed. True, but insufficient — a LATER bare occurrence of the same term is still a candidate, so a second run marked occurrence #2, a third run #3, and the sweep never converged. Two red tests caught it (test_applying_twice_is_a_no_op, test_an_already_marked_post_gains_nothing). Fixed by seeding the first-occurrence 'seen' set from MARKER_RE.findall(text) — terms already marked anywhere in the file are treated as satisfied. The misleading comment claiming it fell out was replaced with one explaining why the seed is required.

<!-- fr:journal kind=discovery scope=plan id=p4-two-mirrors created=2026-07-26T00:40:28 phase=4 -->
### p4-two-mirrors · discovery · The validator needs TWO mirrors, not one — glossary_scan travels with it (phase 4)

The plan said mirror validate_glossary.py into templates/hugo-hextra/scripts/. But the validator imports MARKER_RE / code_spans / markers_in from glossary_scan rather than re-deriving 'is this marker executed or shown as an example?', and a materialized blog has no plugin on sys.path. Shipping only the validator would have produced an ImportError the moment a blog's CI ran it — and no unit test would have caught it, because in-repo both files sit in tools/.

Mirrored both; both pairs enrolled in test_mirrors.py with the reason recorded in its docstring. Cost is one extra shipped file under the existing scripts/** framework rule — no manifest change, no new class.

Also added glossary_scan.code_spans() in this phase: the validator must IGNORE a {{< abbr >}} written inside a code fence, because a post documenting the shortcode would otherwise fail its own blog's CI. code_spans is deliberately narrower than excluded_spans — it omits headings, since a marker in a heading really does execute and so really must be validated.

<!-- fr:journal kind=finding scope=plan id=p5-hugo-named-params created=2026-07-26T00:55:56 phase=5 state=fixed -->
### p5-hugo-named-params · finding [fixed] · Hugo forbids mixing positional and named shortcode params — display override is now positional (phase 5)

The spec specified {{< abbr "SLO" text="SLOs" >}}. Hugo rejects it outright: 'got named parameter text. Cannot mix named and positional parameters'. Caught by test_display_override_changes_display_not_lookup, which builds a real site.

Options were all-named ({{< abbr term="NUT" >}} for the common case — verbose where it matters most) or all-positional. Chose all-positional: {{< abbr "NUT" >}} stays terse and the inflected form is {{< abbr "SLO" "SLOs" >}}. Updated the shortcode (.Get 1), glossary_apply._marker(), both test files and the shortcode's own header comment, which now records WHY it is positional so nobody 'improves' it back to text=. Spec §3 is corrected in phase 7.

<!-- fr:journal kind=discovery scope=plan id=p5-flake-fixed created=2026-07-26T00:55:57 phase=5 -->
### p5-flake-fixed · discovery · Pre-existing explainers flake fixed; suite is now 482 passed / 0 failed (phase 5)

Branch-point baseline was 395 passed, 1 FAILED (test_explainers_hugo). Fixed by stamping the scaffolded post a day ahead — making the failure deterministic instead of time-of-day dependent — then passing --buildFuture. Proven both ways: with the flag removed and the day-ahead stamp kept, the test fails; restored, it passes. Every new render test in test_glossary_hugo.py uses --buildFuture from the start.

Phase 5 verification: 482 passed, 0 failed (was 395/1), smoke-bootstrap 6 passed 0 failed.
