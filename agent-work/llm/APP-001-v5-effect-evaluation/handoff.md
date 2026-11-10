# APP-001-V5-FORMAL-EFFECT-EVALUATION handoff (historical pre-run instructions)

These were the controlled execution instructions before the authorized v5
batch ran. The sole authorized batch `app001-phase1-v5-20261111-01` has already
run and must not be resumed, rerun, overwritten, or combined with another
batch. Its 32 raw files remain at the batch root as a documented deviation
from the authorized `raw/` subdirectory; preserve them unchanged.

The future-run retention path is now corrected and independently reviewed:
`src/llm/runner.py` writes formal raw responses under
`work/app001-runs/<batch_id>/raw/`. Any future model run still requires a
reviewed entrypoint baseline, a new unique batch ID, and separate explicit
authorization. The implementation and document follow-up through `3a55cc1`
passed independent review, and Codex's final acceptance passed. The project
owner must push/merge the accepted branch, after which Codex will verify `main`
and rerun targeted checks before the task can be marked `done`.
