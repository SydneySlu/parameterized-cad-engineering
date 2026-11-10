# APP-001-V5-FORMAL-EFFECT-EVALUATION handoff

The v5 effect run must use `scripts/run_app001_v5_formal_batch.py`, the unique
batch authorization in this directory, and the frozen runtime versions/hashes.
Do not reuse the v4 script or batch directory. Before any model request, review
the task diff, rerun the v5 script tests and relevant LLM/Schema suites, then
run the script preflight. A successful offline test or dry run is not a model
effect result. If preflight succeeds, execute the real batch and preserve its
raw/run records under the git-ignored batch directory; review the evidence
before writing conclusions.
