# APP-003 Product Live Formal Approval — app003-product-live-20261114-02

**状态：历史模板，已由正式批准记录取代。** 本 batch 的 formal preflight 与真实请求分别获批；实际记录见 `formal-preflight.json`、`execution-report.json` 和 `checkpoint.md`。保留下方模板内容用于追溯，不代表当前仍待批准。

```text
batch_id: app003-product-live-20261114-02
profile_id: app003-product-live.v1
sample_set: app003-product-live-smoke.v1
provider: DeepSeek
model: deepseek-flash
condition: C0
input_ids: P1-24mm, P2-ask-bore, P3-catalog-conflict, P4-unsupported
inputs_sha256: 666a4c08bbbb051a2bac038db4f5184c18a01829d4fff8f6d698832195fc0e8a
evaluator_labels_sha256: 73c671a7950afebb7e7e4c3a1e4fdc52702ebf43ec85fec0a588308abc4fd795
prompt_file_sha256: 18cc180fca975da89ed01e10b750ecf023cf800a30e84f99664191ede2faafe9
max_batch_http: 12
enable_cad_pipeline: true
approver: <由负责人填写>
approved_at_utc: <负责人确认时记录 ISO-8601 UTC>
approval_record_ref: <负责人确认后填写对话或记录引用>
is_test_only: false
approval_statement: <负责人明确批准该 batch 的 formal preflight；此项本身不授权真实 provider 请求>
```

任何 provider HTTP 请求都需要在 formal preflight 通过后，再取得独立、明确的 live execution approval。
