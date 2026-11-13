<!-- fr:journal-schema=3 -->
# Journal: 2026-11-13-writing-standards

<!-- fr:journal kind=decision scope=plan id=plan-tests-ci created=2026-11-13T13:40:41+00:00 -->
### plan-tests-ci · decision · Test evidence is CI (tests: ci), not a local log

The container has no hugo; 38 pre-existing tests fail locally for that reason alone (measured 2026-11-13, 3m13s run). Each phase runs its writing-standard tests locally and records CI's test job on the pushed head. The draft PR opens when implement starts.
