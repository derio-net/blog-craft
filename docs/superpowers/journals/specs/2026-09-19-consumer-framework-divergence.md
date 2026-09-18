# Journal: 2026-09-19-consumer-framework-divergence

<!-- fr:journal kind=decision scope=spec id=b02b89fdeb28 created=2026-09-19T01:15:31 -->
### b02b89fdeb28 · decision · Operator selected manifest mechanism

Implement only declared framework divergence through the existing three-way merge pipeline; undeclared-drift refusal and convergence reporting are deferred.

<!-- fr:journal kind=review scope=spec id=e698a45d20ba created=2026-09-19T01:15:35 -->
### e698a45d20ba · review · Spec reviewed against updater

Verified tools/update.py already rerenders the recorded release from the sync snapshot and applies ordinary merged paths with git merge-file. The specification uses that exact base and limits the new classification to manifest-declared framework paths. Corrected scope to defer undeclared-drift refusal because it is a second mechanism beyond this run.
