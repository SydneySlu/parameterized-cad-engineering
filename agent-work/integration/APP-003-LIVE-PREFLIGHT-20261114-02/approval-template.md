# APP-003 Product Live Formal Approval — app003-product-live-20261114-02

**状态：待负责人审阅/填写。** 以下为批准模板，不是已批准记录。负责人批准 scope 后，需明确确认并补齐本模板；批准 formal preflight 不等于批准发送真实请求。

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
