# APP-003 Product Live Formal Approval（待负责人填写）

本模板只绑定 `app003-product-live-20261113-01` 的固定 scope。填写并明确批准前，不得调用正式 runner、读取 API key、创建批次目录或发送 provider 请求。

```text
batch_id: app003-product-live-20261113-01
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
approver: <负责人姓名或标识>
approved_at_utc: <ISO-8601 UTC 时间>
approval_record_ref: <可选记录链接或编号>
is_test_only: false
approval_statement: I approve product live formal execution of batch app003-product-live-20261113-01 with the exact scope above: four frozen inputs, DeepSeek deepseek-flash, condition C0, maximum 12 HTTP attempts, and CAD pipeline enabled only after explicit user confirmation. I understand ask/refuse/conflict/unsupported/parse/Schema/IR/CAD/STEP failures must fail closed and that this is a smoke run, not a broad language evaluation or manufacturing certification.
```

批准凭证必须在正式 runner 调用前由服务端构造为 `ProductLiveFormalApproval`，并与同 batch 的 `ProductLiveAuthorization` 做 binding 校验。`is_test_only=true`、错 batch、错 provider/model/hash/预算或缺字段都会被拒绝。
